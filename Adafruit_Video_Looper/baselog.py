import logging
from logging.handlers import RotatingFileHandler

def getlogger(modname):
    # logger
    logger = logging.getLogger(modname)
    logger.setLevel(logging.DEBUG)

    ch = RotatingFileHandler('/opt/lomorage/var/lomo-frame.log', maxBytes=10*1024*1024, backupCount=5)
    ch.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)
    return logger
