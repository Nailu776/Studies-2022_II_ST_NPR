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
    dMonitor = DistributedMonitor(sys.argv[2], sys.argv[1], sys.argv[2:], [0])
    # Handler zakończenia CTRL+C
    signal.signal(signal.SIGINT, signal_handler)
    i = 0
    while True:
        # Zdobądź dostęp do zasobu
        produkt = dMonitor.acquire()
        # Modyfikuj zasób jeżeli jest co modyfikować
        if produkt:
            i = 0
            myLogger.info("Konsumuje produkt: " + str(produkt.pop(0)) + ".")
            # Przetrzymaj przez chwilę zasób
            time.sleep(1)
            # Zwolnij zasób
            dMonitor.release(produkt)
        else:
            i+=1
            myLogger.info("Nie ma nic już " + str(i) + " raz z rzędu.")
            # Przetrzymaj przez chwilę zasób
            time.sleep(1)
            # Idź spać, aż będzie coś do zmodyfikowania
            dMonitor.wait()
        # Jeżeli 3 razy nic się nie pojawiło do skonsumowania to wychodzimy
        if i >=3:
            myLogger.info("Nie ma tutaj nic dla mnie 3 razy z rzędu.")
            # Zakończ pracę
            dMonitor.end_work()
            sys.exit(0)