from securedrop_client.queue import ApiJob

class DummyApiJob(ApiJob):

    def __init__(self) -> None:
        self.flag = False

    @staticmethod
    def call_api(api_client, nargs, kwargs) -> None:
        self.flag = True 
