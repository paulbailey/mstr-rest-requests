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

from __future__ import annotations

from types import TracebackType
from typing import Any

from mstr.requests.rest.core import Credential, resolve_credential as _resolve

from .session import MSTRRESTSession


class AuthenticatedMSTRRESTSession(MSTRRESTSession):
    """Context-managed session that logs in on entry and out on exit.

    Each credential argument is a :data:`~mstr.requests.Credential`: a
    string or a zero-argument callable.  Credentials are resolved when the
    context manager is entered, and the underlying client is closed on exit.
    An ``identity_token`` takes precedence over an ``api_key``, which takes
    precedence over ``username``/``password``; with none of them the session
    connects anonymously.  Sessions created with an identity token are not
    logged out on exit.

    Example::

        with AuthenticatedMSTRRESTSession(
            base_url="https://env.example.com/api/",
            username="dave",
            password=fetch_password,
        ) as session:
            projects = session.get_projects()

    Args:
        base_url: MicroStrategy REST API root URL (or callable).
        username: Username for standard authentication (login mode 1).
        password: Password for standard authentication.
        identity_token: Token for delegated authentication (login mode -1).
        api_key: API key for trusted authentication (login mode 4096).
        application_type: MicroStrategy application type identifier.
        **session_kwargs: Passed to
            :class:`~mstr.requests.rest.httpx_sync.base.MSTRBaseSession`, e.g.
            ``timeout`` or ``verify``.
    """

    def __init__(
        self,
        base_url: Credential = None,
        username: Credential = None,
        password: Credential = None,
        identity_token: Credential = None,
        api_key: Credential = None,
        application_type: int = 8,
        **session_kwargs: Any,
    ):
        super().__init__(
            base_url if isinstance(base_url, str) else "", **session_kwargs
        )
        self._base_url_credential = base_url
        self._username = username
        self._password = password
        self._identity_token = identity_token
        self._api_key = api_key
        self._application_type = application_type
        self._used_delegate = False

    def __enter__(self) -> AuthenticatedMSTRRESTSession:
        try:
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
                self.login(api_key=api_key, application_type=self._application_type)
                self._used_delegate = False
            else:
                self.login(
                    username=username,
                    password=password,
                    application_type=self._application_type,
                )
                self._used_delegate = False
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            if not self._used_delegate:
                self.logout()
        finally:
            self.close()
