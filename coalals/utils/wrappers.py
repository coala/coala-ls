from socketserver import StreamRequestHandler


def func_wrapper(func, *args, **kargs):
    """
    Minimal function wrapper to be used with process
    pool. ProcessPool requires function to be picklable.
    func_wrapper simplifies passing an callable to
    executor by wrapping it.

    :param func:
        The callable to wrap.
    :param args:
        The args to be passed to func callable.
    :return:
        The result of execution of func with args and kargs.
    """
    return func(*args, **kargs)


class StreamHandlerWrapper(StreamRequestHandler):
    """
    Wraps a stream processing class and abstracts setup and
    handle methods.
    """
    delegate = None

    def setup(self):
        """
        Initialize delegate class instance with read and write
        streams.
        """
        super(StreamHandlerWrapper, self).setup()
        self.delegate = self.DELEGATE_CLASS(self.rfile, self.wfile)

    def handle(self):
        """
        Start the delegate class on handle being called.
        """
        self.delegate.start()
