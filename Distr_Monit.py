# plik Distr_Monit.py 
# zawiera implementację monitora rozproszonego (Distributed Monitor)
# napisaną w języku programowania python


# Importy:
# Logowanie informacji
from Logger import logger as myLogger
# "A multi-producer, multi-consumer queue."
# https://docs.python.org/3/library/queue.html?highlight=queue#module-queue
import queue
# "Thread module emulating a subset of Java's threading model."
# https://docs.python.org/3/library/threading.html
import threading
# "Python bindings for 0MQ."
# https://github.com/zeromq/pyzmq
# pipenv install pyzmq
import zmq
# "Context to automatically close something at the end of a block."
from contextlib import closing
# Wrapper module for _socket, providing some additional facilities
# implemented in Python.
import socket
# Pakowanie - picklowanie obiektu pythona do binarnych danych
# https://docs.python.org/3/library/pickle.html
import pickle


# Zaimplementowany algorytm wzajemnego wykluczania: suzuki-kasami
# https://www.geeksforgeeks.org/suzuki-kasami-algorithm-for-mutual-exclusion-in-distributed-system/
# Założenie - token wygląda następująco: 
# (znak '|' służy tylko rozdzieleniu poszczególnych składowych tokenu)
# |rozmiar(kolejki)|kolejka Q|
# |rozmiar(tablicy)|tablica LN|
# |rozmiar(zmiennych współdzielonych)|zmienne współdzielone|
# gdzie rozmiar ma ustaloną wielkość 32 bitów i oznacza rozmiar obiektu w nawiasach ()


# KOMUNIKATY:
#   REQUEST: 
#       - wysłanie swojego ID oraz swojej wartości RNi[i]
#   TOKEN:
#       - wysłanie tokenu pierwszemu procesowi z kolejki Q
# Implementacja tokenu:
# Funkcja do konwersji obiektu
def conv_obj(Qsize, Q, LNsize, LN, SDsize, SD, to_token=True):
    pass
# Funkcja do konwersji tokenu 
def conv_token():
    pass
# Przesyłany obiekt wymiany - token albo aktualizacja RNi
class ExchangeTokenOrRNi():
    # Przesyłanie tokenu --> token_or_rni == True, 
    # a przesyłanie rni --> token_or_rni == False
    def __init__(self, rcvfrom, Qsize=None, Q=None, LNsize=None, LN=None, 
        SDsize=None, SD=None, sendto=None, rni=None):
        # Kto wysyła wiadomość - od kogo ją odbierzemy
        self.rcvfrom = rcvfrom
        # Czy wysyłamy RNi[i]
        if rni is not None:
            self.rni = rni
            self.Qsize = None
            self.Q = None
            self.LNsize = None
            self.LN = None
            self.SDsize = None
            self.SD = None
            self.sendto = None # ALL
        # Czy wysyłamy token w przeciwnym wypadku
        else:
            self.Qsize = Qsize
            self.Q = Q
            self.LNsize = LNsize
            self.LN = LN
            self.SDsize = SDsize
            self.SD = SD
            # Wyspecyfikowanego współpracownika
            self.sendto = sendto 
            self.rni = None
            

