from PyQt5.QtCore import QObject, QThread
from queue import Queue
from sdclientapi import API
from typing import Any, Optional


class ApiJob:

    def __init__(self, nargs: list, kwargs: dict) -> None:
        self.nargs = nargs
        self.kwargs = kwargs

    def _do_call_api(self, api_client: API) -> None:
        try:
            result = ApiJob.call_api(api_client, self.nargs, self.kwargs)
        except Exception as e:
            self.handle_failure(e)
        else:
            self.handle_success(result)

    @staticmethod
    def call_api(api_client: API, nargs: list, kwargs: dict) -> Any:
        raise NotImplementedError


class DownloadFileJob(ApiJob):

    @staticmethod
    def call_api(api_client: API, nargs: list, kwargs: dict) -> Any:
        return api_client.download_submission(*nargs, **kwargs)


class RunnableQueue(QObject):

    def __init__(self, api_client: API) -> None:
        super().__init__()
        self.queue = Queue()

    def __call__(self, loop: bool = True) -> None:
        while True:
            job = self.queue.get(block=True)  # type: ApiJob
            job._do_call_api(self.api_client)
            if not loop:
                break


class ApiJobQueue(QObject):

    def __init__(self, api_client: API, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.api_client = api_client
        self.main_queue = RunnableQueue(self.api_client)
        self.download_queue = RunnableQueue(self.api_client)

    def start_queues(self, loop: bool = True) -> None:
        main_thread = QThread(self)
        download_thread = QThread(self)

        self.main_queue.moveToThread(main_thread)
        self.download_queue.moveToThread(download_thread)

        main_thread.run()
        download_thread.run()

    def enqueue(self, job: ApiJob) -> None:
        if isinstance(job, DownloadFileJob):
            self.download_queue.queue.put_nowait(job)
        else:
            self.main_queue.queue.put_nowait(job)
