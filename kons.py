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


class Product():
    def __init__(self):
        self.buffer = []
        self.counter = 0
    def add(self, num):
        self.buffer.append(num)
        self.counter +=1
    def rm(self):
        self.counter -=1
        return self.buffer.pop(0)
    def exists(self):
        return bool(self.counter)

# Funkcja main.
if __name__ == "__main__":
    # Init rozproszonego monitora
    dMonitor = DistributedMonitor(sys.argv[2], sys.argv[1], sys.argv[2:], Product())
    # Handler zakończenia CTRL+C
    signal.signal(signal.SIGINT, signal_handler)
    i = 0
    while True:
        # Zdobądź dostęp do zasobu
        produkt = dMonitor.acquire()
        # Modyfikuj zasób
        if produkt.exists():
            i = 0
            myLogger.info("Konsumuje produkt: " + str(produkt.rm()) + ".")
        else:
            i+=1
            myLogger.info("Nie ma nic już " + str(i) + " raz.")
        # Przetrzymaj przez chwilę zasób
        time.sleep(1)
        # Zwolnij zasób
        dMonitor.release(produkt)
        # Jeżeli 3 razy nic się nie pojawiło do skonsumowania to wychodzimy
        if i >=3:
            myLogger.info("Nie ma tutaj nic dla mnie 3 razy z rzędu.")
            # Zakończ pracę
            dMonitor.end_work()
            sys.exit(0)