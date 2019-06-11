from .exceptions import SessionException

import json

from requests.utils import dict_from_cookiejar, cookiejar_from_dict


class SessionPersistenceMixin:
    def json(self):
        return json.dumps({
            'base_url': self.base_url,
            'cookies': dict_from_cookiejar(self.cookies),
            'headers': self.headers
        })

    def update_from_json(self, data):
        if type(data) is dict:
            input_data = data
        elif type(data) is str:
            input_data = json.loads(data)
        else:
            input_data = dict()

        try:
            self.base_url = input_data['base_url']
            self.cookies = cookiejar_from_dict(input_data['cookies'])
            self.headers.update(input_data['headers'])
        except KeyError as e:
            raise SessionException(e)
