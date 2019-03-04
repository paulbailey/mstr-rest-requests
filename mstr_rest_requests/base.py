from requests_toolbelt.sessions import BaseUrlSession

from .exceptions import LoginFailureException, MSTRException, SessionException
from .utils import MSTR_AUTH_TOKEN, MSTR_HEADER_PREFIX


class MSTRBaseSession(BaseUrlSession):
    def has_session(self):
        return MSTR_AUTH_TOKEN in self.headers

    def destroy_auth_token(self):
        try:
            del self.headers[MSTR_AUTH_TOKEN]
        except KeyError:
            pass

    def request(self, method, url, include_auth=True, *args, **kwargs):

        headers = kwargs.get('headers', {})

        if include_auth and MSTR_AUTH_TOKEN in self.headers:
            headers.update({MSTR_AUTH_TOKEN: self.headers[MSTR_AUTH_TOKEN]})

        response = super(MSTRBaseSession, self).request(method, url, headers=headers, *args, **kwargs)

        if not response.ok and len(response.content) > 0:
            try:
                resp_json = response.json()
                try:
                    if resp_json['code'] in ['ERR003', 'ERR001']:
                        raise LoginFailureException(**resp_json)
                    elif resp_json['code'] == 'ERR009':
                        raise SessionException(**resp_json)
                except KeyError:
                    raise MSTRException(**resp_json)
                else:
                    raise MSTRException(**resp_json)
            except ValueError:
                raise MSTRException("Couldn't parse response: {}".format(response.text))
        if response.ok:
            for key, value in response.headers.items():
                if key.startswith('X-MSTR'):
                    self.headers.update({key: value})
        return response
