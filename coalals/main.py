import sys
from socketserver import TCPServer
from argparse import ArgumentParser

from coala_utils.decorators import enforce_signature
from .utils.wrappers import StreamHandlerWrapper
from .langserver import LangServer

import logging
logger = logging.getLogger(__name__)


@enforce_signature
def start_tcp_lang_server(handler_class: LangServer, bind_addr, port):
    wrapper_class = type(
        handler_class.__name__ + 'Handler',
        (StreamHandlerWrapper,),
        {'DELEGATE_CLASS': handler_class, },
    )

    try:
        server = TCPServer((bind_addr, port), wrapper_class)
    except Exception as e:
        logger.fatal('Fatal Exception: %s', e)
        sys.exit(1)

    logger.info('Serving %s on (%s, %s)',
                handler_class.__name__, bind_addr, port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit('Killed by keyboard interrupt')
    finally:
        logger.info('Shutting down')
        server.server_close()


@enforce_signature
def start_io_lang_server(handler_class: LangServer, rstream, wstream):
    logger.info('Starting %s IO language server', handler_class.__name__)
    server = handler_class(rstream, wstream)
    server.start()


def main():
    parser = ArgumentParser(description='')
    parser.add_argument('--mode', default='stdio',
                        help='communication (stdio|tcp)')
    parser.add_argument('--addr', default=2087,
                        help='server listen (tcp)', type=int)
    args = parser.parse_args()

    if args.mode == 'stdio':
        start_io_lang_server(LangServer, sys.stdin.buffer, sys.stdout.buffer)
    elif args.mode == 'tcp':
        host, addr = '0.0.0.0', args.addr
        start_tcp_lang_server(LangServer, host, addr)
