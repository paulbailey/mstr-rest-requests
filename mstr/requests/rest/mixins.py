# -*- coding: utf-8 -*-
# Copyright 2020 Paul Bailey
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        https://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from typing import Union
from .exceptions import SessionException

import json

from requests.utils import dict_from_cookiejar, cookiejar_from_dict


class SessionPersistenceMixin:
    def dict(self):
        return {
            "base_url": self.base_url,
            "cookies": dict_from_cookiejar(self.cookies),
            "headers": dict(self.headers),
        }

    def json(self):
        return json.dumps(self.dict())

    def update_from_json(self, data: Union[dict, str]):
        if type(data) is dict:
            input_data = data
        elif type(data) is str:
            input_data = json.loads(data)
        else:
            input_data = dict()

        try:
            self.base_url = input_data["base_url"]
            self.cookies = cookiejar_from_dict(input_data["cookies"])
            self.headers.update(input_data["headers"])
        except KeyError as e:
            raise SessionException(e)
