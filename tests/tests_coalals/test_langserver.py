import pytest
from os.path import dirname
from jsonrpc.streams import JsonRpcStreamReader
from tempfile import TemporaryFile, NamedTemporaryFile

from coalals.langserver import LangServer
from coalals.utils.files import FileProxy, UriUtils
from helpers.utils import get_random_path
from helpers.resources import url, sample_code_files
from helpers.dummies import (DummyDiagnostics, DummyProcessPoolExecutor,
                             DummyAlwaysCancelledFuture,
                             DummyAlwaysExceptionFuture)


@pytest.fixture
def file_langserver(monkeypatch):
    DummyProcessPoolExecutor.on_submit = None

    with monkeypatch.context() as patch:
        patch.setattr('coalals.concurrency.ProcessPoolExecutor',
                      DummyProcessPoolExecutor)

        file = TemporaryFile()
        langserver = LangServer(file, file)

        return (file, langserver)


@pytest.fixture
def file_langserver_deep(monkeypatch):
    DummyProcessPoolExecutor.on_submit = None

    with monkeypatch.context() as patch:
        patch.setattr('coalals.concurrency.ProcessPoolExecutor',
                      DummyProcessPoolExecutor)
        # concurrent.futures maintains the same API for PoolExecutor's
        # hence, reusing DummyProcessPoolExecutor for ThreadPoolExecutor
        patch.setattr('jsonrpc.endpoint.futures.ThreadPoolExecutor',
                      DummyProcessPoolExecutor)

        file = TemporaryFile()
        langserver = LangServer(file, file)

        return (file, langserver)


@pytest.fixture
def verify_response():
    def _internal(file, langserver, consumer, **kargs):
        passed = [False]
        file.seek(0)

        def _consumer(response):
            consumer(file, response, passed, **kargs)

        reader = JsonRpcStreamReader(file)
        reader.listen(_consumer)
        reader.close()

        assert passed == [True]
    return _internal


@pytest.fixture
def verify_docsync_respone(verify_response):
    def _internal(file, langserver):
        def consumer(file, response, passed):
            assert response is not None
            capabilities = response['result']['capabilities']
            assert capabilities['textDocumentSync'] == 1
            assert capabilities['documentFormattingProvider'] == 1

            file.close()
            passed[0] = True

        verify_response(file, langserver, consumer)
    return _internal


@pytest.fixture
def verify_publish_respone(verify_response):
    def _internal(file, langserver, diag_count):
        def consumer(file, response, passed, diag_count):
            assert response is not None
            assert response['method'] == 'textDocument/publishDiagnostics'
            assert len(response['params']['diagnostics']) is diag_count

            file.close()
            passed[0] = True

        verify_response(file, langserver, consumer, diag_count=diag_count)
    return _internal


def test_server_init_with_rootPath(file_langserver, verify_docsync_respone):
    file, langserver = file_langserver
    random = get_random_path('1', True)
    uri = random.as_uri()

    request = {
        'method': 'initialize',
        'params': {
            'rootPath': UriUtils.dir_from_uri(uri),
            'capabilities': {},
        },
        'id': 1,
        'jsonrpc': '2.0',
    }

    langserver._endpoint.consume(request)
    verify_docsync_respone(file, langserver)


def test_server_init_with_rootUri(file_langserver, verify_docsync_respone):
    file, langserver = file_langserver
    random = get_random_path('1', True)
    uri = random.as_uri()

    request = {
        'method': 'initialize',
        'params': {
            'rootUri': UriUtils.dir_from_uri(uri),
            'capabilities': {},
        },
        'id': 1,
        'jsonrpc': '2.0',
    }

    langserver._endpoint.consume(request)
    verify_docsync_respone(file, langserver)


def test_send_diagnostics(file_langserver, verify_publish_respone):
    file, langserver = file_langserver
    langserver.send_diagnostics('/sample', DummyDiagnostics())
    verify_publish_respone(file, langserver, 0)


@pytest.mark.parametrize('msg_type', [1, 5])
def test_send_show_message_req(file_langserver, verify_response, msg_type):
    file, langserver = file_langserver

    future = langserver.send_show_message_req(
                msg_type,
                'This is not a message.',
                ('Okay', 'Yo!'))

    def _responder(file, request, passed, **kargs):
        msg_id = request['id']

        langserver._endpoint.consume({
            'id': msg_id,
            'result': {'title': 'Yo!', },
            'jsonrpc': '2.0',
        })

        # now wait for the future to be resolved with
        # the result of the selection
        result = future.result()

        assert result is not None
        assert result['title'] == 'Yo!'

        file.close()
        passed[0] = True

    verify_response(file, langserver, _responder)


def test_lanserver_shutdown(file_langserver):
    file, langserver = file_langserver
    langserver.m_shutdown()

    assert langserver._shutdown is True


def test_langserver_exit_no_shutdown(file_langserver):
    _, langserver = file_langserver

    with pytest.raises(SystemExit) as excp:
        langserver.m_exit()

    assert excp.value.code == 1


