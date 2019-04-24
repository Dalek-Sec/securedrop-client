import time

from datetime import datetime, timedelta
from typing import Any, Optional  # noqa: F401

from securedrop_client.thread_utils import ThreadedOperation, _ThreadState, ThreadTimeoutError

DEFAULT_TIMEOUT = 500


class CallbackHelper:

    def __init__(self) -> None:
        self.is_success = None  # type: Optional[bool]
        self.has_result = False
        self._result = None

    @property
    def result(self) -> Any:
        if self.has_result:
            return self._result
        else:
            raise RuntimeError('Result not set')

    def on_success(self, result: object) -> None:
        print('called on success cb')
        self.is_success = True
        self.has_result = True
        self._result = result

    def on_failure(self, result: Exception) -> None:
        print('called on failure cb')
        self.is_success = False
        self.has_result = True
        self._result = result


def test_thread_op_success(qtbot):
    cb_helper = CallbackHelper()
    data = 'foo'

    def func():
        return data

    start = datetime.now()
    end = start + timedelta(microseconds=DEFAULT_TIMEOUT * 1000 * 2)
    thread_op = ThreadedOperation(
        func,
        timeout=DEFAULT_TIMEOUT,
        success_callback=cb_helper.on_success,
        failure_callback=cb_helper.on_failure,
    )

    while datetime.now() < end and thread_op._state == _ThreadState.Running:
        pass

    print(thread_op._helper)
    print(thread_op._helper.result)

    # assert thread_op._state == _ThreadState.Success
    assert cb_helper.has_result
    assert cb_helper.is_success is True
    assert cb_helper.result == data


def test_thread_op_failure(qtbot):
    cb_helper = CallbackHelper()
    exc = Exception('oh no')

    def func():
        raise exc

    start = datetime.now()
    end = start + timedelta(microseconds=DEFAULT_TIMEOUT * 1000 * 2)
    thread_op = ThreadedOperation(
        func,
        timeout=DEFAULT_TIMEOUT,
        success_callback=cb_helper.on_success,
        failure_callback=cb_helper.on_failure,
    )

    while datetime.now() < end and thread_op._state == _ThreadState.Running:
        pass

    print(thread_op._helper)
    print(thread_op._helper.result)

    # assert thread_op._state == _ThreadState.Failure
    assert cb_helper.has_result
    assert cb_helper.is_success is False
    assert cb_helper.result == exc


def test_thread_op_timeout(mocker, qtbot):
    cb_helper = CallbackHelper()

    timeout = 1  # millisecond

    def func():
        time.sleep(timeout * 1000 * 10)

    start = datetime.now()
    end = start + timedelta(microseconds=timeout * 1000 * 2)
    thread_op = ThreadedOperation(
        func,
        timeout=timeout,
        success_callback=cb_helper.on_success,
        failure_callback=cb_helper.on_failure,
    )

    while datetime.now() < end and thread_op._state == _ThreadState.Running:
        pass

    print(thread_op._helper)
    print(thread_op._helper.result)

    # assert thread_op._state == _ThreadState.Failure
    assert cb_helper.has_result
    assert cb_helper.is_success is False
    assert cb_helper.result == ThreadTimeoutError
