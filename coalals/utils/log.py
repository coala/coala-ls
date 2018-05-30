import logging
from sys import stderr


def configure_logger():  # pragma: no cover
    logging.basicConfig(stream=stderr, level=logging.INFO)


def reset_logger(logger=None):  # pragma: no cover
    logger = logging.getLogger() if logger is None else logger
    for handler in logger.handlers[:]:
        handler.removeHandler()

    configure_logger()
