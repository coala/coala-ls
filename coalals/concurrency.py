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
        """
        Abstract method that should kill a job instance. This
        makes JobTracker independent of the job type and its
        state tracking mechanism.

        :param job:
            Job to be killed.
        :return:
            A boolean value representing the result of a killing.
            True if preemption was successful or false.
        """
        # job is a Future, cancel() only requests and
        # does not currently guarantee cancellation.
        # TODO Add a reliable cancellation mechanism
        # (https://kutt.it/MyF1AZ)
        return job.cancel()

    @staticmethod
    def is_active(job):
        """
        Abstract method to find the running state of a given job.

        :param job:
            The job to find the running state of.
        :return:
            The running state of a job.
        """
        # A typical job can be any convenient object
        # by default it is considered as a future.
        return not job.done()

    def __init__(self, max_jobs=1):
        """
        :param max_jobs:
            The maximum number of concurrent jobs to permit.
        """
        if max_jobs < 1:
            raise ValueError()

        self._max_jobs = max_jobs
        # actually contains the Future
        # instances from scheduled jobs
        self._jobs = []

    def refresh_jobs(self):
        """
        Refresh the internal state of the tracker.
        """
        self._jobs = list(filter(
            lambda job: JobTracker.is_active(job), self._jobs))

    def __len__(self):
        """
        :return:
            Returns the number of active jobs after
            refreshing the job list.
        """
        self.refresh_jobs()
        return len(self._jobs)

    def has_slots(self):
        """
        :return:
            Returns a boolean value representing if there
            are free slots available to add more jobs.
        """
        self.refresh_jobs()
        return len(self._jobs) < self._max_jobs

    def force_free_slots(self):
        """
        Attempt to empty job slots by trying to kill
        older processes. All the excessive jobs
        that are above limit are also killed off.
        force_free_slots only attempts to make slots,
        it does not assure the availability of a slot.

        :return:
            A boolean value indicating if a slot was
            freed for use.
        """
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

        :param force:
            Boolean value indicating if force freeing of
            slots should be used if no slots are empty.
        :return:
            Returns a boolean value indicating if a job
            should be scheduled and added.
        """
        if not self.has_slots():
            if force is True:
                return self.force_free_slots()
            else:
                return False

        return True

    def add(self, job):
        """
        Add a job to the list of jobs but does not
        check for slots or the active status as It is
        assumed that proper checks have been done
        before scheduling. Hence before calling this
        use prepare_slot().

        :param job:
            The job instance.
        """
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
        """
        :param max_jobs:
            The maximum number of jobs to allow concurrently,
            the parameter is passed to JobTracker as is.
        :param max_workers:
            The number of processes to use with the pool.
        """
        self._job_tracker = JobTracker(max_jobs)
        self._process_pool = ProcessPoolExecutor(max_workers=max_workers)

    @enforce_signature
    def exec_func(self,
                  func,
                  params: (list, tuple) = [],
                  kparams: dict = {},
                  force=False):
        """
        Handle preparing slot on the tracker, scheduling the
        job on the pool and adding the job to the tracker.

        :param func:
            The callable that should be invoked on a new process.
        :param params:
            A list of non-keyword arguments to be passed to the
            callable for execution.
        :param kparams:
            A dict of keyword arguments to be passed to the callable
            for execution.
        :param force:
            The force flag to use while preparing a slot.
        :return:
            Returns a job added to the tracker or a False.
        """
        # TODO Add a meta information carrying mechanism
        # so the callbacks can get some context.
        if not self._job_tracker.prepare_slot(force):
            return False

        future = self._process_pool.submit(
            func_wrapper, func, *params, **kparams)

        self._job_tracker.add(future)
        return future

    def shutdown(self, wait=True):
        """
        Shutdown the process pool and all associated resources.

        :param wait:
            Boolean indicating if the pool should wait until all
            the processes close.
        """
        self._process_pool.shutdown(wait)
