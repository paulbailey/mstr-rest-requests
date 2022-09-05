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

from .session import MSTRRESTSession


class AuthenticatedMSTRRESTSession(MSTRRESTSession):
    """A context manager for sessions interacting with the MicroStrategy REST API."""

    def __init__(
        self,
        base_url: str,
        username: str = None,
        password: str = None,
        identity_token: str = None,
        application_type: int = 8,
    ):
        super(AuthenticatedMSTRRESTSession, self).__init__(base_url)
        self._username = username
        self._password = password
        self._identity_token = identity_token
        self._application_type = application_type

    def __enter__(self):
        if self._identity_token is not None:
            self.delegate(self._identity_token)
        else:
            self.login(self._username, self._password, self._application_type)
        return self

    def __exit__(self, t, v, tb):
        if self._identity_token is None:
            self.logout()
