# plik Distr_Monit.py 
# zawiera implementację monitora rozproszonego (Distributed Monitor)
# napisaną w języku programowania python


# Importy:
# Logowanie informacji
from Logger import logger as myLogger
# "A multi-producer, multi-consumer queue." [1]
import queue
# "Thread module emulating a subset of Java's threading model." [2]
import threading
# "Python bindings for 0MQ." [3]
import zmq
# "Context to automatically close something at the end of a block." [4]
from contextlib import closing
# "Wrapper module for _socket, providing some additional facilities
# implemented in Python." [5]
import socket
# Pakowanie - picklowanie obiektu pythona do binarnych danych [6] 
import pickle
# Sys dla sprawdzania wielości obiektu - wiadomości przy debugowaniu komunikatów
# import sys


# Do osobnego oddawania:
# Przesyłana wiadomość - token albo aktualizacja RNi
class ExchangeMsg():
    def __init__(self, rcvfrom, Q=None, LN=None, 
        SD=None, sendto=None, rni=None):
        # Kto wysyła wiadomość - od kogo ją odbierzemy
        self.rcvfrom = rcvfrom
        # rni == None --> wysyłamy token, a nie REQUEST
        self.rni = rni
        # Zawartość tokenu: Q, LN, SD
        self.Q = Q
        self.LN = LN
        self.SD = SD
        # sendto == None --> do wszystkich
        self.sendto = sendto  
# # Do spójności rozwiązania z rozwiązaniami kolegów:
# # TODO: Wspólne komunikaty (z resztą grupy) do testowania między językami!
# # Przesyłana wiadomość - token albo aktualizacja RNi
# class ExchangeMsg():
#     # Przesyłanie tokenu --> rni is None, 
#     # a przesyłanie RNi[i] --> rni is not None
#     def __init__(self, rcvfrom, Qsize=None, Q=None, LNsize=None, LN=None, 
#         SDsize=None, SD=None, sendto=None, rni=None):
#         # Kto wysyła wiadomość - od kogo ją odbierzemy
#         self.rcvfrom = rcvfrom
#         # Czy wysyłamy RNi[i]
#         if rni is not None:
#             self.rni = rni
#             self.Qsize = None
#             self.Q = None
#             self.LNsize = None
#             self.LN = None
#             self.SDsize = None
#             self.SD = None
#             self.sendto = None # ALL
#         # Czy wysyłamy token w przeciwnym wypadku
#         else: # If rni is None
#             self.Qsize = Qsize
#             self.Q = Q
#             self.LNsize = LNsize
#             self.LN = LN
#             self.SDsize = SDsize
#             self.SD = SD
#             # Wyspecyfikowanego współpracownika
#             self.sendto = sendto 
#             self.rni = None
        

