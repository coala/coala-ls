import pytest

from coalals.langserver import LangServer
from coalals.main import (TCPServer, start_tcp_lang_server,
                          start_io_lang_server)
from helpers.dummies import DummyTCPServer


def test_start_tcp_server(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr('coalals.main.TCPServer', DummyTCPServer)

        DummyTCPServer.panic = True
        with pytest.raises(SystemExit):
            start_tcp_lang_server(LangServer, '127.0.0.1', 4008)

        DummyTCPServer.panic = False
        DummyTCPServer.keyboard_interrupt = True
        with pytest.raises(SystemExit):
            start_tcp_lang_server(LangServer, '127.0.0.1', 4074)

        DummyTCPServer.panic = False
        DummyTCPServer.keyboard_interrupt = False
        start_tcp_lang_server(LangServer, '127.0.0.1', 4008)

        assert DummyTCPServer.served is True
        assert DummyTCPServer.closed is True


def test_start_io_server():
    del LangServer.start

    with pytest.raises(AttributeError):
        start_io_lang_server(LangServer, None, None)
