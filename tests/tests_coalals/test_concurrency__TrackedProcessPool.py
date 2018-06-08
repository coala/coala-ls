import pytest

from coalals.concurrency import JobTracker, TrackedProcessPool
from helpers.dummies import DummyFuture, DummyProcessPoolExecutor


@pytest.fixture
def trackedpool(monkeypatch):
    def _trackedpool(max_jobs=1, max_workers=1):
        with monkeypatch.context() as patch:
            patch.setattr('coalals.concurrency.ProcessPoolExecutor',
                          DummyProcessPoolExecutor)

            return TrackedProcessPool(max_jobs, max_workers)
    return _trackedpool


def test_trackedpool_init(trackedpool):
    trackedpool = trackedpool()
    assert isinstance(trackedpool._job_tracker, JobTracker)
    assert isinstance(trackedpool._process_pool, DummyProcessPoolExecutor)


def test_shutdown(trackedpool):
    trackedpool = trackedpool()
    trackedpool.shutdown()
    assert trackedpool._process_pool._closed


def test_exec_func(trackedpool):
    trackedpool = trackedpool(2)
    one, two = DummyFuture(), DummyFuture()

    def _internal_func(*args, **kargs):
        return args

    with pytest.raises(TypeError):
        trackedpool.exec_func(_internal_func, True)

    trackedpool._job_tracker._jobs = [one, two]
    assert trackedpool.exec_func(_internal_func, (True,)) is False

    one.f_cancel = False
    assert trackedpool.exec_func(_internal_func, (True,)) is False

    one.f_cancel = True
    future = trackedpool.exec_func(_internal_func, ('coala',), force=True)
    trackedpool._job_tracker.refresh_jobs()

    assert isinstance(future, DummyFuture)
    assert trackedpool._job_tracker._jobs == [two, future]
    # unpacking is done by func_wrapper
    # which is not used here, hence...
    assert future.result() == ('coala',)