# Monitor rozproszony
# Wykorzystujący do komunikacji PUB-SUB zmq
class DistributedMonitor():
    def end_work(self):
        # NOTE: PROBLEM ZGUBIONEGO TOKENU
        myLogger.debug("Adios. My id: " + self.my_id + ".")
        # Zatrzymanie komunikacji
        self.stop_zmq()
    # Init monitora rozproszonego
    def __init__(self, id_ip_port, is_token_acquired, coworkers):
        # Zaimplementowany algorytm wzajemnego wykluczania: suzuki-kasami [0]
        # Zmienne algorytmu wzajemnego wykluczania Suzuki-Kasami
        # Na podstawie AR ćw4 wzajemne wykluczanie (~AR_ćw)
        # RNi[1..N] tablica RN przechowywana przez proces Pi;
        # RNi[j] oznacza największą liczbę porządkową otrzymaną
        # w żądaniu od procesu Pj
        # żądanie o n < RNi[j] jest uznawane za przedawnione,
        # gdzie n oznacza żądanie n-tego wykonania sekcji krytycznej
        # Tablica RN procesu i-tego
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
        # Identyfikator danego pracownika-procesu (swój - "IP:PORT")
        self.my_id = id_ip_port
        # Lista współpracowników przy danych współdzielonych
        # identyfikatory wszystkich procesów
        self.coworkers_list = coworkers
        # Init wyżej opisanych tablic N 
        self.RNi = {process: 0 for process in self.coworkers_list}
        self.LN = {process: 0 for process in self.coworkers_list}
        # Czy ten proces (w momencie initu Monitora) posiada token
        if is_token_acquired == "1" :
            self.got_token = True
        else:
            self.got_token = False
        # Czy ten proces wszedł do sekcji krytycznej
        self.in_cs = False
        # Zmienne współdzielone spakowane do obiektu
        self.shared_obj = None
        # Kolejka z blokującą metodą get - dopiero, gdy coś będzie w kolejce
        # pobierzemy to do swojego self.shared_obj
        # Kolejkę uzupełniamy (put) przy odbieraniu tokenu 
        self.rcv_que = queue.Queue(1)
        # Zamek 
        # "The class implementing primitive lock objects. 
        # Once a thread has acquired a lock, 
        # subsequent attempts to acquire it block, 
        # until it is released; any thread may release it."
        self.lock = threading.Lock()
        # Mozliwość wyłączenia pobocznego wątku odbierającego wiadomości:
        self.rcv_running = True
        # Init komunikacji ZMQ
        self.start_zmq()
    # Inicjalizacja publishera
    def publisher_init(self):
        # Utworzenie gniazda publikującego [7]
        # Kontekst Publishera
        pub_ctx = zmq.Context()
        # Gniazdo Publishera
        self.pub_sock = pub_ctx.socket(zmq.PUB)
        # Łączenie gniazda z my ID --> IP:PORT
        self.pub_sock.bind("tcp://"+self.my_id)
        '''  DO PRZETESTOWANIA [7]
        time.sleep(1)
        "Let's edit simple_pub to include a sleep statement, 
        which is a simplified solution to this problem. 
        This way, the asynchronous bind() should run to 
        completion before the publishing of the message."
        '''
        # Inne rozwiązanie niż sleep:
        pollerOUT = zmq.Poller()
        pollerOUT.register(self.pub_sock, zmq.POLLOUT)
        events_from_poll = pollerOUT.poll(timeout=1000)
        myLogger.debug("ZMQ Publisher initiated. \n" + \
            "\tEvents ready to be processed: \n\t" + str(events_from_poll))
    # Inicjalizacja subskrybenta
    def subscriber_init(self):
        # Kontekst Subskybenta [7]
        sub_ctx = zmq.Context()
        # Gniazdo Subskybenta
        self.sub_sock = sub_ctx.socket(zmq.SUB)
        # Połącz się ze wszystkimi procesami/współpracownikami
        for coworker in self.coworkers_list:
            # Oprócz siebie
            if coworker is not self.my_id:
                self.sub_sock.connect("tcp://"+coworker)
        # Subskrypcja każdego kontentu
        self.sub_sock.subscribe("")
        # Nieblokujący sposób otrzymywania wiadomości
        self.pollerIN = zmq.Poller()   
        # Rejestracja gniazda w pollerze
        self.pollerIN.register(self.sub_sock, zmq.POLLIN)
        # Ominięcie problemu kolejności uruchomienia procesów z tokenem/bez
        events_from_poll = self.pollerIN.poll(timeout=1000) 
        myLogger.debug("ZMQ Subscriber initiated. \n" + \
            "\tEvents ready to be processed: \n\t" + str(events_from_poll))
    # Wysłanie tokenu
    def send_token(self, receiver):
        # Odebranie sobie tokenu
        self.got_token = False
        # TODO: Wspólne komunikaty (z resztą grupy) do testowania między językami!
        # snd_msg = ExchangeMsg(rcvfrom=self.my_id, 
        #     Qsize=self.Q.__sizeof__, Q=self.Q, 
        #     LNsize=self.LN.__sizeof__, LN=self.LN, 
        #     SDsize=self.shared_obj.__sizeof__, SD=self.shared_obj,
        #     sendto=receiver)
        # Tworzenie komunikatu
        snd_msg = ExchangeMsg(
            # Nadawca
            rcvfrom=self.my_id,
            # Zawartość tokenu 
            Q=self.Q, LN=self.LN, SD=self.shared_obj,
            # Odbiorca tokenu
            sendto=receiver)
        # Wysyłanie spakowanego komunikatu
        myLogger.debug("Sending token from: " + self.my_id + " to: " + receiver + ".")
        sending_token_msg = pickle.dumps(snd_msg)
        # NOTE: Debugowanie komunikatu
        # myLogger.debug("Pickled Sending msg: " + str(sending_token_msg) + " Size: " + str(sys.getsizeof(sending_token_msg)) + ".")
        self.pub_sock.send(sending_token_msg)
        myLogger.debug("Token sent from: " + self.my_id + " to: " + receiver + ".")
    # Funkcja do odbierania wiadomości
    def receiver_fun(self):
        # Pętla działająca dopóki nie wyłączymy wątku odbiornika
        # ustawiając self.rcv_running na False
        while self.rcv_running:
            # Oczekiwanie na gotowość socketu wejściowego (SUB)
            # timeout w milisekundach
            ready_sockets = dict(self.pollerIN.poll(timeout=1000))
            # myLogger.debug("Receiver polling events. \n" + \
            # "\tEvents ready to be processed: \n\t" + str(ready_sockets))  
            if self.sub_sock in ready_sockets:
                # Zamek na czas przetwarzania komunikatu
                # with self.lock == Acquire lock try sth and then finall release
                with self.lock:
                    # Odebranie komunikatu 
                    rcv_msg = self.sub_sock.recv()
                    # Odpakowanie komunikatu
                    unpickled_msg = pickle.loads(rcv_msg)
                    # Dla wygody przepisanie id z komunikatu
                    rcvfrom_id = unpickled_msg.rcvfrom
                    myLogger.debug("Received msg from: " + rcvfrom_id)
                    # Jeżeli pole rni nie jest niczym - dostaliśmy REQUEST (prośbę o token)
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
                    # W przeciwnym wypadku chodzi o token (rni is None)
                    # jeżeli do nas szła wiadomość to przyjmujemy token
                    elif unpickled_msg.sendto == self.my_id:
                        myLogger.debug("Received token from: "+ rcvfrom_id)
                        # Aktualizujemy swoje wartości Q i LN wartościami z tokenu
                        self.Q = unpickled_msg.Q
                        self.LN = unpickled_msg.LN
                        # Wstawiamy go do Kolejki by czekając getem dostać SharedData
                        self.rcv_que.put(unpickled_msg.SD)
                        # Ustawiamy flagę posiadania tokenu na True
                        self.got_token = True
        # Jeżeli self.rcv_running jest ustawione na False
        # to wychodzimy z pętli while self.rcv_running
        # Zamykamy gniazdo subskrybenta
        self.sub_sock.close()
        myLogger.debug("ZMQ stopped.")
    # Czeka, aż współpracownik będzie możliwy do połączenia
    def wait_untill_connected(self, coworker):
        # Tymczasowy socket do sprawdzenia połączenia ze współpracownikiem
        # "Context to automatically close something at the end of a block."
        coworker_IP, coworker_PORT = coworker.split(":")
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as tmp_sock:
            try:
                # Connect - czeka dopóki się nie połączy / 
                # nie rzuci ConnectionRefusedError [8]
                tmp_sock.connect((coworker_IP, int(coworker_PORT)))
            except ConnectionRefusedError:
                # Ponowienie próby połączenia
                self.wait_untill_connected(coworker)
            finally:
                if self.conn_logged == False:
                    self.conn_logged = True
                    myLogger.debug("Coworker: " + str(coworker) + " connected.")
    # Oczekiwanie na wszystkich współpracowników
    def waiting_for_coworkers(self):
        # Lista współpracowników (poza nami)
        coworkers = [
            coworker 
            for coworker in self.coworkers_list 
                if coworker != self.my_id
            ]
        # Oczekiwanie na wszystkich współpracowników (poza nami)
        # Do włączenia się do pracy
        for coworker in coworkers:
            self.conn_logged = False
            self.wait_untill_connected(coworker)
        myLogger.debug("All coworkers connected.")
    # Uruchomienie wątku odbiornika komunikatów
    def start_receiver(self):
        # Wątek odbiornika komunikatów [9]
        rcv = threading.Thread(target=self.receiver_fun)
        # Wątek działający w tle [10]
        rcv.setDaemon = True
        # Uruchomienie wątku odbiornika 
        rcv.start()
        myLogger.debug("Receiver thread started.")
    # Uruchomienie mechanizmu ZMQ do publikacji tokenu oraz subskrypcji
    def start_zmq(self):
        myLogger.debug("Starting... ZMQ")
        # Inicjalizacja publishera
        self.publisher_init()
        # Czekanie na wszystkich współpracowników do dołączenia do pracy
        self.waiting_for_coworkers()
        # Inicjalizacja subskrybenta
        self.subscriber_init()
        # Wystartowanie wątku odbierającego wiadomości
        self.start_receiver()
        myLogger.debug("ZMQ started.")
    # Zatrzymanie mechanizmu PUB-SUB ZMQ
    def stop_zmq(self):
        # Zamknięcie gniazda publikującego
        self.pub_sock.close()
        # Zakończenie wątku odbierającego komunikaty
        # Loggowanie zakończenia ZMQ po wyjściu z wątku odbiornika
        self.rcv_running = False
    # Zwolnienie dostępu do zasobu (współdzielonego obiektu danych)
    # funkcja nic nie zwraca - odsyła token jeżeli ktoś o niego prosi
    def release(self, shared_data_obj):
        # Zamek na czas opuszczania strefy krytycznej
        with self.lock:
            myLogger.debug("Trying to release SD. My id:" + self.my_id + ".")
            # Aktualizuję współdzielony obiekt 
            self.shared_obj = shared_data_obj
            # Po wykonaniu sekcji krytycznej:
            # Aktualizuję tablicę LN wartością RNi[i]
            self.LN[self.my_id] = self.RNi[self.my_id]
            # (~AR_ćw)
            # Dla każdego procesu Pj, którego Id nie ma
            # w kolejce żetonu (Q), dołącza jego Id do Q 
            # pod warunkiem: RNi[j] == LN[j]+1 (było nowe żądanie) 
            # Aktualizacja kolejki Q
            # Lista Procesów nie będących w kolejce:
            not_in_Q_que = [
                process 
                for process in self.coworkers_list 
                    if process not in self.Q
            ]
            # Przechodząc przez listę procesów, nie będących w Q
            for process in not_in_Q_que:
                # Pod warunkiem: RNi[p_id] == LN[p_id]+1
                if self.RNi[process] == (self.LN[process] + 1):
                    # Dodanie procesu do kolejki Q
                    self.Q.append(process)
            # (~AR_ćw)
            # Jeżeli Q nie jest pusta, to usuwamy pierwszy Id z niej
            # i wysyłamy do tego procesu token
            # Wysyłanie do pierwszego Id jezeli Q niepuste
            if self.Q:
                # Wyciągnięcie pierwszego współpracownika z Q
                next_receiver = self.Q.pop(0)
                # Wysłanie do niego tokenu
                self.send_token(receiver=next_receiver)
            # Wychodzę z sekcji krytycznej
            self.in_cs = False
            myLogger.debug("Exited Critical Section. My id:" + self.my_id + ".")
    # Publikacja zaktualizowanej swojej wartości w tablicy RNi wysyłając żądanie tokenu
    def pub_REQUEST(self):
        # Tworzenie komunikatu REQUEST zawierającego Pi_id i RNi[i]
        snd_msg = ExchangeMsg(rcvfrom=self.my_id, rni=self.RNi[self.my_id])
        # Wysyłanie spakowanego komunikatu
        myLogger.debug("Sending REQUEST for token. My id:" + self.my_id + ".")
        sending_REQUEST_msg = pickle.dumps(snd_msg)
        # NOTE: Debugowanie komunikatu
        # myLogger.debug("Pickled Sending msg: " + str(sending_REQUEST_msg) + " Size: " + str(sys.getsizeof(sending_REQUEST_msg)) + ".")
        self.pub_sock.send(sending_REQUEST_msg)
    # Zdobycie dostępu do zasobu (współdzielonego obiektu danych)
    # jako wynik działania funkcji zwraca obiekt współdzielony
    def acquire(self):
        # Zamek na czas wchodzenia do Sekcji Krytycznej
        # lub wysyłania komunikatu REQUEST jeżeli nie mamy tokenu
        with self.lock:
            myLogger.debug("Trying to acquire... My id:" + self.my_id + ".")
            # Jezeli mam token to:
            if self.got_token:
                myLogger.debug("Already had token. My id:" + self.my_id + ".")
                # Wchodzę do sekcji krytycznej
                self.in_cs = True
                # Zwracam współdzielony obiekt 
                return self.shared_obj
            else:
                # W przeciwnym razie aktualizuję o 1 wartość tablicy RNi odpowiadającą i
                self.RNi[self.my_id]+=1
                # Publikacja zaktualizowanej wartości tablicy RNi odpowiadającą i
                # Wysyłając żądanie(i, sn) - sn to zaktualizowana wartość RNi[i]
                self.pub_REQUEST()
        # Jeżeli nie otrzymaliśmy obiektu to czekamy, 
        # aż wątek odbierający komunikaty odbierze token
        # innymi słowy
        # Blokujemy się w tym miejscu, aż w kolejce rcv_que będziemy 
        # mieli gotowy obiekt współdzielony (aż nie będzie wykonany put na self.rcv_que)
        myLogger.debug("Waiting for token... My id:" + self.my_id + ".")
        self.shared_obj = self.rcv_que.get(block=True)
        myLogger.debug("Got token. My id:" + self.my_id + ".")
        # Wchodzę do sekcji krytycznej
        self.in_cs = True
        # Zwracam współdzielony obiekt 
        return self.shared_obj


# Funkcja main do debugowania.
if __name__ == "__main__":
    # Start
    myLogger.debug("Starting... main in Distr_Monit.py.")