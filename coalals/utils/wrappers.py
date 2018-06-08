from socketserver import StreamRequestHandler


def func_wrapper(func, *args, **kargs):
    return func(*args, **kargs)


class StreamHandlerWrapper(StreamRequestHandler):
    delegate = None

    def setup(self):
        super(StreamHandlerWrapper, self).setup()
        self.delegate = self.DELEGATE_CLASS(self.rfile, self.wfile)

    def handle(self):
        self.delegate.start()
