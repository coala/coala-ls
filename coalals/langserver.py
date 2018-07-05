import sys

from jsonrpc.endpoint import Endpoint
from jsonrpc.dispatchers import MethodDispatcher
from jsonrpc.streams import JsonRpcStreamWriter, JsonRpcStreamReader
from .results.diagnostics import Diagnostics
from .interface import coalaWrapper
from .utils.files import UriUtils, FileProxy, FileProxyMap

import logging
logger = logging.getLogger(__name__)


class LangServer(MethodDispatcher):
    """
    LangServer class handles various kinds of
    notifications and requests.
    """

    _config_max_jobs = 2
    _config_max_workers = 2

    @classmethod
    def set_concurrency_params(cls, max_jobs=2, max_workers=2):
        """
        Allow for setting concurrency parameters to be used with
        tracker and process pool. The settings are sticky and will
        also be used with later instances of language server unless
        explicitly reset.

        :param max_jobs:
            The max_jobs parameter to be used with coalaWrapper.
            Indicates the maximum number of concurrent jobs to permit.
        :param max_workers:
            The max_workers parameter to be used with coalaWrapper.
            This indicates the maximum number of processes to maintain
            in the pool. max_workers >= max_jobs.
        :return:
            True if parameters were set successfully else False.
        """
        if max_jobs < 1 or max_workers < max_jobs:
            return False

        cls._config_max_jobs = max_jobs
        cls._config_max_workers = max_workers

        return True

    def __init__(self, rx, tx):
        """
        :param rx:
            An input stream.
        :param tx:
            An output stream.
        """
        self.root_path = None
        self._dispatchers = []
        self._shutdown = False

        self._jsonrpc_stream_reader = JsonRpcStreamReader(rx)
        self._jsonrpc_stream_writer = JsonRpcStreamWriter(tx)
        self._endpoint = Endpoint(self, self._jsonrpc_stream_writer.write)
        self._proxy_map = FileProxyMap()

        # max_jobs is strict and a new job can only be submitted by pre-empting
        # an older job or submitting later. No queuing is supported.
        self._coala = coalaWrapper(max_jobs=self._config_max_jobs,
                                   max_workers=self._config_max_workers)

        self._capabilities = {
            'capabilities': {
                'textDocumentSync': 1,
            }
        }

    def start(self):  # pragma: no cover
        """
        Start listening on the stream and dispatches events to
        callbacks.
        """
        self._jsonrpc_stream_reader.listen(self._endpoint.consume)

    def m_initialize(self, **params):
        """
        initialize request is sent from a client to server and it
        expects the list of capabilities as a response.

        :param params:
            Parameters passed to the callback method from a dispatcher,
            follows InitializeParams structure according to LSP.
        """
        logger.info('Serving initialize request')

        # Notice that the root_path could be None.
        if 'rootUri' in params:
            self.root_path = UriUtils.path_from_uri(params['rootUri'])
        elif 'rootPath' in params:  # pragma: no cover
            self.root_path = UriUtils.path_from_uri(params['rootPath'])

        return self._capabilities

    def local_p_analyse_file(self, fileproxy, force=False):
        """
        Schedule concurrent analysis cycle and handles
        the resolved future. The diagnostics are published
        from the callback.

        :param fileproxy:
            The proxy of the file to perform coala analysis on.
        :param force:
            The force flag to use when perparing a slot.
        """
        filename = fileproxy.filename
        logger.info('Running analysis on %s', filename)

        result = self._coala.p_analyse_file(fileproxy, force=force)
        if result is False:
            logging.info('Failed analysis on %s', fileproxy.filename)
            return

        # Always called on this thread
        def _handle_diagnostics(future):
            # TODO Find a better method to deal with
            # failure cases.
            if future.cancelled():
                logger.debug('Cancelled diagnostics on %s', filename)
                return

            if future.exception():
                logger.debug('Exception during analysis: %s',
                             future.exception())
                return

            coala_json = future.result()
            diagnostics = Diagnostics.from_coala_json(coala_json)

            self.send_diagnostics(filename, diagnostics)

        result.add_done_callback(_handle_diagnostics)

    def _text_document_to_name(self, text_document):
        uri = text_document['uri']
        return UriUtils.path_from_uri(uri)

    def m_text_document__did_open(self, **params):
        """
        textDocument/didOpen request is dispatched by the client
        to the server whenever a new file is opened in the editor.
        LangServer here builds a new FileProxy object and replaces
        or adds it to the map. It also has access to file content
        via the params. It also performs initial coala analysis on
        the file and published the diagnostics.

        :param params:
            The params passed by the client. The structure remains
            consistent with the LSP protocol definition.
        """
        logger.info('Reacting to didOpen notification')

        text_document = params['textDocument']
        filename = self._text_document_to_name(text_document)

        # didOpen can create the file proxy from
        # the params passed to it
        contents = text_document['text']
        version = text_document['version']

        proxy = FileProxy(filename, workspace=self.root_path)
        proxy.replace(contents, version)
        self._proxy_map.add(proxy, replace=True)

        self.local_p_analyse_file(proxy, True)

    def m_text_document__did_save(self, **params):
        """
        textDocument/didSave is dispatched by the client to the
        server on saving a file. LangServer performs a coala
        analysis of the file if it already exists in its file
        map.

        :param params:
            The parameters passed during the notification.
        """
        logger.info('Reacting to didSave notification')

        text_document = params['textDocument']
        filename = self._text_document_to_name(text_document)

        # If the file does not exist in the proxy map
        # discard the request, it should didOpen first
        proxy = self._proxy_map.get(filename)
        if proxy is None:
            return

        text_document = params['textDocument']
        self.local_p_analyse_file(proxy, True)

    def m_text_document__did_change(self, **params):
        """
        textDocument/didChange is a notification from client to
        server when the text document is changed by adding or
        removing content. This callback current updates the
        associated proxy's content.

        :param params:
            The parameters passed during the notification.
        """
        logger.info('Reacting to didChange notification')
        text_document = params['textDocument']
        content_changes = params['contentChanges']

        filename = self._text_document_to_name(text_document)
        proxy = self._proxy_map.get(filename)

        # Send a didOpen first
        if proxy is None:
            return

        # update if range and rangeLength are present
        # in the contentChanges dict else replace
        if ('range' not in content_changes[0] and
                'rangeLength' not in content_changes[0]):

            version = text_document['version']
            content = content_changes[0]['text']

            if proxy.replace(content, version):
                logger.info(
                    'Replaced proxy content to version %s', version)

        # FIXME Add a way to handle the range updates mechanism
        # i.e resolve diffs and construct the text, the diff
        # handling mechanism should be handled in FileProxy's
        # update method

    def m_text_document__did_close(self, **params):
        """
        textDocument/didClose is dispatched by the client to the
        server when a file is closed in the text editor. This
        callback updates the state of the proxy map.

        :param params:
            The parameters passed during the notification.
        """
        logger.info('Reacting to didClose notification')

        text_document = params['textDocument']
        filename = self._text_document_to_name(text_document)

        # just remove the proxy object
        self._proxy_map.remove(filename)

        # TODO Add a mechanism to send a pre-empt signal to running
        # analysis cycles on the file being closed.

    def m_shutdown(self, **params):
        """
        shutdown request is sent from client to the server.
        """
        self._shutdown = True

    def m_exit(self, **params):
        """
        exit notification expects that server will close while
        freeing all its resources.
        """
        logger.info('Reacting to exit notification')

        self._coala.close()
        sys.exit(not self._shutdown)

    def send_diagnostics(self, path, diagnostics):
        """
        Dispatche diagnostic messages to the editor.

        :param path:
            The path of the file corresponding to the diagnostic
            messages as a string.
        :param diagnostics:
            An instance of Diagnostics class with holding the
            associated diagnostic messages.
        """
        warnings = diagnostics.warnings()
        logger.info('Publishing %s diagnostic messages', len(warnings))

        params = {
            'uri': UriUtils.file_to_uri(path),
            'diagnostics': warnings,
        }

        self._endpoint.notify(
            'textDocument/publishDiagnostics',
            params=params)
