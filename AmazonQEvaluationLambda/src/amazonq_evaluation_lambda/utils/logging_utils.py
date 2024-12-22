import logging


def setup_logging(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger
