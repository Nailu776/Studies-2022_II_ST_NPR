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
        self.RN = {n: 0 for n in self.coworkers_list}
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
        pass
    # Zatrzymanie mechanizmu publikacji tokenu
    def stop_zmq(self):
        pass
    # Wysłanie tokenu
    def send_token(self, receiver):
        pass
    # Zwolnienie dostępu do zasobu (współdzielonego obiektu danych)
    # funkcja nic nie zwraca - odsyła token 
    def release(self, shared_data_obj):
        pass
    # Zdobycie dostępu do zasobu (współdzielonego obiektu danych)
    # jako wynik działania funkcji zwraca obiekt współdzielony
    def acquire(self):
        pass


# Funkcja main do debugowania.
if __name__ == "__main__":
    # Start
    myLogger.debug("Starting... main in Distr_Monit.py")