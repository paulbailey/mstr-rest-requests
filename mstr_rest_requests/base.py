from requests_toolbelt.sessions import BaseUrlSession

from .exceptions import LoginFailureException, MSTRException, SessionException, MSTRUnknownException

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

        if not response.ok and len(response.content) > 0:
            try:
                resp_json = response.json()
                try:
                    if resp_json['code'] in ['ERR003', 'ERR001']:
                        raise LoginFailureException(**resp_json)
                    elif resp_json['code'] == 'ERR009':
                        raise SessionException(**resp_json)
                    else:
                        raise MSTRException(**resp_json)
                except KeyError:
                    raise MSTRUnknownException(**resp_json)
            except ValueError:
                raise MSTRException("Couldn't parse response: {}".format(response.text))
        if response.ok:
            for key, value in response.headers.items():
                if key.startswith('X-MSTR'):
                    self.headers.update({key: value})
        return response
