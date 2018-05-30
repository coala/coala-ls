import sys
from os import chdir
from json import dumps
from io import StringIO
from contextlib import redirect_stdout

from coalib import coala
from .concurrency import TrackedProcessPool
from .utils.log import configure_logger, reset_logger

import logging
logger = logging.getLogger(__name__)


class coalaWrapper:
    """
    Provides an abstract interaction layer to coala
    to perform the actual analysis.
    """

    def __init__(self, max_jobs=1, max_workers=1):
        self._tracked_pool = TrackedProcessPool(
            max_jobs=max_jobs, max_workers=max_workers)

    @staticmethod
    def _run_coala():
        stream = StringIO()
        with redirect_stdout(stream):
            return (stream, coala.main())

    @staticmethod
    def _get_op_from_coala(stream, retval):
        output = None
        if retval == 1:
            output = stream.getvalue()
            if output:
                logger.debug('Output: %s', output)
            else:
                logger.debug('No results for the file')
        elif retval == 0:
            logger.debug('No issues found')
        else:
            logger.debug('Exited with: %s', retval)

        return output or dumps({'results': {}})

    @staticmethod
    def analyse_file(file_proxy):
        logger.info('Running analysis on %s', file_proxy.filename)

        sys.argv = ['', '--json', '--find-config',
                    '--limit-files', file_proxy.filename]

        workspace = file_proxy.workspace
        if workspace is None:
            workspace = '.'
        chdir(workspace)

        stream, retval = coalaWrapper._run_coala()
        return coalaWrapper._get_op_from_coala(stream, retval)

    def p_analyse_file(self, file_proxy, force=False, **kargs):
        """
        It is a concurrent version of coalaWrapper.analyse_file().
        force indicates whether the request should pre-empt running
        cycles.
        """
        result = self._tracked_pool.exec_func(
            coalaWrapper.analyse_file, (file_proxy,), kargs, force=force)

        if result is False:
            logging.debug('Failed p_analysis_file() on %s', file_proxy)

        return result

    def close(self):
        self._tracked_pool.shutdown()
