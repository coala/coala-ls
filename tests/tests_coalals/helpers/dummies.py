class DummyFileProxy:

    def __init__(self, filename, workspace='.', content=''):
        self.filename = filename
        self.workspace = workspace
        self.content = content
        self.version = -1


class DummyFileProxyMap:

    def __init__(self, file_map={}):
        self.file_map = file_map

    def resolve(self, name):
        return self.file_map.get(name)


class DummyDiagnostics:

    def __init__(self, warnings=[], fixes=[]):
        self.f_warnings = warnings
        self.f_fixes = fixes

    def warnings(self):
        return self.f_warnings


class DummyFuture:

    def __init__(self, active=True, on_cancel=True, result=None):
        self.f_active = active
        self.f_result = result
        self.f_cancel = on_cancel
        self._cancelled = False

    def done(self):
        return not self.f_active

    def cancel(self):
        if self.f_cancel:
            self.f_active = False

        self._cancelled = True
        return self.f_cancel

    def cancelled(self):
        return self._cancelled

    def exception(self):
        return None

    def result(self):
        return self.f_result

    def add_done_callback(self, func):
        func(self)


class DummyAlwaysCancelledFuture(DummyFuture):

    def __init__(self, active=True, on_cancel=True, result=None):
        DummyFuture.__init__(self, active, on_cancel, result)
        self._cancelled = True


class DummyAlwaysExceptionFuture(DummyFuture):

    def exception(self):
        return Exception()


class DummyProcessPoolExecutor:

    FutureClass = DummyFuture
    on_submit = None

    def __init__(self, max_workers=1, *args, **kargs):
        self._max_workers = max_workers

    def submit(self, func, *args, **kargs):
        self._func = lambda: func(*args, **kargs)
        result = self._func()

        if DummyProcessPoolExecutor.on_submit is None:
            return DummyProcessPoolExecutor.FutureClass(result=result)
        else:
            return DummyProcessPoolExecutor.on_submit

    def shutdown(self, *args, **kargs):
        self._closed = True
        return True


class DummyLangServer:

    def __init__(self, rfile, wfile, *args, **kargs):
        self.f_rfile = rfile
        self.f_wfile = wfile
        self.started = False

    def start(self):
        self.started = True


class DummyTCPServer:

    panic = False
    served = False
    closed = False
    keyboard_interrupt = False

    def __init__(self, *args, **kargs):
        if DummyTCPServer.panic:
            raise Exception()

    def serve_forever(self):
        DummyTCPServer.served = True
        if DummyTCPServer.keyboard_interrupt:
            raise KeyboardInterrupt()

    def server_close(self):
        DummyTCPServer.closed = True
