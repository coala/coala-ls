from pathlib import Path
from os.path import sep, isabs, dirname

import logging
logger = logging.getLogger(__name__)


class UriUtils:
    """
    UriUtils helps in performing various transformations
    to file paths and URIs. It works independently from
    the operating system.
    """

    @staticmethod
    def path_from_uri(uri):
        """
        :param uri:
            The URI to decode path from. This method
            fallsback and considers a invalid URI as
            a valid path in itself.
        :return:
            Returns a string path encoded in the URI.
        """
        if not uri.startswith('file://'):
            return uri

        _, path = uri.split('file://', 1)
        return path

    @classmethod
    def dir_from_uri(cls, uri):
        """
        Find and returns the parent directory of the
        path encoded in the URI.

        :param uri:
            The subject URI string containing the path
            to find the parent of.
        :return:
            A string path to the parent directory.
        """
        return dirname(cls.path_from_uri(uri))

    @staticmethod
    def file_to_uri(filename):
        """
        Transform a given file name into a URI. It
        works independent of the file name format.

        :param filename:
            The path of the file to transform into URI.
        :return:
            Returns transformed URI as a string.
        """
        return Path(filename).as_uri()


class FileProxy:
    """
    coala requires the files to be flushed to perform
    analysis on. This provides an alternative by providing
    an always updated proxy of the said file by watching
    for events from the client such as didChange.
    """

    @classmethod
    def from_name(cls, file, workspace):
        """
        Construct a FileProxy instance from an existing
        file on the drive.

        :param file:
            The name of the file to be represented by
            the proxy instance.
        :param workspace:
            The workspace the file belongs to. This can
            be none representing that the the directory
            server is currently serving from is the workspace.
        :return:
            Returns a FileProxy instance of the file with
            the content synced from a disk copy.
        """
        with open(file, 'r') as reader:
            return cls(file, workspace, reader.read())

    def __init__(self, filename, workspace=None, contents=''):
        """
        Initialize the FileProxy instance with the passed
        parameters. A FileProxy instance always starts at
        a fresh state with a negative version indicating
        that no updating operation has been performed on it.

        :param filename:
            The name of the file to create a FileProxy of.
        :param workspace:
            The workspace this file belongs to. Can be None.
        :param contents:
            The contents of the file to initialize the
            instance with. Integrity of the content or the
            sync state is never checked during initialization.
        """
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
        :return:
            Return a string representation of a file proxy
            with information about its version and filename.
        """
        return '<FileProxy {}, {}>'.format(
            self._filename, self._version)

    def update(self, diffs):
        """
        The method updates the contents of the file proxy
        instance by applying patches to the content and
        changing the version number along. It also maintains
        the update history of the proxy.

        :param diffs:
            The list of patches in exact order to be applied
            to the content.
        """
        logger.debug('Updated file proxy %s', self._filename)

        if not isinstance(diffs, list):
            diffs = [diffs]

        # TODO Handle the diff applying

        self._changes_history.extend(diffs)

    def replace(self, contents, version):
        """
        The method replaces the content of the proxy
        entirely and does not push the change to the
        history. It is similar to updating the proxy
        with the range spanning to the entire content.

        :param contents:
            The new contents of the proxy.
        :param version:
            The version number proxy upgrades to after
            the update. This needs to be greater than
            the current version number.
        :return:
            Returns a boolean indicating the status of
            the update.
        """
        if version > self._version:
            self._contents = contents
            self._version = version
            return True

        return False

    def get_disk_contents(self):
        """
        :return:
            Returns the contents of a copy of the file
            on the disk. It might not be in sync with
            the editor version of the file.
        """
        with open(self.filename) as disk:
            return disk.read()

    def contents(self):
        """
        :return:
            Returns the current contents of the proxy.
        """
        return self._contents

    def close(self):
        """
        Closing a proxy essentially means emptying the contents
        of the proxy instance.
        """
        self._contents = ''

    @property
    def filename(self):
        """
        :return:
            Returns the complete file name.
        """
        return self._filename

    @property
    def workspace(self):
        """
        :return:
            Returns the workspace of the file.
        """
        return self._workspace

    @property
    def version(self):
        """
        :return:
            Returns the current edit version of the file.
        """
        return self._version


class FileProxyMap:
    """
    Proxy map handles a collection of proxies
    and provides a mechanism to handles duplicate
    proxies and resolving them.
    """

    def __init__(self, file_proxies=[]):
        """
        :param file_proxies:
            A list of FileProxy instances to initialize
            the ProxyMap with.
        """
        self._map = {proxy.filename: proxy for proxy in file_proxies}

    def add(self, proxy, replace=False):
        """
        Add a proxy instance to the proxy map.

        :param proxy:
            The proxy instance to register in the map.
        :param replace:
            A boolean flag indicating if the proxy should
            replace an existing proxy of the same file.
        :return:
            Boolean true if registering of the proxy was
            successful else false.
        """
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
        """
        Remove the proxy associated with a file from the
        proxy map.

        :param filename:
            The name of the file to remove the proxy
            associated with.
        """
        if self.get(filename):
            del self._map[filename]

    def get(self, filename):
        """
        :param filename:
            The name of the file to get the associated proxy of.
        :return:
            A file proxy instance or None if not available.
        """
        return self._map.get(filename)

    def resolve(self, filename, workspace=None, hard_sync=True):
        """
        Resolve tries to find an available proxy or creates one
        if there is no available proxy for the said file.

        :param filename:
            The filename to search for in the map or to create
            a proxy instance using.
        :param workspace:
            Used in case the lookup fails and a new instance is
            being initialized.
        :hard_sync:
            Boolean flag indicating if the file should be initialized
            from the file on disk or fail otherwise.
        :return:
            Returns a proxy instance or a boolean indicating the
            failure of the resolution.
        """
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
