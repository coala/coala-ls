import pytest
from pathlib import Path

from coalals.utils.files import UriUtils
from helpers.utils import get_random_path


@pytest.fixture
def valid_uri():
    path = get_random_path('1', True)
    return path.as_uri()


@pytest.fixture
def valid_path():
    return get_random_path('1')


@pytest.fixture
def valid_dir():
    path = get_random_path('1', True)
    return str(path.parent)


def test_path_from_uri_with_uri(valid_uri, valid_path):
    gen_path = UriUtils.path_from_uri(valid_uri)
    assert gen_path == valid_path


def test_path_from_uri_with_path(valid_path):
    gen_path = UriUtils.path_from_uri(valid_path)
    assert gen_path == valid_path


def test_dir_from_uri_with_uri(valid_uri, valid_dir):
    gen_dir = UriUtils.dir_from_uri(valid_uri)
    assert gen_dir == valid_dir


def test_dir_from_uri_with_path(valid_path, valid_dir):
    gen_dir = UriUtils.dir_from_uri(valid_path)
    assert gen_dir == valid_dir


def test_file_to_uri(valid_path, valid_uri):
    gen_uri = UriUtils.file_to_uri(valid_path)
    assert gen_uri == valid_uri
