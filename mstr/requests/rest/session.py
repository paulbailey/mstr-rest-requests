from .base import MSTRBaseSession
from .exceptions import ExecutionCancelledException, ExecutionFailedException, MSTRUnknownException
from .execution_status import CUBE_RUNNING, CUBE_PUBLISHED, CUBE_PREPARING
from .mixins import SessionPersistenceMixin
from mstr.requests.rest.api import AuthMixin, SessionsMixin, ObjectsMixin, DatasetsMixin, CubesMixin


class MSTRRESTSession(ObjectsMixin,
                      DatasetsMixin,
                      CubesMixin,
                      AuthMixin,
                      SessionsMixin,
                      SessionPersistenceMixin,
                      MSTRBaseSession):
    pass

    def execute_dataset_object(self, project_id, object_id):
        response = self.post('cubes/{}'.format(object_id), headers={
            'X-MSTR-ProjectID': project_id
        })
        if response.ok:
            return response.json()['instanceId']

    def get_dataset_instance_status(self, project_id, object_id, instance_id):
        response = self.get('datasets/{}/instances/{}/status'.format(object_id, instance_id), headers={
            'X-MSTR-ProjectID': project_id
        })
        if response.ok:
            resp_json = response.json()
            status = resp_json.get('code', None)
            if status:
                if status & CUBE_PUBLISHED == CUBE_PUBLISHED:
                    return CUBE_PUBLISHED
                elif status & CUBE_RUNNING == CUBE_RUNNING:
                    return CUBE_RUNNING
                elif status & CUBE_PREPARING == CUBE_PREPARING:
                    return CUBE_PREPARING
                else:
                    raise MSTRUnknownException(**resp_json)
            else:
                if 'User request is cancelled' in resp_json.get('message', ''):
                    raise ExecutionCancelledException(**resp_json)
                else:
                    raise ExecutionFailedException(**resp_json)
