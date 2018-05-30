from sys import argv, stdout
from .main import main
from .utils.log import configure_logger

import logging
configure_logger()

if __name__ == '__main__':
    main()
