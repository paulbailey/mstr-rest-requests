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

import logging
from types import TracebackType

from .core import (
    Credential,
    raise_for_unresolved_credentials,
    resolve_credential,
)
from .exceptions import SessionException
from .session import MSTRRESTSession

logger = logging.getLogger(__name__)

# Kept for backwards compatibility; both now live in core.
_resolve = resolve_credential

__all__ = ["AuthenticatedMSTRRESTSession", "Credential"]


class AuthenticatedMSTRRESTSession(MSTRRESTSession):
    """Context-managed session that logs in on entry and out on exit.

    All credential parameters accept a :data:`~mstr.requests.Credential` -- either a plain
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

    def __enter__(self) -> AuthenticatedMSTRRESTSession:
        if callable(self._base_url_credential):
            self.base_url = self._base_url_credential()

        identity_token = _resolve(self._identity_token)
        api_key = _resolve(self._api_key)
        username = _resolve(self._username)
        password = _resolve(self._password)

        raise_for_unresolved_credentials(
            identity_token=(self._identity_token, identity_token),
            api_key=(self._api_key, api_key),
            username=(self._username, username),
            password=(self._password, password),
        )

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
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if not self._used_delegate:
            self._logout_on_exit(exc_type)

    def _logout_on_exit(self, exc_type: type[BaseException] | None) -> None:
        """Log out, without hiding an exception raised in the ``with`` block.

        An expired session (``SessionException``) is already logged out, so
        it is ignored.  Any other logout error is raised only if the block
        itself succeeded; otherwise it is logged and the block's exception
        propagates.
        """
        try:
            self.logout()
        except SessionException:
            self.destroy_auth_token()
        except Exception:
            if exc_type is None:
                raise
            logger.warning("Logout failed while handling an exception", exc_info=True)
