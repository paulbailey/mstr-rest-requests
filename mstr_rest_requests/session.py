from .base import MSTRBaseSession
from .exceptions import ExecutionCancelledException, ExecutionFailedException, MSTRUnknownException, SessionException
from .execution_status import CUBE_RUNNING, CUBE_PUBLISHED, CUBE_PREPARING
from .mixins import SessionPersistenceMixin


class MSTRRESTSession(SessionPersistenceMixin, MSTRBaseSession):

    def login(self, username=None, password=None):
        if username is not None and password is not None:
            data = {
                'username': username,
                'password': password,
                'loginMode': 1
            }
        else:
            data = {
                'loginMode': 8
            }
        login_response = self.post('auth/login', data=data)
        if login_response.status_code != 204:
            login_response.raise_for_status()
        return login_response

    def logout(self):
        logout_response = self.post('auth/logout')
        if logout_response.status_code == 204:
            self.destroy_auth_token()

    def extend_session(self):
        if self.has_session():
            self.put('sessions')
        else:
            raise SessionException('There is no session to extend.')

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
