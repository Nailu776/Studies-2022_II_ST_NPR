# plik Distr_Monit.py 
# zawiera implementację monitora rozproszonego (Distributed Monitor)
# napisaną w języku programowania python


# Importy:
from Logger import logger as myLogger


# Zaimplementowany algorytm wzajemnego wykluczania: suzuki-kasami
# https://www.geeksforgeeks.org/suzuki-kasami-algorithm-for-mutual-exclusion-in-distributed-system/
# Założenie - token wygląda następująco: 
# (znak '|' służy tylko rozdzieleniu poszczególnych składowych tokenu)
# |rozmiar(kolejki)|kolejka|
# |rozmiar(tablicy)|tablica|
# |rozmiar(zmiennych współdzielonych)|zmienne współdzielone|
# gdzie rozmiar ma ustaloną wielkość 32 bitów i oznacza ilość bajtów obiektu w nawiasach ()


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
        pass
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