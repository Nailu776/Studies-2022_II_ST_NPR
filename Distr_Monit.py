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
# Sys dla sprawdzania wielości obiektów - wiadomości przy debugowaniu komunikatów
# import sys
# Pakowanie - picklowanie obiektu pythona do binarnych danych [6] 
import pickle


# Przesyłana wiadomość - token albo aktualizacja RNi lub sleep/wake
class ExchangeMsg():
    def __init__(self, rcvfrom, Q=None, LN=None, 
        SD=None, sendto=None, rni=None):
        # NOTE: Jeżeli przyszła do nas wiadomość
        # W przypadku 1: jeżeli rcvfrom is None - to jest to wiadomość wake up
        # W przypadku 1.1: jeżeli jest sendto == None to wszyscy są budzeni, a jeżeli jest sprecyzowany to ktoś konkretny
        # W przypadku 2: Jeżeli rcvfrom jest sprecyzowane oraz rni jest sprecyzowane - to aktualizacja rni
        # W przypadku 3: Jeżeli rcvfrom jest, rni nie, a sendto jest - to przesyłany jest token 
        # W przypadku 4: Jeżeli rcvfrom jest, rni nie, a sendto nie - to jest to wiadomość idę spać sleep
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
        

# Monitor rozproszony wykorzystujący:
# Do komunikacji - mechanizm ZMQ PUB-SUB
# Do wzajemnego wykluczania - algorytm suzuki-kasami 
class DistributedMonitor():
    # Init monitora rozproszonego
    def __init__(self, id_ip_port, is_token_acquired, coworkers, init_shared_data):
        # Zmiana nazwy loggera na identyfikator 
        myLogger.name = "ID: " + id_ip_port
        # Zaimplementowany algorytm wzajemnego wykluczania: suzuki-kasami [0]
        # (~AR_ćw)
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
        self.shared_obj = init_shared_data
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
        # NOTE: Rozszerzenie mechanizmu release i acquire  
        # o  sleep i wakeupOne / wakeupAll
        self.sleeping_list = []
        self.am_i_sleeping = False
        # Wykorzystanie blokowania Get, i ustawiania Put w wątku w tle do budzenia
        self.wake_up_call = queue.Queue(1)
        # Init komunikacji ZMQ
        self.start_zmq()
    # Koniec pracy przy współdzielonej zmiennej
    def end_work(self):
        # NOTE: PROBLEM ZGUBIONEGO TOKENU 
        # Kiedy ktoś się niespodziewanie rozłączy
        myLogger.debug("Adios.")
        # Zatrzymanie komunikacji
        self.stop_zmq()
    # Inicjalizacja publishera
    def publisher_init(self):
        # Utworzenie gniazda publikującego [7]
        # Kontekst Publishera
        pub_ctx = zmq.Context()
        # Gniazdo Publishera
        self.pub_sock = pub_ctx.socket(zmq.PUB)
        # Łączenie gniazda z my_id --> IP:PORT
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
        snd_msg = ExchangeMsg(
            # Nadawca
            rcvfrom=self.my_id,
            # Zawartość tokenu 
            Q=self.Q, LN=self.LN, SD=self.shared_obj,
            # Odbiorca tokenu
            sendto=receiver)
        sending_token_msg = pickle.dumps(snd_msg)
        # NOTE: Debugowanie komunikatu
        # myLogger.debug("Pickled Sending msg: " + str(sending_token_msg) + " Size: " + str(sys.getsizeof(sending_token_msg)) + ".")
        # Wysyłanie spakowanego komunikatu
        myLogger.debug("Sending token from: " + self.my_id + " to: " + receiver + ".")
        self.pub_sock.send(sending_token_msg)
        myLogger.debug("Token sent from: " + self.my_id + " to: " + receiver + ".")
    # Obsługa komunikatu otrzymywania tokenu
    def getting_token_handler(self, unpickled_msg, rcvfrom_id):  
        myLogger.debug("Received token from: "+ rcvfrom_id)
        # Aktualizujemy swoje wartości Q i LN wartościami z tokenu
        self.Q = unpickled_msg.Q
        self.LN = unpickled_msg.LN
        # Wchodzę do sekcji krytycznej (po to prosiłem o token)
        self.in_cs = True
        # Ustawiamy flagę posiadania tokenu na True
        self.got_token = True
        # Wstawiamy go do Kolejki by czekając getem dostać SharedData
        self.rcv_que.put(unpickled_msg.SD)
    # Obsługa komunikatu RNi update
    def rni_update_handler(self, unpickled_msg, rcvfrom_id):
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
    # Obsługa komunikatu wakeupcall
    def wake_up_call_handler(self, unpickled_msg):
        # Jeżeli to wiadomość do mnie (wakeup)
        if unpickled_msg.sendto == self.my_id:
            # Jeśli śpię to oznacza, że mam się obudzić
            if self.am_i_sleeping:
                self.am_i_sleeping = False
                # Wstajemy
                myLogger.debug("Waking up.")
                self.wake_up_call.put(True)
            else: 
                myLogger.warn("Received wake up msg, but I am awake.")
        # Jeżeli to wiadomość do wszystkich
        elif unpickled_msg.sendto is None:
            # Jeśli śpię to oznacza, że mam się obudzić
            if self.am_i_sleeping:
                self.am_i_sleeping = False
                # Wstajemy
                myLogger.debug("Waking up.")
                self.wake_up_call.put(True)
            # Wyczyść listę śpiących
            self.sleeping_list.clear()
            myLogger.debug("Cleared sleeping list.")
        # Wiadomość do konkretnej osoby
        else:
            # Usuwamy ją z listy śpiących osób
            if unpickled_msg.sendto in self.sleeping_list:
                self.sleeping_list.remove(unpickled_msg.sendto)
                myLogger.debug("Removed from sleeping list: " + str(unpickled_msg.sendto))
            else:
                myLogger.warn("This process is not in my sleeping list: " + str(unpickled_msg.sendto))
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
                    # myLogger.debug("Received msg from: " + str(rcvfrom_id))
                    # Jeżeli Id nadawcy jest niczym to otrzymaliśmy wake up call
                    if rcvfrom_id is None:
                        self.wake_up_call_handler(unpickled_msg=unpickled_msg)
                    # Jeżeli pole rni nie jest niczym - dostaliśmy REQUEST (prośbę o token)
                    elif unpickled_msg.rni is not None:
                        self.rni_update_handler(unpickled_msg=unpickled_msg,rcvfrom_id=rcvfrom_id)
                    # W przeciwnym wypadku chodzi o token (rni is None) lub sleep 
                    # Jeżeli do nas szła wiadomość to przyjmujemy token
                    elif unpickled_msg.sendto == self.my_id:
                        self.getting_token_handler(unpickled_msg=unpickled_msg,rcvfrom_id=rcvfrom_id)
                    # Jeżeli wiadomość była wysłana do wszystkich (sendto is None)  
                    # Ale (co wcześniej ustaliliśmy) RNi jest puste
                    # oraz Rcvfrom nie jest puste to jest to wiadomość sleep 
                    elif unpickled_msg.sendto is None:
                        # NOTE: Obsługa komunikatu sleep
                        # Dodajemy go na listę śpiących osób
                        self.sleeping_list.append(rcvfrom_id)
        # Jeżeli self.rcv_running jest ustawione na False
        # to wychodzimy z pętli while self.rcv_running
        # Zamykamy gniazdo subskrybenta
        self.sub_sock.close()
        myLogger.debug("ZMQ stopped.")
    # Funkcja oczekiwania, aż współpracownik będzie możliwy do połączenia
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
            myLogger.debug("Trying to release SD.")
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
            myLogger.debug("Exited Critical Section.")
    # Publikacja zaktualizowanej swojej wartości w tablicy RNi wysyłając żądanie tokenu
    def pub_REQUEST(self):
        # Tworzenie komunikatu REQUEST zawierającego Pi_id i RNi[i]
        snd_msg = ExchangeMsg(rcvfrom=self.my_id, rni=self.RNi[self.my_id])
        sending_REQUEST_msg = pickle.dumps(snd_msg)
        # NOTE: Debugowanie komunikatu
        # myLogger.debug("Pickled Sending msg: " + str(sending_REQUEST_msg) + " Size: " + str(sys.getsizeof(sending_REQUEST_msg)) + ".")
        # Wysyłanie spakowanego komunikatu
        myLogger.debug("Sending REQUEST for token.")
        self.pub_sock.send(sending_REQUEST_msg)
    # Zdobycie dostępu do zasobu (współdzielonego obiektu danych)
    # jako wynik działania funkcji zwraca obiekt współdzielony
    def acquire(self):
        # Zamek na czas wchodzenia do Sekcji Krytycznej
        # lub wysyłania komunikatu REQUEST jeżeli nie mamy tokenu
        with self.lock:
            myLogger.debug("Trying to acquire...")
            # Jezeli mam token to:
            if self.got_token:
                myLogger.debug("Already had token.")
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
        myLogger.debug("Waiting for token...")
        self.shared_obj = self.rcv_que.get(block=True)
        myLogger.debug("Got token.")
        # NOTE: Jeżeli otrzymaliśmy token to już jesteśmy w sekcji krytycznej
        # bo po to otrzymywaliśmy token
        # Zwracam współdzielony obiekt 
        return self.shared_obj
    # Wysłanie wiadomości obudźcie mnie jak coś się stanie
    def send_sleep(self):
        # Tworzenie komunikatu Sleep zawierającego tylko rcvfrom
        snd_msg = ExchangeMsg(rcvfrom=self.my_id)
        sending_wake_me_msg = pickle.dumps(snd_msg)
        # NOTE: Debugowanie komunikatu
        # myLogger.debug("Pickled Sending msg: " + str(sending_wake_me_msg) + " Size: " + str(sys.getsizeof(sending_wake_me_msg)) + ".")
        # Wysyłanie spakowanego komunikatu
        myLogger.debug("Sending Sleep.")
        self.pub_sock.send(sending_wake_me_msg)
    # Jeżeli z jakiś powodów proces nie może teraz przetwarzać zmiennej współdzielonej
    # (np. odebraną zmienną jest bufor, który jest pusty i nie można z niego nic pobrać)
    # to proces zasypia i informuje o tym resztę współpracowników (procesów)
    def going_sleep(self, shared_data_obj):
        # Próbuję oddać token (wychodzę z sekcji krytycznej)
        myLogger.debug("Release before sleep.")
        self.release(shared_data_obj)
        with self.lock:
            # Wysyłam wiadomość obudźcie mnie jak coś się stanie
            self.send_sleep()
            self.am_i_sleeping = True
        # Zatrzymuję się, aż do wiadomości wakeup w wątku pobocznym odbiornika
        return self.wake_up_call.get(block=True)
    # Jeżeli z jakiś powodów proces chce kogoś obudzić (np. dodał coś do współdzielonego bufora)
    # to proces wysyła komunikat budzenia jednego procesu, żeby wybudzić pierwszy znany mu śpiacy proces
    def wake_up(self):
        with self.lock:
            # Tworzenie komunikatu wakeup zawierającego tylko sendto
            if self.sleeping_list:
                snd_msg = ExchangeMsg(rcvfrom=None, sendto=self.sleeping_list.pop(0))
                sending_wake_up_msg = pickle.dumps(snd_msg)
                # NOTE: Debugowanie komunikatu
                # myLogger.debug("Pickled Sending msg: " + str(sending_wake_up_msg) + " Size: " + str(sys.getsizeof(sending_wake_up_msg)) + ".")
                # Wysyłanie spakowanego komunikatu
                myLogger.debug("Sending WakeUp.")
                self.pub_sock.send(sending_wake_up_msg)
            else:
                myLogger.debug("As far as I know... nobody is sleeping.")
    # Podobnie jak metoda wake_up() z tą różnicą, że komunikat jest wysyłany do wszystkich,
    # aby każdy proces, który aktualnie "śpi" został wybudzony
    def wake_up_all(self):
        with self.lock:
            # Tylko jeżeli ktoś śpi
            if self.sleeping_list:
                # Tworzenie komunikatu wakeupall (wszystko na None)
                snd_msg = ExchangeMsg(rcvfrom=None, sendto=None)
                sending_wake_up_all_msg = pickle.dumps(snd_msg)
                # NOTE: Debugowanie komunikatu
                # myLogger.debug("Pickled Sending msg: " + str(sending_wake_up_all_msg) + " Size: " + str(sys.getsizeof(sending_wake_up_all_msg)) + ".")
                # Wysyłanie spakowanego komunikatu
                myLogger.debug("Sending WakeUpALL.")
                self.pub_sock.send(sending_wake_up_all_msg)
            else:
                myLogger.debug("As far as I know... nobody is sleeping.")
    # Opakowanie (z ang. wrapper) na funkcje: going_sleep(), wake_up() oraz wake_up_all(), 
    # aby ich nazwy były bardziej intuicyjne (dla innych programistów):
    # NOTE: metoda going_sleep() umożliwia edycję zmiennej w przeciwieństwie do wait()
    # w metodzie wait() oddawana zmienna współdzielona będzie niezmieniona
    # Odpowiednik going_sleep()
    def wait(self):
        # Ignoruje jakiekolwiek zmiany w obiekcie współdzielonym
        # Oddajemy do systemu obiekt, który dostaliśmy
        self.going_sleep(self.shared_obj)
    # Odpowiednik wake_up()
    def notify(self):
        self.wake_up()
    # Odpowiednik wake_up_all()
    def notifyAll(self):
        self.wake_up_all()


# Funkcja main do debugowania.
if __name__ == "__main__":
    # Start
    myLogger.debug("Starting... main in Distr_Monit.py.")