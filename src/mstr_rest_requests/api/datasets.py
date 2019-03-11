from .utils import check_valid_session


class DatasetStatus:
    UNKNOWN = -1
    READY = 1
    PROCESSING = 2
    NOT_READY = 4

    @staticmethod
    def is_ready(status):
        return status & DatasetStatus.READY == DatasetStatus.READY

    @staticmethod
    def is_processing(status):
        return status & DatasetStatus.PROCESSING == DatasetStatus.PROCESSING

    @staticmethod
    def is_not_ready(status):
        return status & DatasetStatus.NOT_READY == DatasetStatus.NOT_READY


class DatasetsMixin:

    @check_valid_session
    def get_datasets_instance_status(self, project_id, dataset_id, instance_id):
        return self.get('datasets/{}/instances/{}/status'.format(dataset_id, instance_id), project_id=project_id)

    # "Friendly" method aliases
    def get_dataset_status(self, project_id, dataset_id, instance_id):
        return DatasetStatusResponse(self.get_datasets_instance_status(project_id, dataset_id, instance_id))


class DatasetStatusResponse:

    def __init__(self, response):
        if response.headers['content-type'] == 'application/json':
            json = response.json()
            self.code = json.get('code', -1)
            self.message = json.get('message', '')
        else:
            self.code = -1
            self.message = 'No error message found'
