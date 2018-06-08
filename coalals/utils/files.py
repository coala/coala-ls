from pathlib import Path
from os.path import sep, isabs, dirname

import logging
logger = logging.getLogger(__name__)


class UriUtils:

    @staticmethod
    def path_from_uri(uri):
        if not uri.startswith('file://'):
            return uri

        _, path = uri.split('file://', 1)
        return path

    @classmethod
    def dir_from_uri(cls, uri):
        return dirname(cls.path_from_uri(uri))

    @staticmethod
    def file_to_uri(filename):
        return Path(filename).as_uri()


class FileProxy:
    """
    coala requires the files to be flushed to perform
    analysis on. This provides an alternative by proving
    an always updated proxy of the said file by watching
    for events from the client such as didChange.
    """

    @classmethod
    def from_name(cls, file, workspace):
        with open(file, 'r') as reader:
            return cls(file, workspace, reader.read())

    def __init__(self, filename, workspace=None, contents=''):
        logger.debug('File proxy for %s created', filename)

        # The file may not exist yet, hence there is no
        # reliable way of knowing if it is a file on the
        # disk or a directory.
        if not isabs(filename) or filename.endswith(sep):
            raise Exception('filename needs to be absolute')

        self._version = -1
        self._filename = filename
        self._contents = contents
        self._workspace = workspace
        self._changes_history = []

    def __str__(self):
        """
        Return a string representation of a file proxy
        with information about its version and filename.
        """
        return '<FileProxy {}, {}>'.format(
            self._filename, self._version)

    def update(self, diffs):
        logger.debug('Updated file proxy %s', self._filename)

        if not isinstance(diffs, list):
            diffs = [diffs]

        # TODO Handle the diff applying

        self._changes_history.extend(diffs)

    def replace(self, contents, version):
        if version > self._version:
            self._contents = contents
            self._version = version
            return True

        return False

    def contents(self):
        return self._contents

    def close(self):
        self._contents = ''

    @property
    def filename(self):
        return self._filename

    @property
    def workspace(self):
        return self._workspace

    @property
    def version(self):
        return self._version


class FileProxyMap:

    def __init__(self, file_proxies=[]):
        self._map = {proxy.filename: proxy for proxy in file_proxies}

    def add(self, proxy, replace=False):
        if not isinstance(proxy, FileProxy):
            return False

        if self._map.get(proxy.filename) is not None:
            if replace:
                self._map[proxy.filename] = proxy
                return True
            return False

        self._map[proxy.filename] = proxy
        return True

    def remove(self, filename):
        if self.get(filename):
            del self._map[filename]

    def get(self, filename):
        return self._map.get(filename)

    def resolve(self, filename, workspace=None, hard_sync=True):
        proxy = self.get(filename)
        if proxy is not None:
            return proxy

        try:
            proxy = FileProxy.from_name(filename, workspace)
        except FileNotFoundError:
            if hard_sync:
                return False

            try:
                proxy = FileProxy(filename, workspace)
            except Exception:
                return False

        self.add(proxy)
        return proxy
