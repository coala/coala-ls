from jsonrpc.endpoint import Endpoint
from jsonrpc.dispatchers import MethodDispatcher
from jsonrpc.streams import JsonRpcStreamWriter, JsonRpcStreamReader

from .results import Diagnostics
from .interface import coalaWrapper
from .utils.files import UriUtils, FileProxy, FileProxyMap

import logging
logger = logging.getLogger(__name__)


class LangServer(MethodDispatcher):

    def __init__(self, rx, tx):
        self.root_path = None
        self._dispatchers = []
        self._shutdown = False

        self._jsonrpc_stream_reader = JsonRpcStreamReader(rx)
        self._jsonrpc_stream_writer = JsonRpcStreamWriter(tx)
        self._endpoint = Endpoint(self, self._jsonrpc_stream_writer.write)
        self._proxy_map = FileProxyMap()

        # max_jobs is strict and a new job can only be submitted by pre-empting
        # an older job or submitting later. No queuing is supported.
        self._coala = coalaWrapper(max_jobs=2, max_workers=2)

        self._capabilities = {
            'capabilities': {
                'textDocumentSync': 1,
            }
        }

    def start(self):  # pragma: no cover
        self._jsonrpc_stream_reader.listen(self._endpoint.consume)

    def m_initialize(self, **params):
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
        """
        filename = fileproxy.filename

        result = self._coala.p_analyse_file(fileproxy, force=force)
        if result is False:
            logging.debug('Failed analysis on %s', fileproxy)
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
        Handle the file updates and syncs the file proxy
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
        logger.info('Reacting to didClose notification')

        text_document = params['textDocument']
        filename = self._text_document_to_name(text_document)

        # just remove the proxy object
        self._proxy_map.remove(filename)

        # TODO Add a mechanism to send a pre-empt signal to running
        # analysis cycles on the file being closed.

    def m_shutdown(self, **_kwargs):
        self._shutdown = True

    def send_diagnostics(self, path, diagnostics):
        warnings = diagnostics.warnings()
        logger.info('Publishing %s diagnostic messages', len(warnings))

        params = {
            'uri': UriUtils.file_to_uri(path),
            'diagnostics': warnings,
        }

        self._endpoint.notify(
            'textDocument/publishDiagnostics',
            params=params)
