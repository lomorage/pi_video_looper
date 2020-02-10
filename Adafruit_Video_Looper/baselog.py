import logging

def getlogger(modname):
    # logger
    logger = logging.getLogger(modname)
    logger.setLevel(logging.DEBUG)
    # create console handler and set level to debug
    #ch = logging.StreamHandler()
    ch = logging.FileHandler('/tmp/lomo-frame.log')
    ch.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)
    return logger
