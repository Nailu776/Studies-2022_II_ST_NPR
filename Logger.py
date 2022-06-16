# plik Logger.py 
# zawiera ustawienia logger'a
import logging


# Ustawienia logowania informacji
logger = logging.getLogger('dist_monit')
logger.setLevel(logging.INFO)
FORMAT = '[ %(levelname)s\t%(asctime)s %(name)s ] %(message)s'
logging.basicConfig(format=FORMAT, datefmt='%m/%d/%Y %I:%M:%S %p')