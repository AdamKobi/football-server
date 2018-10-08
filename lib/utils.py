import logging
import yaml


def init_logging(mod_name):
    """
    To use this, do logger = init_logging(__name__)
    """
    logger = logging.getLogger(mod_name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
 
 
def get_cfg(filename):
    with open(filename, 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
    return cfg