def test_langserver_exit_shutdown(file_langserver):
    _, langserver = file_langserver
    langserver.m_shutdown()

    with pytest.raises(SystemExit) as excp:
        langserver.m_exit()

    assert excp.value.code == 0


def assert_missing(langserver, filename):
    proxymap = langserver._proxy_map
    proxy = proxymap.get(filename)

    assert proxy is None


def assert_changed_file(langserver, filename, version, content):
    proxymap = langserver._proxy_map
    proxy = proxymap.get(filename)

    assert proxy is not None
    assert proxy.version == version
    assert proxy.contents() == content


def test_did_change_proxy_replace_new_file(file_langserver):
    file, langserver = file_langserver
    random_path = get_random_path('1', True)
    random_uri = random_path.as_uri()

    # tests the replace mode of the didChange
    request = {
        'method': 'textDocument/didChange',
        'params': {
            'textDocument': {
                'uri': random_uri,
                'version': 1,
            },
            'contentChanges': [
                {
                    'text': 'print("coala-rocks!")',
                }
            ],
        },
        'jsonrpc': '2.0',
    }

    langserver._endpoint.consume(request)
    assert_missing(langserver, str(random_path))


def test_did_change_proxy_replace_open_file(file_langserver):
    file, langserver = file_langserver

    source = NamedTemporaryFile(delete=False)
    source.write('coala'.encode('utf-8'))
    source.close()

    proxy = FileProxy(source.name)
    langserver._proxy_map.add(proxy)

    request = {
        'method': 'textDocument/didChange',
        'params': {
            'textDocument': {
                'uri': UriUtils.file_to_uri(source.name),
                'version': 2,
            },
            'contentChanges': [
                {
                    'text': 'print("coala-bears!")',
                }
            ],
        },
        'jsonrpc': '2.0',
    }

    langserver._endpoint.consume(request)
    assert_changed_file(langserver, source.name, 2, 'print("coala-bears!")')

    # not greater version
    request = {
        'method': 'textDocument/didChange',
        'params': {
            'textDocument': {
                'uri': UriUtils.file_to_uri(source.name),
                'version': 1,
            },
            'contentChanges': [
                {
                    'text': 'print("coala-bears-old!")',
                }
            ],
        },
        'jsonrpc': '2.0',
    }

    langserver._endpoint.consume(request)
    assert_changed_file(langserver, source.name, 2, 'print("coala-bears!")')


def test_did_change_proxy_replace_missing_file(file_langserver):
    file, langserver = file_langserver
    random_path = get_random_path('2', True)
    file_uri = random_path.as_uri()

    request = {
        'method': 'textDocument/didChange',
        'params': {
            'textDocument': {
                'uri': file_uri,
                'version': 2,
            },
            'contentChanges': [
                {
                    'text': 'print("coala-bears!")',
                }
            ],
        },
        'jsonrpc': '2.0',
    }

    langserver._endpoint.consume(request)
    proxymap = langserver._proxy_map
    proxy = proxymap.get(str(random_path))

    assert proxy is None


def test_did_change_proxy_update(file_langserver):
    file, langserver = file_langserver
    filename = url('failure2.py', True)

    proxy = FileProxy(str(filename))
    langserver._proxy_map.add(proxy)

    request = {
        'method': 'textDocument/didChange',
        'params': {
            'textDocument': {
                'uri': filename.as_uri(),
                'version': 2,
            },
            'contentChanges': [
                {
                    'range': {
                        'start': {
                            'line': 0,
                            'character': 0,
                        },
                        'end': {
                            'line': 0,
                            'character': 5,
                        },
                    },
                    'rangeLength': 5,
                    'text': 'print("coala-bears!")',
                }
            ],
        },
        'jsonrpc': '2.0',
    }

    langserver._endpoint.consume(request)
    # FIXME Update to test the updates


def test_langserver_did_open(file_langserver, verify_publish_respone):
    file, langserver = file_langserver
    filename = url('failure2.py')

    code = None
    with open(filename) as code_file:
        code = code_file.read()

    request = {
        'method': 'textDocument/didOpen',
        'params': {
            'textDocument': {
                'uri': UriUtils.file_to_uri(filename),
                'languageId': 'python',
                'version': 1,
                'text': code,
            },
        },
        'jsonrpc': '2.0',
    }

    code_file = sample_code_files[filename]
    exp_diag_count = code_file['diagnostics']

    langserver._endpoint.consume(request)
    verify_publish_respone(file, langserver, exp_diag_count)


def test_langserver_did_save(file_langserver, verify_publish_respone):
    file, langserver = file_langserver

    code_sample_path = url('failure.py', True)
    code_sample_name = str(code_sample_path)
    proxy = FileProxy(code_sample_name)
    langserver._proxy_map.add(proxy)

    request = {
        'method': 'textDocument/didSave',
        'params': {
            'textDocument': {
                'uri': code_sample_path.as_uri(),
            },
        },
        'jsonrpc': '2.0',
    }

    code_desc = sample_code_files[code_sample_name]
    exp_diag_count = code_desc['diagnostics']

    langserver._endpoint.consume(request)
    verify_publish_respone(file, langserver, exp_diag_count)


