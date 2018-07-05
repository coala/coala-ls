import pytest

from helpers.dummies import DummyFuture
from coalals.concurrency import JobTracker


@pytest.fixture
def completed_future():
    return DummyFuture(False, True)


@pytest.fixture
def running_future():
    return DummyFuture(True, True)


@pytest.fixture
def jobtracker():
    return JobTracker()


def test_jobtracker_init():
    # Mostly to ensure that the internal API
    # is consistent for following tests.
    tracker = JobTracker()
    assert tracker._jobs == []
    assert tracker._max_jobs == 1

    tracker = JobTracker(max_jobs=3)
    assert tracker._jobs == []
    assert tracker._max_jobs == 3

    with pytest.raises(ValueError):
        tracker = JobTracker(max_jobs=0)


def test_jobtracker_kill():
    dummy = DummyFuture(False, True)
    assert JobTracker.kill_job(dummy) is True

    dummy.f_cancel = False
    assert JobTracker.kill_job(dummy) is False


def test_jobtracker_is_active():
    dummy = DummyFuture(True, True)
    assert JobTracker.is_active(dummy) is True

    dummy.f_active = False
    assert JobTracker.is_active(dummy) is False


def test_jobtracker_refresh(jobtracker, completed_future, running_future):
    jobtracker._jobs = [completed_future, running_future]
    assert len(jobtracker._jobs) == 2

    jobtracker.refresh_jobs()
    assert len(jobtracker._jobs) == 1
    assert completed_future not in jobtracker._jobs

    jobtracker._jobs[0].f_active = False
    jobtracker.refresh_jobs()
    assert len(jobtracker._jobs) == 0
    assert running_future not in jobtracker._jobs


def test_jobtracker_has_slots(completed_future, running_future):
    jobtracker = JobTracker(max_jobs=2)
    assert jobtracker.has_slots() is True

    jobtracker._jobs = [running_future]
    assert jobtracker.has_slots() is True

    jobtracker._jobs = [running_future, running_future]
    assert jobtracker.has_slots() is False

    jobtracker._jobs = [completed_future, running_future]
    assert jobtracker.has_slots() is True


def test_force_free_slots():
    jobtracker = JobTracker(max_jobs=2)
    one, two = DummyFuture(), DummyFuture()

    jobtracker._jobs = [one]
    assert jobtracker.force_free_slots() is True

    one.f_cancel = False
    jobtracker._jobs = [one, two]
    assert jobtracker.force_free_slots() is False

    one.f_cancel = True
    assert jobtracker.force_free_slots() is True
    assert len(jobtracker) == 1
    assert one not in jobtracker._jobs

    three = DummyFuture()
    two.f_cancel = False
    jobtracker._jobs = [one, two, three]
    assert jobtracker.force_free_slots() is False

    two.f_cancel = True
    assert jobtracker.force_free_slots() is True
    assert len(jobtracker) == 1
    assert one not in jobtracker._jobs
    assert two not in jobtracker._jobs


def test_jobtracker_prepare_slot():
    jobtracker = JobTracker(max_jobs=2)
    one, two = DummyFuture(), DummyFuture()

    jobtracker._jobs = [one]
    assert jobtracker.prepare_slot(force=False) is True

    jobtracker._jobs = [one, two]
    assert jobtracker.prepare_slot(force=False) is False

    one.f_cancel = False
    assert jobtracker.prepare_slot(force=True) is False

    one.f_cancel = True
    assert jobtracker.prepare_slot(force=True) is True
    jobtracker.refresh_jobs()
    assert one not in jobtracker._jobs


def test_jobtracker_add(jobtracker, running_future):
    jobtracker.add(running_future)
    assert jobtracker._jobs == [running_future]

    jobtracker.add(running_future)
    assert jobtracker._jobs == [running_future, running_future]


def test_jobtracker_len(jobtracker, running_future, completed_future):
    jobtracker.add(running_future)
    assert len(jobtracker) == 1

    jobtracker.add(completed_future)
    assert len(jobtracker) == 1
    assert completed_future not in jobtracker._jobs
