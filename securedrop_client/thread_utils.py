from contextlib import contextmanager
from enum import Enum
from PyQt5.QtCore import QObject, QThread, QTimer, QMutex, pyqtSignal
from typing import Callable, Optional, Any


@contextmanager
def lock_mutex(mutex):
    mutex.lock()
    print('locking')
    try:
        yield
    finally:
        print('unlocking')
        mutex.unlock()


class ThreadTimeoutError(Exception):

    def __init__(self) -> None:
        super().__init__('QThread timed out.')


class _ThreadState(Enum):

    Running = 1
    Success = 2
    Failure = 3


class ThreadedOperation(QObject):

    def __init__(
        self,
        func: Callable,
        nargs: Optional[list] = None,
        kwargs: Optional[dict] = None,
        timeout: Optional[int] = 20000,
        success_callback: Optional[Callable[[object], None]] = None,
        failure_callback: Optional[Callable[[Exception], None]] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._state = _ThreadState.Running
        self._thread = QThread()
        self._is_timed_out = False

        if not nargs:
            nargs = []

        if not kwargs:
            kwargs = {}

        self._helper = _ThreadHelper(func, nargs, kwargs)
        self._helper.moveToThread(self._thread)
        self._thread.started.connect(self._helper.run)
        self._thread.finished.connect(self._on_thread_finished)

        self._helper.call_success.connect(self._set_thread_success)
        if success_callback:
            self._helper.call_success.connect(success_callback)

        self._helper.call_failure.connect(self._set_thread_failure)
        if failure_callback:
            self._helper.call_failure.connect(failure_callback)

        if timeout is not None:  # yes, "is not None" because 0 is valid
            timer = QTimer()
            timer.setSingleShot(True)
            timer.start(timeout)
            timer.timeout.connect(self._on_timeout)

        self._thread.start()

    def _set_thread_success(self, result: object) -> None:
        print('set succ')
        with lock_mutex(self._helper._mutex):
            print('in mutex succ')
            if self._state == _ThreadState.Running:
                print('setting')
                self._state = _ThreadState.Success
                print(self._state)

    def _set_thread_failure(self, result: Exception) -> None:
        print('set fail')
        with lock_mutex(self._helper._mutex):
            print('in mutex fali')
            if self._state == _ThreadState.Running:
                print('setting')
                self._state = _ThreadState.Failure
                print(self._state)

    def _on_thread_finished(self) -> None:
        print('on fin')
        with lock_mutex(self._helper._mutex):
            print("in mutex fin")
            print(self._state)
            if self._state == _ThreadState.Running:
                if self._helper.is_success and not self._is_timed_out:
                    print('setting succ')
                    self._state = _ThreadState.Success
                else:
                    print('setting fail')
                    self._state = _ThreadState.Failure
            print(self._state)

    def _on_timeout(self) -> None:
        print('on time')
        with lock_mutex(self._helper._mutex):
            print('in mutex time')
            if self._state == _ThreadState.Running:
                self._state = _ThreadState.Failure
            self._is_timed_out = True
            self._thread._exit(1)
            self._helper._set_result(False, ThreadTimeoutError)


class _ThreadHelper(QObject):

    call_success = pyqtSignal(object)
    call_failure = pyqtSignal(Exception)

    def __init__(
        self,
        func: Callable,
        nargs: list,
        kwargs: dict,
    ) -> None:
        super().__init__()
        self._func = func
        self._nargs = nargs
        self._kwargs = kwargs
        self._mutex = QMutex()

        self.is_completed = False
        self.is_success = None  # type: Optional[bool]
        self.result = None  # type: Optional[Any]

    def run(self) -> None:
        try:
            result = self._func(*self._nargs, **self._kwargs)
            self._set_result(True, result)
        except Exception as e:
            self._set_result(False, e)

    def _set_result(self, is_success: bool, result: Any) -> None:
        print('set res')
        if not self.is_completed:
            self.is_completed = True
            self.is_success = is_success
            self.result = result

        if is_success:
            self.call_success.emit(result)
        else:
            self.call_failure.emit(result)

    def __repr__(self) -> str:
        return '<{} is_completed={} is_success={}>'.format(
            self.__class__.__name__,
            self.is_completed,
            self.is_success,
        )
