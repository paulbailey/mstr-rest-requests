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

from typing import Callable, Optional, Union

from .session import MSTRRESTSession

Credential = Union[str, Callable[[], str], None]
"""A credential value: either a plain string or a zero-argument callable that
returns a string.  Callables are resolved lazily when the session's context
manager is entered, making it easy to integrate secrets managers or other
deferred-lookup strategies."""


def _resolve(value: Credential) -> Optional[str]:
    """Resolve a :data:`Credential` to its string value.

    If *value* is callable it is invoked and the result returned; otherwise
    *value* is returned as-is.
    """
    if callable(value):
        return value()
    return value


class AuthenticatedMSTRRESTSession(MSTRRESTSession):
    """Context-managed session that logs in on entry and out on exit.

    All credential parameters accept a :data:`Credential` -- either a plain
    string **or** a zero-argument callable returning a string.  Callables are
    resolved when the context manager is entered, not at construction time.
    This enables integration with secrets managers and other deferred-lookup
    strategies.

    Example::

        with AuthenticatedMSTRRESTSession(
            base_url="https://env.example.com/api/",
            username=lambda: fetch_username(),
            password=lambda: fetch_password(),
        ) as session:
            session.get("projects")

    Args:
        base_url: MicroStrategy REST API root URL (or callable).
        username: Username for standard authentication (login mode 1).
        password: Password for standard authentication.
        identity_token: Token for delegated authentication (login mode -1).
        api_key: API key for trusted authentication (login mode 4096).
        application_type: MicroStrategy application type identifier.
    """

    def __init__(
        self,
        base_url: Credential = None,
        username: Credential = None,
        password: Credential = None,
        identity_token: Credential = None,
        api_key: Credential = None,
        application_type: int = 8,
    ):
        super(AuthenticatedMSTRRESTSession, self).__init__(
            base_url if isinstance(base_url, str) else ""
        )
        self._base_url_credential = base_url
        self._username = username
        self._password = password
        self._identity_token = identity_token
        self._api_key = api_key
        self._application_type = application_type
        self._used_delegate = False

    def __enter__(self):
        if callable(self._base_url_credential):
            self.base_url = self._base_url_credential()

        identity_token = _resolve(self._identity_token)
        api_key = _resolve(self._api_key)
        username = _resolve(self._username)
        password = _resolve(self._password)

        if identity_token is not None:
            self.delegate(identity_token)
            self._used_delegate = True
        elif api_key is not None:
            self.login(api_key, None, self._application_type)
            self._used_delegate = False
        else:
            self.login(username, password, self._application_type)
            self._used_delegate = False
        return self

    def __exit__(self, t, v, tb):
        if not self._used_delegate:
            self.logout()