def assert_callback_not_called(file):
    passed = [False]
    file.seek(0)

    def _consumer(response):
        passed[0] = True

    reader = JsonRpcStreamReader(file)
    reader.listen(_consumer)
    reader.close()

    assert passed[0] is False


def test_langserver_did_save_missing_proxy(file_langserver,
                                           verify_publish_respone):
    file, langserver = file_langserver
    random_path = get_random_path('3', True)
    random_uri = random_path.as_uri()

    request = {
        'method': 'textDocument/didSave',
        'params': {
            'textDocument': {
                'uri': random_uri,
            },
        },
        'jsonrpc': '2.0',
    }

    langserver._endpoint.consume(request)
    assert_callback_not_called(file)


@pytest.mark.parametrize('future_class', [
    DummyAlwaysCancelledFuture,
    DummyAlwaysExceptionFuture])
def test_langserver_did_open_future_cancelled(future_class,
                                              monkeypatch,
                                              verify_publish_respone):
    with monkeypatch.context() as patch:
        patch.setattr('coalals.concurrency.ProcessPoolExecutor',
                      DummyProcessPoolExecutor)
        DummyProcessPoolExecutor.FutureClass = future_class

        file = TemporaryFile()
        langserver = LangServer(file, file)

        code = None
        code_path = url('failure2.py', True)
        with open(str(code_path)) as code_file:
            code = code_file.read()

        request = {
            'method': 'textDocument/didOpen',
            'params': {
                'textDocument': {
                    'uri': code_path.as_uri(),
                    'languageId': 'python',
                    'version': 1,
                    'text': code,
                },
            },
            'jsonrpc': '2.0',
        }

        langserver._endpoint.consume(request)
        assert_callback_not_called(file)


def test_langserver_did_save_failed_job(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr('coalals.concurrency.ProcessPoolExecutor',
                      DummyProcessPoolExecutor)
        DummyProcessPoolExecutor.on_submit = False

        file = TemporaryFile()
        langserver = LangServer(file, file)

        code_sample_name = url('failure.py', True)
        proxy = FileProxy(str(code_sample_name))
        langserver._proxy_map.add(proxy)

        request = {
            'method': 'textDocument/didSave',
            'params': {
                'textDocument': {
                    'uri': code_sample_name.as_uri(),
                },
            },
            'jsonrpc': '2.0',
        }

        langserver._endpoint.consume(request)
        assert_callback_not_called(file)


@pytest.mark.parametrize('will_respond', [True, False])
def test_langserver_document_formatting(will_respond,
                                        file_langserver_deep,
                                        verify_response):
    file, langserver = file_langserver_deep

    code_sample_path = url('failure3.py', True)
    code_sample_name = str(code_sample_path)
    proxy = FileProxy(code_sample_name)

    # it should fail if the file is not open
    # in the editor by extension is not in the
    # proxy map.
    if will_respond is True:
        langserver._proxy_map.add(proxy)

    request = {
        'method': 'textDocument/formatting',
        'params': {
            'textDocument': {
                'uri': code_sample_path.as_uri(),
            },

            'options': {
                'tabSize': 4,
                'insertSpaces': True,
            },
        },
        'jsonrpc': '2.0',
        'id': 1244,
    }

    langserver._endpoint.consume(request)

    def consumer(file, response, passed):
        if will_respond is False:
            passed[0] = True
            return

        elif 'id' in response:
            for text_edit in response['result']:
                assert text_edit['newText']
            passed[0] = True

    verify_response(file, langserver, consumer)


@pytest.mark.parametrize('name,add', [
    ('one', True),
    ('two', False)])
def test_langserver_did_close(file_langserver, name, add):
    _, langserver = file_langserver
    random_path = get_random_path(name, True)
    random_uri = random_path.as_uri()
    random_name = str(random_path)

    if add:
        proxy = FileProxy(random_name)
        langserver._proxy_map.add(proxy)

    request = {
        'method': 'textDocument/didClose',
        'params': {
            'textDocument': {
                'uri': random_uri,
            },
        },
        'jsonrpc': '2.0',
    }

    langserver._endpoint.consume(request)
    assert langserver._proxy_map.get(random_name) is None


def test_langserver_set_concurrency_params(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr('coalals.concurrency.ProcessPoolExecutor',
                      DummyProcessPoolExecutor)

        file = TemporaryFile()

        assert LangServer.set_concurrency_params(3, 4)
        langserver = LangServer(file, file)

        pool = langserver._coala._tracked_pool
        assert pool._job_tracker._max_jobs == 3
        assert pool._process_pool._max_workers == 4

        # Sticky concurrency configuration
        langserver = LangServer(file, file)

        pool = langserver._coala._tracked_pool
        assert pool._job_tracker._max_jobs == 3
        assert pool._process_pool._max_workers == 4

        assert not LangServer.set_concurrency_params(0, 2)
        assert not LangServer.set_concurrency_params(2, 0)
