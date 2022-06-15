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


# Zaimplementowany algorytm wzajemnego wykluczania: suzuki-kasami
# https://www.geeksforgeeks.org/suzuki-kasami-algorithm-for-mutual-exclusion-in-distributed-system/
# Założenie - token wygląda następująco: 
# (znak '|' służy tylko rozdzieleniu poszczególnych składowych tokenu)
# |rozmiar(kolejki)|kolejka Q|
# |rozmiar(tablicy)|tablica LN|
# |rozmiar(zmiennych współdzielonych)|zmienne współdzielone|
# gdzie rozmiar ma ustaloną wielkość 32 bitów i oznacza rozmiar obiektu w nawiasach ()


# Implementacja tokenu:
# Funkcja do konwersji obiektu
def conv_obj():
    pass
# Funkcja do konwersji tokenu 
def conv_token():
    pass
# Przesyłany wymieniany token
class ExchangeToken():
    pass


# Monitor rozproszony
# Wykorzystujący do komunikacji PUB-SUB zmq
class DistributedMonitor():
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
        # identyfikatory pozostałych pracowników
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
    # Funkcja do odbierania wiadomości
    def receiver_fun(self):
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
        myLogger.debug("ZMQ Publisher initiated.")
        # TODO: oczekiwanie na współpracowników
        # TODO: funkcja odbiornika komunikatów
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
        pass
    # Zwolnienie dostępu do zasobu (współdzielonego obiektu danych)
    # funkcja nic nie zwraca - odsyła token 
    def release(self, shared_data_obj):
        myLogger.debug("Trying to acquire lock for release... My id:" + self.my_id)
        # Acquire lock try sth and then finall release
        with self.lock:
            myLogger.debug("Trying to release. My id:" + self.my_id)
            # Aktualizuję współdzielony obiekt 
            self.shared_obj = shared_data_obj
            # Po wykonaniu sekcji krytycznej:
            # Aktualizuję tablicę LN wartością RNi[i]
            self.LN[self.my_id] = self.RNi[self.my_id]
            # ~ AR ćw :
            # Dla każdego procesu Pj, którego Id nie ma
            # w kolejce żetonu (Q), dołącza jego Id do Q 
            # pod warunkiem: RNi[j] = LN[j]+1 (było nowe żądanie) 
            # TODO: Aktualizacja kolejki Q
            # ~ AR ćw:
            # Jeżeli Q nie jest pusta, to usuwamy pierwszy Id z niej
            # i wysyłamy do tego procesu token
            # TODO: Wysyłanie do pierwszego Id jezeli Q niepuste
            # Wychodzę z sekcji krytycznej
            self.in_cs = False
            myLogger.debug("Exited Critical Section. My id:" + self.my_id)
    # Zdobycie dostępu do zasobu (współdzielonego obiektu danych)
    # jako wynik działania funkcji zwraca obiekt współdzielony
    def acquire(self):
        myLogger.debug("Trying to acquire lock for acquire... My id:" + self.my_id)
        # Acquire lock try sth and then finall release
        with self.lock:
            # Jezeli mam token to:
            if self.got_token:
                myLogger.debug("Got token. CS = True. My id:" + self.my_id)
                # Wchodzę do sekcji krytycznej
                self.in_cs = True
                # Zwracam współdzielony obiekt 
                return self.shared_obj
            else:
                myLogger.debug("Update RNi and wait for token. My id:" + self.my_id)
                # W przeciwnym razie aktualizuję o 1 tablicę RN
                self.RNi[self.my_id]+=1
                # TODO: publikacja zaktualizowanej tablicy RN
        # Jeżeli nie otrzymaliśmy obiektu to czekamy, 
        # aż wątek odbierający komunikaty odbierze token
        # Blokujemy się w tym miejscu, aż w kolejce będziemy 
        # mieli gotowy obiekt współdzielony
        myLogger.debug("Waiting for token. My id:" + self.my_id)
        self.shared_obj = self.rcv_que.get(block=True)
        myLogger.debug("Got token. CS = True. My id:" + self.my_id)
        # Wchodzę do sekcji krytycznej
        self.in_cs = True
        # Zwracam współdzielony obiekt 
        return self.shared_obj


# Funkcja main do debugowania.
if __name__ == "__main__":
    # Start
    myLogger.debug("Starting... main in Distr_Monit.py")
    # DistributedMonitor(1,True,[1, 1]).start_zmq() # Debug ctx