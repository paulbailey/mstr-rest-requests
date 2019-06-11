from requests_toolbelt.sessions import BaseUrlSession

from mstr.requests.rest import exceptions

MSTR_AUTH_TOKEN = 'X-MSTR-AuthToken'
MSTR_PROJECT_ID_HEADER = 'X-MSTR-ProjectID'
MSTR_HEADER_PREFIX = 'X-MSTR'


class MSTRBaseSession(BaseUrlSession):
    def has_session(self):
        return MSTR_AUTH_TOKEN in self.headers

    def destroy_auth_token(self):
        try:
            del self.headers[MSTR_AUTH_TOKEN]
        except KeyError:
            pass

    def request(self, method, url, include_auth=True, project_id=None, *args, **kwargs):

        headers = kwargs.get('headers', {})

        if include_auth and MSTR_AUTH_TOKEN in self.headers:
            headers.update({MSTR_AUTH_TOKEN: self.headers[MSTR_AUTH_TOKEN]})

        if project_id is not None:
            headers.update({
                MSTR_PROJECT_ID_HEADER: project_id
            })

        response = super(MSTRBaseSession, self).request(method, url, headers=headers, *args, **kwargs)

        if not response.ok and response.headers['content-type'] == 'application/json':
            try:
                resp_json = response.json()
                try:
                    resp_code = resp_json['code']
                except KeyError:
                    raise exceptions.MSTRUnknownException(**resp_json)
                if resp_code in ['ERR003', 'ERR001']:
                    raise exceptions.LoginFailureException(**resp_json)
                elif resp_code == 'ERR009':
                    raise exceptions.SessionException(**resp_json)
                elif resp_code == 'ERR004':
                    raise exceptions.ResourceNotFoundException(**resp_json)
                else:
                    raise exceptions.MSTRException(**resp_json)
            except ValueError:
                raise exceptions.MSTRException("Couldn't parse response: {}".format(response.text))
        if response.ok:
            for key, value in response.headers.items():
                if key.startswith('X-MSTR'):
                    self.headers.update({key: value})
        return response
