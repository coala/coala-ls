import logging
from sys import stderr


def configure_logger():  # pragma: no cover
    """
    Configure logging to stream to stderr to not
    interfere with the stdio mode of the server.
    """
    logging.basicConfig(stream=stderr, level=logging.INFO)


def reset_logger(logger=None):  # pragma: no cover
    """
    Reset the logger while removing all the handlers.
    This can reset the logger when it has been interfered
    with some other logging configuration.

    :param logger:
        The logger to reset configuration.
    """
    logger = logging.getLogger() if logger is None else logger
    for handler in logger.handlers[:]:
        handler.removeHandler()

    configure_logger()
