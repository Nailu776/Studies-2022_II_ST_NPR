# 0. 2022_II_ST_NPR
Repozytorium przeznaczone na przedmiot Narzędzia Przetwarzania Rozproszonego (NPR) na drugim stopniu studiów.

## 1. Implementacja rozproszonego monitora w ØMQ
### 1.0 Wymagania
 - Python
 - PyZmq (https://github.com/zeromq/pyzmq)
 ```
 $ pipenv install pyzmq
 ```
### 1.1 Krótki opis implementacji
W skład implementacji (znajdującej się w pliku *Distr_Monit.py*) wchodzą dwa obiekty:  
 - ExchangeMsg() --> Komunikat wymiany, który służy do tworzenia wiadomości,  
 przesyłanych pomiędzy procesami.
 - DistributedMonitor() --> Rozproszony monitor, oferujący mechanizm synchronizacji  
 w systemie rozproszonym bazujący głównie na funkcji acquire (zdobycia dostępu do zasobu)  
 oraz funkcji release (zwolnienie dostępu do zasobu).  
 Do komunikacji międzyprocesowej wykorzystuje mechanizm ZeroMQ (0MQ) w schemacie PUB-SUB.  
 Zaimplementowany algorytm wzajemnego wykluczania: suzuki-kasami.
### 1.2 Opis klasy ExchangeMsg()
```python
# Przesyłana wiadomość
class ExchangeMsg():
    def __init__(self, rcvfrom, Q=None, LN=None, 
        SD=None, sendto=None, rni=None):
        # Nadawca wiadomości (od kogo odebraliśmy wiadomość)
        self.rcvfrom = rcvfrom
        # Zaktualizowana wartość tablicy RNi[rcvfrom]
        self.rni = rni
        # Kolejka procesów żądających tokenu
        self.Q = Q
        # Tablica LN zawierająca lp. ostatnio wykonywanych żądań
        self.LN = LN
        # Shared_Data - zmienna/obiekt współdzielony
        self.SD = SD
        # Odbiorca wiadomości (do kogo wiadomość wysyłamy)
        self.sendto = sendto 
# Przesyłane są komunikaty 4 typów (rozróżniane na podstawie warunków ich zawartości):
#   1.0 Komunikat budzenia - Warunki: rcvfrom = None
#       1.1 sendto = None --> wszystkie procesy oczekujące [metodą going_sleep() lub wait()]
#       są budzone, aby mogły wznowić przetwarzanie.
#       1.2 sendto jest sprecyzowane --> konkretny proces wznawia przetwarzanie.
#   2.0 Komunikat aktualizacji tablicy RN - Warunki: rcvfrom i rni jest sprecyzowane.
#   3.0 Komunikat przesłania tokenu - Warunki: rcvfrom i sendto jest sprecyzowane, a rni = None.
#   4.0 Komunikat zasypiania - Warunki: rcvfrom jest sprecyzowane, a rni i sendto jest równe None.      
```
### 1.3 Opis klasy DistributedMonitor()
#### 1.3.1 Wstęp
```python
# Monitor rozproszony wykorzystujący:
# Do komunikacji - mechanizm ZMQ PUB-SUB
# Do wzajemnego wykluczania - algorytm suzuki-kasami 
class DistributedMonitor():
    # Init monitora rozproszonego (fr. implementacji)
    def __init__(self, id_ip_port, is_token_acquired, coworkers, init_shared_data):
        # Init zmiennych wykorzystywanych w algorytmie suzuki-kasami oraz przy komunikacji zmq
        # (...)
    # Init rozproszonego monitora (wykorzystanie)
    myDistributedMonitor = DistributedMonitor(
        id_ip_port, # łańcuch znaków: "AdresIP:PORT" wykorzystywany przez dany proces do komunikacji 
        is_token_acquired, # wartość boolowska True or False wykorzystywana do poinformowania, 
        # czy dany proces zaczyna pracę nad współdzielonymi danymi w systemie posiadając token. 
        coworkers, # lista wszystkich identyfikatorów współpracowników (z aktualnym procesem włącznie)
        init_shared_data # początkowa wartość/obiekt zmiennej współdzielonej  
        )
```
Po utworzeniu obiektu monitora rozproszonego "myDistributedMonitor" rozpoczyna się próba podłączenia 
do systemu rozproszonego. Inicjowane jest gniazdo publikujące oraz subskrybujące, a także oczekiwanie 
na podłączenie się wszystkich współpracowników do systemu i połączenie do nich gniazda subskrybenta. 
W wątku demonicznym działającym w tle odbierane i przetwarzane są komunikaty (opisane w pkt. 1.2.).  
#### 1.3.2 Funkcje użytkowe
```python
    # Zdobycie dostępu do zasobu (zmiennej współdzielonej)
    # Wynik działania funkcji: zwrócenie zmiennej współdzielonej
    # NOTE: Funkcja będzie w stanie się zablokować,
    # jeżeli proces nie posiada tokenu, aż wątek odbiornika
    # odbierze token (zawierający zmienną współdzieloną)
    def acquire(self): 
        #(...)
    # Zwolnienie dostępu do zasobu (zmiennej współdzielonej)
    # Wynik działania funkcji: funkcja nic nie zwraca,
    # wychodzi z sekcji krytycznej i odsyła token, jeżeli ktoś o niego aktualnie prosi
    def release(self, shared_data_obj):
        #(...)
    # Jeżeli z jakiś powodów proces nie może teraz przetwarzać zmiennej współdzielonej
    # (np. odebraną zmienną jest bufor, który jest pusty i nie można z niego nic pobrać)
    # to proces zasypia i informuje o tym resztę współpracowników (procesów)
    def going_sleep(self, shared_data_obj): 
        #(...)
    # Jeżeli z jakiś powodów proces chce kogoś obudzić (np. dodał coś do współdzielonego bufora)
    # to proces wysyła komunikat budzenia jednego procesu, żeby wybudzić pierwszy znany mu śpiacy proces
    def wake_up(self): 
        #(...)
    # Podobnie jak metoda wake_up() z tą różnicą, że komunikat jest wysyłany do wszystkich,
    # aby każdy proces, który aktualnie "śpi" został wybudzony
    def wake_up_all(self): 
        #(...)
    # Opakowanie (z ang. wrapper) na funkcje: going_sleep(), wake_up() oraz wake_up_all(), 
    # aby ich nazwy były bardziej intuicyjne (dla innych programistów):
    # NOTE: metoda going_sleep() umożliwia edycję zmiennej w przeciwieństwie do wait()
    # w metodzie wait() oddawana zmienna współdzielona będzie niezmieniona
    # Odpowiednik going_sleep()
    def wait(self): 
        #(...)
    # Odpowiednik wake_up()
    def notify(self): 
        #(...)
    # Odpowiednik wake_up_all()
    def notifyAll(self): 
        #(...)
```
Mechanizm synchronizacji oparty tylko na metodach acquire() i release() nie umożliwia 
prostego sposobu na usprawnienie systemu rozproszonego w scenariuszu, gdy proces otrzymuje 
dostęp do zmiennej współdzielonej, która nie może zostać przez niego przetworzona (np. bufor jest pusty). 
W takim przypadku proces po oddaniu dostępu do zmiennej współdzielonej (metodą release()) 
może ponownie próbować otrzymać dostęp (metodą acquire()) do zmiennej, której wciąż nie będzie w stanie przetworzyć. 
Do tego typu przypadków przydatne są metody going_sleep() oraz wait(), które umożliwiają "poczekanie" 
na komunikat o zmianie stanu zmiennej współdzielonej wysyłany przez inny proces za pomocą metod notify() lub notifyAll() 
[lub analogicznie wake_up()/wake_up_all()].  


### 1.4 Przykłady problemu producenta konsumenta
Do przetestowania poprawności implementacji przygotowane zostały przeze mnie przykłady problemu producenta konsumenta.  
### 1.4.1 Podstawowy (wykorzystanie wyłącznie metod acquire() oraz release())
W pliku *kons.py* znajduje się przykładowy konsument produktu Produkt(), który jest obiektem bufora zawierającym 
tablicę oraz licznik elementów w tablicy. Konsument próbuje konsumować współdzielony między procesami produkt, 
a po 3 nieudanych próbach konsumpcji z rzędu kończy swoją pracę w systemie. 
Czas konsumpcji produktu jest wydłużony o 1 sekunde, w celu lepszego zaobserwowania przetrzymywania zasobu.  
W pliku *prod.py* znajduje się przykładowy producent produktu Produkt(), który wstawia do produktu liczby od 1 do 5 
i kończy swoje działanie. Czas produkcji produktu jest wydłużony o 1 sekunde, 
w celu lepszego zaobserwowania przetrzymywania zasobu.  
*Parametry wywołania:*  
[Posiadanie przez proces tokenu: 1/0] [ID procesu --> "IP:PORT"] [lista ID innych procesów --> "IP:PORT"]  
*Zasada uruchomienia:*  
```
# Bardzo prosty przykład producenta konsumenta
pipenv run python prod.py 1 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772  
pipenv run python prod.py 0 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777  
pipenv run python prod.py 0 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776  
pipenv run python kons.py 0 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775   
pipenv run python kons.py 0 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774  
pipenv run python kons.py 0 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773  
```
### 1.4.2 Wydajniejszy (wykorzystanie dodatkowo metod wait() oraz notifyAll())
W pliku *kons_sleep.py* znajduje się przykładowy konsument produktu, którym jest tablica wartości (bufor). 
Konsument próbuje konsumować jedną wartość ze współdzielonego między procesami produktu, 
a po 3 nieudanych próbach konsumpcji z rzędu kończy swoją pracę w systemie. 
Czas konsumpcji produktu jest wydłużony o 1 sekunde, w celu lepszego zaobserwowania przetrzymywania zasobu. 
Dodatkowo w przypadku nieudanej konsumpcji wywoływana jest metoda wait(), 
aby poczekać na zmianę stanu współdzielonej zmiennej.  
W pliku *prod_wakeupall.py* znajduje się przykładowy producent produktu Produkt(), który wstawia do produktu liczby od 1 do 5 
i kończy swoje działanie. Dodatkowo po wstawieniu do produktu liczby wywoływana jest metoda notifyAll(), 
która budzi wszystkich śpiących konsumentów.  
*Parametry wywołania:*  
[Posiadanie przez proces tokenu: 1/0] [ID procesu --> "IP:PORT"] [lista ID innych procesów --> "IP:PORT"]  
*Zasada uruchomienia:*  
```
# Przykład producenta konsumenta z możliwością czekania na pojawienie się produktu i budzeniem wszystkich oczekujących konsumentów
pipenv run python prod_wakeupall.py 1 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772  
pipenv run python prod_wakeupall.py 0 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777  
pipenv run python prod_wakeupall.py 0 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776  
pipenv run python kons_sleep.py 0 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775   
pipenv run python kons_sleep.py 0 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774  
pipenv run python kons_sleep.py 0 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773  
```
### 1.4.3 Wykorzystanie metody notify() zamiast notifyAll() 
W pliku *kons_sleep.py* znajduje się przykładowy konsument produktu, którym jest tablica wartości (bufor). 
Konsument próbuje konsumować jedną wartość ze współdzielonego między procesami produktu, 
a po 3 nieudanych próbach konsumpcji z rzędu kończy swoją pracę w systemie. 
Czas konsumpcji produktu jest wydłużony o 1 sekunde, w celu lepszego zaobserwowania przetrzymywania zasobu. 
Dodatkowo w przypadku nieudanej konsumpcji wywoływana jest metoda wait(), 
aby poczekać na zmianę stanu współdzielonej zmiennej.  
W pliku *prod_wakeup.py* znajduje się przykładowy producent produktu Produkt(), który wstawia do produktu liczby od 1 do 5 
i kończy swoje działanie. Dodatkowo po wstawieniu do produktu liczby wywoływana jest metoda notify(), 
która budzi jeden ze śpiących konsumentów (który jest znany danemu producentowi).  
*Parametry wywołania:*  
[Posiadanie przez proces tokenu: 1/0] [ID procesu --> "IP:PORT"] [lista ID innych procesów --> "IP:PORT"]  
*Zasada uruchomienia:*   
```
# Przykład producenta konsumenta z możliwością czekania na pojawienie się produktu oraz budzenia, 
# ale budzony jest tylko 1 proces na raz (przez inny proces) 
pipenv run python prod_wakeup.py 1 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772  
pipenv run python prod_wakeup.py 0 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777  
pipenv run python prod_wakeup.py 0 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776  
pipenv run python kons_sleep.py 0 127.0.0.1:7774 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775   
pipenv run python kons_sleep.py 0 127.0.0.1:7773 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774  
pipenv run python kons_sleep.py 0 127.0.0.1:7772 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775 127.0.0.1:7774 127.0.0.1:7773  
```
### 1.4.4 Mniejsza ilość procesów 
*Zasada uruchomienia poprzednich przykładów z 2 konsumentami i 1 producentem:* (do testowania)    
```
# Mniejsza ilość procesów
# Podstawowa
pipenv run python prod.py 1 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775
pipenv run python kons.py 0 127.0.0.1:7776 127.0.0.1:7777 127.0.0.1:7775
pipenv run python kons.py 0 127.0.0.1:7775 127.0.0.1:7777 127.0.0.1:7776
# notifyAll()
pipenv run python prod_wakeupall.py 1 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775
pipenv run python kons_sleep.py 0 127.0.0.1:7776 127.0.0.1:7777 127.0.0.1:7775
pipenv run python kons_sleep.py 0 127.0.0.1:7775 127.0.0.1:7777 127.0.0.1:7776
# notify()
pipenv run python prod_wakeup.py 1 127.0.0.1:7777 127.0.0.1:7776 127.0.0.1:7775
pipenv run python kons_sleep.py 0 127.0.0.1:7776 127.0.0.1:7777 127.0.0.1:7775
pipenv run python kons_sleep.py 0 127.0.0.1:7775 127.0.0.1:7777 127.0.0.1:7776
```
