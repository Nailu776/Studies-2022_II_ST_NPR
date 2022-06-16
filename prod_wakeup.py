# Wyłączenie programu
import sys
import signal
# Przetrzywanie zasobu na chwilę
import time
# Logowanie informacji
from Logger import logger as myLogger
# Implementacja Rozproszonego Monitora
from Distr_Monit import DistributedMonitor


# End of program - sigint
def signal_handler(sig, frame):
    myLogger.info("You pressed Ctrl+C! End of program.")
    # Zakończ pracę
    dMonitor.end_work()
    sys.exit(0)


# Funkcja main.
if __name__ == "__main__":
    # Init rozproszonego monitora
    dMonitor = DistributedMonitor(sys.argv[2], sys.argv[1], sys.argv[2:])
    # Handler zakończenia CTRL+C
    signal.signal(signal.SIGINT, signal_handler)
    # Produkuj liczby od 1 do 5
    liczba = 0
    while True:
        # Zdobądź dostęp do zasobu
        produkt = dMonitor.acquire()
        # Modyfikuj zasób
        liczba +=1
        if not produkt:
            produkt = [liczba]
            myLogger.info("Produkuje produkt: " + str(produkt))
        else:
            produkt.append(liczba)
            myLogger.info("Produkuje produkt: " + str(produkt))
        # Przetrzymaj przez chwilę zasób
        time.sleep(1)
        # Obudź 1 osobę, jeżeli jakaś śpi
        dMonitor.notify()
        # Zwolnij zasób
        dMonitor.release(produkt)
        # Poczekaj z kolejną produkcją (aby przetestować czekanie konsumentów)
        time.sleep(3)
        # Sprawdź czy już wystarczająco dużo popracowałeś z zasobem
        if liczba == 5:
            myLogger.info("Wyprodukowano: "+str(liczba)+".")
            # Zakończ pracę
            dMonitor.end_work()
            sys.exit(0)