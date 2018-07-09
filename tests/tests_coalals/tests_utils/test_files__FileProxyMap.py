import pytest
from pathlib import Path
from random import randint
from tempfile import NamedTemporaryFile

from coalals.utils.files import FileProxy, FileProxyMap
from helpers.utils import get_random_path


@pytest.fixture
def random_filename():
    def _internal():
        rand_no = randint(1, 9999)
        return get_random_path(rand_no)
    return _internal


@pytest.fixture
def random_fileproxy(random_filename):
    def _internal():
        random = random_filename()
        return FileProxy(random)
    return _internal


@pytest.fixture
def empty_proxymap(random_filename):
    return FileProxyMap()


def test_proxymap_empty(empty_proxymap):
    assert empty_proxymap._map == {}


def test_proxymap_add(empty_proxymap, random_fileproxy):
    assert empty_proxymap.add(123) is False
    assert empty_proxymap.add('coala') is False

    proxy_one = random_fileproxy()
    assert empty_proxymap.add(proxy_one) is True
    assert empty_proxymap._map == {proxy_one.filename: proxy_one}

    proxy_two = FileProxy(proxy_one.filename, '.', 'coala-rocks')
    assert empty_proxymap.add(proxy_two, replace=False) is False
    assert empty_proxymap.add(proxy_two, replace=True) is True

    added_proxy = empty_proxymap._map[proxy_two.filename]
    assert added_proxy.contents() == 'coala-rocks'


def test_proxymap_remove(empty_proxymap, random_fileproxy, random_filename):
    random = random_fileproxy()
    empty_proxymap.add(random)

    assert len(empty_proxymap._map) == 1
    empty_proxymap.remove(random.filename)
    assert len(empty_proxymap._map) == 0

    search_for = random_filename()
    assert empty_proxymap.remove(search_for) is None


def test_proxymap_get(empty_proxymap, random_fileproxy, random_filename):
    search_for = random_filename()
    assert empty_proxymap.get(search_for) is None

    random = random_fileproxy()
    empty_proxymap.add(random)
    assert empty_proxymap.get(random.filename) == random


def test_proxymap_resolve_finds(empty_proxymap, random_fileproxy):
    random = random_fileproxy()

    empty_proxymap.add(random)
    assert empty_proxymap.resolve(random.filename) == random


def test_proxymap_resolve_creates(empty_proxymap):
    file = NamedTemporaryFile(delete=False)
    file.write('coala-rocks'.encode('utf-8'))
    file.close()

    proxy = empty_proxymap.resolve(file.name)
    assert proxy.contents() == 'coala-rocks'


def test_proxymap_resolve_not_finds_hard(empty_proxymap, random_filename):
    filename = random_filename()
    assert empty_proxymap.resolve(filename, hard_sync=True) is False


def test_proxymap_resolve_create_soft_err(empty_proxymap):
    random_path = get_random_path('1', True)
    relative = random_path.relative_to(Path.cwd())

    assert empty_proxymap.resolve(str(relative), hard_sync=False) is False


def test_proxymap_resolve_not_finds_soft(empty_proxymap, random_fileproxy):
    random = random_fileproxy()

    proxy = empty_proxymap.resolve(random.filename, random.workspace,
                                   hard_sync=False)

    assert proxy.filename == random.filename
    assert proxy.workspace == random.workspace
    assert proxy.contents() == ''
    assert proxy.version == -1
