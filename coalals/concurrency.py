from concurrent.futures import ProcessPoolExecutor

from coala_utils.decorators import enforce_signature
from .utils.wrappers import func_wrapper

import logging
logger = logging.getLogger(__name__)


class JobTracker:
    """
    JobTracker helps to keep track of running jobs and
    function as an advanced counter. It is lazy and will
    only update its internal state when requested for
    information about it. JobTracker instances should always
    live on the main thread. Hence should never go out of sync.
    """

    @staticmethod
    def kill_job(job):
        # job is a Future, cancel() only requests and
        # does not currently guarantee cancellation.
        # TODO Add a reliable cancellation mechanism
        # (https://kutt.it/MyF1AZ)
        return job.cancel()

    @staticmethod
    def is_active(job):
        return not job.done()

    def __init__(self, max_jobs=1):
        if max_jobs < 1:
            raise ValueError()

        self._max_jobs = max_jobs
        # actually contains the Future
        # instances from scheduled jobs
        self._jobs = []

    def refresh_jobs(self):
        self._jobs = list(filter(
            lambda job: JobTracker.is_active(job), self._jobs))

    def __len__(self):
        """
        Return the number of active jobs after
        refreshing the job list.
        """
        self.refresh_jobs()
        return len(self._jobs)

    def has_slots(self):
        self.refresh_jobs()
        return len(self._jobs) < self._max_jobs

    def force_free_slots(self):
        if self.has_slots():
            return True

        count = 1 + len(self._jobs) - self._max_jobs
        for job in self._jobs[:count]:
            if not JobTracker.kill_job(job):
                return False

        return True

    def prepare_slot(self, force=False):
        """
        Jobtracker is not responsible to schedule,
        monitor or manage the jobs in any manner, although
        it can send a pre-empt signal to running jobs.
        It only keeps a running count and indicates if
        resources with respect to max allocation are
        available to accept incoming request. Hence the
        prepare_slot() should be called before actual
        job allocation happens to check for resources.
        """
        if not self.has_slots():
            if force is True:
                return self.force_free_slots()
            else:
                return False

        return True

    def add(self, job):
        # Evaluates lazily and does not complain about
        # the overflow. prepare_slot() should be used.

        # TODO self._jobs should be a dict and should
        # map from filename to job object. That way we
        # can prevent multiple requests fighting to run
        # on the same source file.
        # take caution before adding
        self._jobs.append(job)


class TrackedProcessPool:
    """
    Abstracts the integration of ProcessPoolExec,
    JobTracker and func_wrapper.
    """

    def __init__(self, max_jobs=1, max_workers=1):
        self._job_tracker = JobTracker(max_jobs)
        self._process_pool = ProcessPoolExecutor(max_workers=max_workers)

    @enforce_signature
    def exec_func(self,
                  func,
                  params: (list, tuple) = [],
                  kparams: dict = {},
                  force=False):
        # TODO Add a meta information carrying mechanism
        # so the callbacks can get some context.
        if not self._job_tracker.prepare_slot(force):
            return False

        future = self._process_pool.submit(
            func_wrapper, func, *params, **kparams)

        self._job_tracker.add(future)
        return future

    def shutdown(self, wait=True):
        self._process_pool.shutdown(wait)
