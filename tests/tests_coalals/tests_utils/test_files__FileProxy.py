import pytest
from os.path import relpath
from tempfile import NamedTemporaryFile

from coalals.utils.files import FileProxy
from helpers.resources import url
from helpers.utils import get_random_path


@pytest.fixture
def temporary_file():
    temp = NamedTemporaryFile(delete=False)
    temp.write('coala'.encode('utf8'))
    temp.close()

    return temp.name


@pytest.fixture
def empty_fileproxy():
    random_path = get_random_path('1')
    return FileProxy(random_path)


def test_fileproxy_relative_name():
    failure_path = url('failure.py')
    rel = relpath(failure_path, __file__)
    # FIXME __file__ is unreliable here

    with pytest.raises(Exception):
        FileProxy(rel)


def test_fileproxy_init(empty_fileproxy):
    assert empty_fileproxy.version == -1
    assert empty_fileproxy.contents() == ''
    assert empty_fileproxy.workspace is None


def test_fileproxy_str(empty_fileproxy):
    gen_str = '<FileProxy {}, {}>'.format(
        empty_fileproxy.filename, empty_fileproxy.version)
    assert gen_str == str(empty_fileproxy)


def test_fileproxy_from_name(temporary_file):
    fileproxy = FileProxy.from_name(temporary_file, '.')

    assert fileproxy.version == -1
    assert fileproxy.workspace == '.'
    assert fileproxy.contents() == 'coala'
    assert fileproxy.filename == temporary_file


def test_file_from_name_missing_file():
    random_path = get_random_path('5', py=False)

    with pytest.raises(FileNotFoundError):
        FileProxy.from_name(random_path, '.')


def test_fileproxy_close(empty_fileproxy):
    empty_fileproxy.close()
    assert empty_fileproxy.contents() == ''


def test_fileproxy_replace(temporary_file):
    fileproxy = FileProxy.from_name(temporary_file, '.')

    assert fileproxy.version == -1
    assert fileproxy.contents() == 'coala'

    assert fileproxy.replace('coala-rocks', 1)
    assert fileproxy.contents() == 'coala-rocks'

    assert not fileproxy.replace('coala-mountains', 1)
    assert fileproxy.contents() == 'coala-rocks'

    assert not fileproxy.replace('coala-mountains', 0)
    assert fileproxy.contents() == 'coala-rocks'


def test_fileproxy_update(temporary_file):
    class Diff:
        pass

    fileproxy = FileProxy.from_name(temporary_file, '.')
    one, two, three = Diff(), Diff(), Diff()
    assert fileproxy._changes_history == []

    fileproxy.update(one)
    assert fileproxy._changes_history == [one]

    fileproxy.update([two, three])
    assert fileproxy._changes_history == [one, two, three]
