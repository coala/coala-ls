import pytest
from tempfile import TemporaryFile

from helpers.dummies import DummyLangServer
from coalals.utils.wrappers import func_wrapper, StreamHandlerWrapper


class DummyStreamRequestHandler:

    rfile = None
    wfile = None

    def __init__(self, *args, **kargs):
        pass

    def setup(self):
        pass


def test_func_wrapper():
    def _sum(*args):
        return sum(args)

    def _act(*args, _max=True):
        if _max:
            return max(args)
        return min(args)

    assert func_wrapper(_sum, 1, 2) == 3
    assert func_wrapper(_act, 5, 6, 8, _max=True) == 8


def test_streamhandler():
    bases = StreamHandlerWrapper.__bases__
    StreamHandlerWrapper.__bases__ = (DummyStreamRequestHandler,)

    wrapped_type = type(
        'DummyWrapped',
        (StreamHandlerWrapper,),
        {'DELEGATE_CLASS': DummyLangServer, })

    instance = wrapped_type()

    rtemp, wtemp = TemporaryFile(), TemporaryFile()
    DummyStreamRequestHandler.rfile = rtemp
    DummyStreamRequestHandler.wfile = wtemp

    instance.setup()
    assert instance.delegate.f_rfile == rtemp
    assert instance.delegate.f_wfile == wtemp

    instance.handle()
    assert instance.delegate.started is True

    StreamHandlerWrapper.__bases__ = bases