# Monitor rozproszony
# Wykorzystujący do komunikacji PUB-SUB zmq
class DistributedMonitor():
    def end_work(self):
        myLogger.debug("Adios. My id: " + self.my_id + ".")
        # NOTE: PROBLEM ZGUBIONEGO TOKENU
        # Zatrzymanie komunikacji
        self.stop_zmq()
    # Init monitora rozproszonego
    def __init__(self, id_ip_port, is_token_acquired, coworkers):
        # Zmienne algorytmu wzajemnego wykluczania Suzuki-Kasami
        # Na podstawie AR ćw: cw4-mutual-exclusion-wyklad.pdf
        # Tablica RN procesu i-tego
        # RNi[1..N] tablica przechowywana przez proces Pi;
        # RNi[j] oznacza największą liczbę porządkową otrzymaną
        # w żądaniu od procesu Pj
        # żądanie o n < RNi[j] jest uznawane za przedawnione,
        # gdzie n oznacza żądanie n-tego wykonania sekcji krytycznej
        self.RNi = {} 
        # Q Kolejka procesów żądających
        self.Q = []
        # Tablica LN tokenu,
        # gdzie LN[j] oznacza liczbę porządkową ostatnio wykonanego
        # żądania przez proces Pj
        # tablica ta jest aktualizowana i na jej podstawie można 
        # stwierdzić, czy jakiś proces ma zaległe żądanie:
        # Po wykonaniu sekcji krytycznej Pi aktualizuje LN[i] = RNi[i]
        self.LN = {}
        # Identyfikator danego pracownika (swój - adr IP + Port)
        self.my_id = id_ip_port
        # Lista współpracowników przy danych współdzielonych
        # identyfikatory wszystkich pracowników
        self.coworkers_list = coworkers
        # Init wyżej wymienionych tablic N 
        self.RNi = {n: 0 for n in self.coworkers_list}
        self.LN = {n: 0 for n in self.coworkers_list}
        # Czy ten proces posiada token
        self.got_token = is_token_acquired
        # Czy ten proces wszedł do sekcji krytycznej
        self.in_cs = False
        # Zmienne współdzielone spakowane do obiektu
        self.shared_obj = None
        # "A multi-producer, multi-consumer queue." 
        # Posiada blokującą metodę get - dopiero, gdy coś będzie w kolejce
        # pobierzemy to do swojego self.shared_obj
        # Kolejkę tą przy odbieraniu tokenu w pobocznym wątku 
        # będziemy uzupełniać 
        self.rcv_que = queue.Queue(1)
        # Zamek 
        self.lock = threading.Lock()
        # Mozliwość wyłączenia pobocznego wątku odbierającego wiadomości:
        self.rcv_running = True
        self.start_zmq()
    # Funkcja do odbierania wiadomości
    def receiver_fun(self):
        # https://dev.to/dansyuqri/pub-sub-with-pyzmq-part-1-2f63
        # Subscriber context
        sub_ctx = zmq.Context()
        # Subscriber socket
        sub_sock = sub_ctx.socket(zmq.SUB)
        for coworker in self.coworkers_list:
            # Połącz się ze wszystkimi oprócz siebie
            if coworker is not self.my_id:
                sub_sock.connect("tcp://"+coworker)
        # Subskrypcja wszystkiego
        sub_sock.subscribe("")
        # NOTE: BLOKUJĄCY SPOSOB
        # Odbiór wiadomości w formacie string 
        # sub_sock.recv_string()
        # https://dev.to/dansyuqri/pub-sub-with-pyzmq-part-2-2f63
        poller = zmq.Poller()
        # Rejestracja gniazda w pollerze
        poller.register(sub_sock, zmq.POLLIN)
        # Pętla działająca dopóki nie wyłączymy wątku odbiornika
        # ustawiając self.rcv_running na False
        while self.rcv_running:
            # "Poll the registered 0MQ or native fds for I/O."
            # timeout in ms
            sockets_fds = dict(poller.poll(timeout=1000))
            if sub_sock in sockets_fds:
                with self.lock:
                    # Odebranie komunikatu (blokujemy się na tej metodzie)
                    rcv_msg = sub_sock.recv()
                    # Odpakowanie komunikatu
                    unpickled_msg = pickle.loads(rcv_msg)
                    rcvfrom_id = unpickled_msg.rcvfrom
                    myLogger.debug("Received msg from: " + rcvfrom_id)
                    # Jeżeli pole rni nie jest niczym - dostaliśmy prośbę o token
                    if unpickled_msg.rni is not None:
                        # Aktualizujemy pole rni odpowiedniego procesu
                        self.RNi[rcvfrom_id] = \
                            max(self.RNi[rcvfrom_id], unpickled_msg.rni)
                        # Posiadając token 
                        if self.got_token == True:
                            # Jeżeli nie jesteśmy w sekcji krytycznej
                            if self.in_cs == False:
                                # Jeżeli to jest nowe żądanie (RNi[j]==LN[j]+1)
                                if self.RNi[rcvfrom_id] == (self.LN[rcvfrom_id] + 1):
                                    # Wysyłamy token
                                    self.send_token(receiver=rcvfrom_id)
                    # W przeciwnym wypadku chodzi o token
                    # jeżeli do nas szła wiadomość to przyjmujemy token
                    elif unpickled_msg.sendto == self.my_id:
                        myLogger.debug("Received token from: "+ rcvfrom_id)
                        self.Q = unpickled_msg.Q
                        self.LN = unpickled_msg.LN
                        self.rcv_que.put(unpickled_msg.SD)
                        self.got_token = True
                    pass
        # Jeżeli self.rcv_running jest ustawione na False
        # i wyszliśmy z pętli while self.rcv_running
        # Zamykamy gniazdo subskrybenta
        sub_sock.close()
    # Czeka, aż współpracownik będzie możliwy do połączenia
    def wait_untill_connected(self, coworker):
        # Tymczasowy socket do sprawdzenia połączenia ze współpracownikiem
        # "Context to automatically close something at the end of a block."
        coworker_IP, coworker_PORT = coworker.split(":")
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as tmp_sock:
            # https://docs.python.org/3/library/socket.html
            # Connect - waits until the connection completes
            try:
                tmp_sock.connect((coworker_IP, int(coworker_PORT)))
            except ConnectionRefusedError:
                self.wait_untill_connected(coworker)
            finally:
                pass
    # Uruchomienie mechanizmu ZMQ do publikacji tokenu oraz subskrypcji
    def start_zmq(self):
        myLogger.debug("Starting... ZMQ")
        # https://zguide.zeromq.org/docs/chapter5/
        # https://dev.to/dansyuqri/pub-sub-with-pyzmq-part-1-2f63
        # Utworzenie gniazda publikującego
        # Publisher context
        pub_ctx = zmq.Context()
        # Publisher socket
        self.pub_sock = pub_ctx.socket(zmq.PUB)
        # Łączenie gniazda z my ID --> IP:PORT
        self.pub_sock.bind("tcp://"+self.my_id)
        '''  DO PRZETESTOWANIA 
        https://dev.to/dansyuqri/pub-sub-with-pyzmq-part-1-2f63
        time.sleep(1) # new sleep statement
        "Let's edit simple_pub to include a sleep statement, 
        which is a simplified solution to this problem. 
        This way, the asynchronous bind() should run to 
        completion before the publishing of the message."
        '''
        # time.sleep(1)
        # Inne rozwiązanie niż sleep:
        pollerOUT = zmq.Poller()
        pollerOUT.register(self.pub_sock, zmq.POLLOUT)
        dict(pollerOUT.poll(timeout=1000))
        myLogger.debug("ZMQ Publisher initiated.")
        # Lista współpracowników (poza nami)
        coworkers = [
            coworker 
            for coworker in self.coworkers_list 
                if coworker != self.my_id
            ]
        # Oczekiwanie na wszystkich współpracowników (poza nami)
        # Do włączenia się
        for coworker in coworkers:
            self.wait_untill_connected(coworker)
        # Wątek odbiornika komunikatów
        # https://www.pythontutorial.net/advanced-python/python-threading/
        rcv = threading.Thread(target=self.receiver_fun)
        # https://www.geeksforgeeks.org/python-daemon-threads/
        rcv.setDaemon = True
        # Uruchomienie wątku odbiornika komunikatów
        rcv.start()
    # Zatrzymanie mechanizmu PUB-SUB ZMQ
    def stop_zmq(self):
        # Zamknięcie gniazda publikującego
        self.pub_sock.close()
        # Zakończenie wątku odbierającego komunikaty
        self.rcv_running = False
        pass
    # Wysłanie tokenu
    def send_token(self, receiver):
        myLogger.debug("Sending token from: " + self.my_id + " to: " + receiver + ".")
        # Tworzenie komunikatu
        snd_msg = ExchangeTokenOrRNi(rcvfrom=self.my_id, 
            Qsize=self.Q.__sizeof__, Q=self.Q, 
            LNsize=self.LN.__sizeof__, LN=self.LN, 
            SDsize=self.shared_obj.__sizeof__, SD=self.shared_obj,
            sendto=receiver)
        # Wysyłanie spakowanego komunikatu
        self.pub_sock.send(pickle.dumps(snd_msg))
    # Zwolnienie dostępu do zasobu (współdzielonego obiektu danych)
    # funkcja nic nie zwraca - odsyła token 
    def release(self, shared_data_obj):
        myLogger.debug("Trying to acquire lock for release... My id:" + self.my_id + ".")
        # Acquire lock try sth and then finall release
        with self.lock:
            myLogger.debug("Trying to release. My id:" + self.my_id + ".")
            # Aktualizuję współdzielony obiekt 
            self.shared_obj = shared_data_obj
            # Po wykonaniu sekcji krytycznej:
            # Aktualizuję tablicę LN wartością RNi[i]
            self.LN[self.my_id] = self.RNi[self.my_id]
            # ~ AR ćw :
            # Dla każdego procesu Pj, którego Id nie ma
            # w kolejce żetonu (Q), dołącza jego Id do Q 
            # pod warunkiem: RNi[j] == LN[j]+1 (było nowe żądanie) 
            # Aktualizacja kolejki Q
            # Lista Procesów nie będących w kolejce:
            not_in_Q_list = [p for p in self.coworkers_list if p not in self.Q]
            # Przechodząc przez listę procesów, nie będących w Q
            for p in not_in_Q_list:
                # Pod warunkiem: RNi[p_id] == LN[p_id]+1
                if self.RNi[p] == (self.LN[p] + 1):
                    # Dodanie procesu do kolejki Q
                    self.Q.append(p)
            # ~ AR ćw:
            # Jeżeli Q nie jest pusta, to usuwamy pierwszy Id z niej
            # i wysyłamy do tego procesu token
            # Wysyłanie do pierwszego Id jezeli Q niepuste
            if self.Q:
                # Wyciągnięcie pierwszego współpracownika z Q
                next_receiver = self.Q.pop(0)
                # Odebranie sobie tokenu
                self.got_token = False
                # Wysłanie do niego tokenu
                self.send_token(receiver=next_receiver)
            # Wychodzę z sekcji krytycznej
            self.in_cs = False
            myLogger.debug("Exited Critical Section. My id:" + self.my_id + ".")
    # Publikacja zaktualizowanej swojej wartości w tablicy RNi
    def pub_REQUEST(self):
        myLogger.debug("Publishing my RNi[i]. My id: " + self.my_id + ".")
        # Tworzenie komunikatu
        snd_msg = ExchangeTokenOrRNi(rcvfrom=self.my_id, rni=self.RNi[self.my_id])
        # Wysyłanie spakowanego komunikatu
        self.pub_sock.send(pickle.dumps(snd_msg))
    # Zdobycie dostępu do zasobu (współdzielonego obiektu danych)
    # jako wynik działania funkcji zwraca obiekt współdzielony
    def acquire(self):
        myLogger.debug("Trying to acquire lock for acquire... My id:" + self.my_id + ".")
        # Acquire lock try sth and then finall release
        with self.lock:
            # Jezeli mam token to:
            if self.got_token:
                myLogger.debug("Got token. CS = True. My id:" + self.my_id + ".")
                # Wchodzę do sekcji krytycznej
                self.in_cs = True
                # Zwracam współdzielony obiekt 
                return self.shared_obj
            else:
                myLogger.debug("Update RNi and wait for token. My id:" + self.my_id + ".")
                # W przeciwnym razie aktualizuję o 1 wartość tablicy RNi odpowiadającą i
                self.RNi[self.my_id]+=1
                # Publikacja zaktualizowanej wartości tablicy RNi odpowiadającą i
                # Wysyłając żądanie(i, sn) - sn to zaktualizowana wartość RNi[i]
                self.pub_REQUEST()
        # Jeżeli nie otrzymaliśmy obiektu to czekamy, 
        # aż wątek odbierający komunikaty odbierze token
        # Blokujemy się w tym miejscu, aż w kolejce będziemy 
        # mieli gotowy obiekt współdzielony
        myLogger.debug("Waiting for token. My id:" + self.my_id + ".")
        self.shared_obj = self.rcv_que.get(block=True)
        myLogger.debug("Got token. CS = True. My id:" + self.my_id + ".")
        # Wchodzę do sekcji krytycznej
        self.in_cs = True
        # Zwracam współdzielony obiekt 
        return self.shared_obj


# Funkcja main do debugowania.
if __name__ == "__main__":
    # Start
    myLogger.debug("Starting... main in Distr_Monit.py.")