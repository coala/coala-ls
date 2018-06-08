import pytest
from io import StringIO
from json import loads, dumps

from coalals.interface import coalaWrapper
from helpers.utils import get_random_path
from helpers.resources import url, sample_code_files, count_diagnostics
from helpers.dummies import (DummyFuture, DummyFileProxy, DummyFileProxyMap,
                             DummyProcessPoolExecutor)


@pytest.fixture
def sample_proxymap():
    file_map = {}

    for filename in sample_code_files.keys():
        file_map[filename] = DummyFileProxy(filename)

    return DummyFileProxyMap(file_map)


@pytest.fixture
def coala(monkeypatch):
    def _internal(patch_run_coala=False, patched_ret_val=1):
        with monkeypatch.context() as patch:
            if patch_run_coala:
                def _patch(*args):
                    return (StringIO(), patched_ret_val)

                monkeypatch.setattr('test_interface.coalaWrapper._run_coala',
                                    _patch)

            patch.setattr('coalals.concurrency.ProcessPoolExecutor',
                          DummyProcessPoolExecutor)

            return coalaWrapper()
    return _internal


def get_gen_diag_count(result):
    if hasattr(result, 'result'):
        result = result.result()

    gen_diagnostics = loads(result)['results']
    return count_diagnostics(gen_diagnostics)


def test_coalawrapper_analyse_file(coala, sample_proxymap):
    coala = coala()

    filename = url('failure.py')
    proxy = sample_proxymap.resolve(filename)
    proxy.workspace = None

    gen_diagnostics = coala.analyse_file(proxy)
    gen_diag_count = get_gen_diag_count(gen_diagnostics)

    sample_code = sample_code_files[filename]
    exp_diag_count = sample_code['diagnostics']

    assert gen_diag_count == exp_diag_count


def test_coalawrapper_analyse_missing_file(coala):
    coala = coala()

    random_path = get_random_path('1')
    proxy = DummyFileProxy(random_path)

    gen_diagnostics = coala.analyse_file(proxy)
    gen_diag_count = get_gen_diag_count(gen_diagnostics)

    assert gen_diag_count == 0


def test_coalawrapper_p_analyse_file(coala, sample_proxymap):
    coala = coala()

    filename = url('failure2.py')
    proxy = sample_proxymap.resolve(filename)

    result = coala.p_analyse_file(proxy)
    assert isinstance(result, DummyFuture)
    gen_diag_count = get_gen_diag_count(result)

    sample_code = sample_code_files[filename]
    exp_diag_count = sample_code['diagnostics']

    assert gen_diag_count == exp_diag_count


def test_coalawrapper_p_analyse_missing_file(coala):
    coala = coala()

    random_path = get_random_path('2')
    proxy = DummyFileProxy(random_path)

    result = coala.p_analyse_file(proxy)
    assert isinstance(result, DummyFuture)
    gen_diag_count = get_gen_diag_count(result)

    assert gen_diag_count == 0


def test_coalawrapper_p_analyse_file_fail_job(coala):
    coala = coala()
    one, two = DummyFuture(), DummyFuture()

    random_path = get_random_path('3')
    proxy = DummyFileProxy(random_path)

    one.f_cancel = False
    two.f_cancel = False
    coala._tracked_pool._job_tracker._jobs = [one, two]

    result = coala.p_analyse_file(proxy)
    assert result is False


@pytest.mark.parametrize('retval', (1, -1))
def test_coalawrapper_run_coala_patched_op(coala, retval):
    coala = coala(True, retval)

    random_path = get_random_path('4')
    proxy = DummyFileProxy(random_path)

    result = coala.p_analyse_file(proxy)
    assert isinstance(result, DummyFuture)
    gen_diag_count = get_gen_diag_count(result)

    assert gen_diag_count == 0


def test_coalawrapper_close(coala):
    coala = coala()
    coala.close()

    # mocked shutdown property
    assert coala._tracked_pool._process_pool._closed
