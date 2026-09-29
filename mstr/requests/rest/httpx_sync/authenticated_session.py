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
import threading
from types import TracebackType
from typing import Any

import httpx

from mstr.requests.rest.core import (
    MSTR_AUTH_TOKEN,
    Credential,
    is_auth_url,
    is_session_expired,
    raise_for_unresolved_credentials,
    resolve_credential as _resolve,
)
from mstr.requests.rest.exceptions import SessionException

from .session import MSTRRESTSession

logger = logging.getLogger(__name__)


class AuthenticatedMSTRRESTSession(MSTRRESTSession):
    """Context-managed session that logs in on entry and out on exit.

    Each credential argument is a :data:`~mstr.requests.Credential`: a
    string or a zero-argument callable.  Credentials are resolved when the
    context manager is entered, and the underlying client is closed on exit.
    An ``identity_token`` takes precedence over an ``api_key``, which takes
    precedence over ``username``/``password``; with none of them the session
    connects anonymously.  Sessions created with an identity token are not
    logged out on exit.

    With ``relogin=True``, a request that fails because the session has
    expired (``ERR009``) logs in again, resolving the credentials afresh, and
    is sent once more.  With ``keepalive_interval`` set, a background thread
    calls :meth:`extend_session` every that many seconds while the ``with``
    block runs, so a long job's session doesn't time out between requests.

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
        relogin: Log in again and retry once when a request fails with an
            expired session (``ERR009``).  Requests to ``auth/`` endpoints
            are never retried this way.
        keepalive_interval: Seconds between background calls to
            :meth:`extend_session` while the session is open.  ``None`` (the
            default) turns this off.  Keep it below the server's session
            timeout.
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
        *,
        relogin: bool = False,
        keepalive_interval: float | None = None,
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
        self.relogin = relogin
        self.keepalive_interval = keepalive_interval
        self._auth_lock = threading.Lock()
        self._keepalive_stop = threading.Event()
        self._keepalive_thread: threading.Thread | None = None

    def __enter__(self) -> AuthenticatedMSTRRESTSession:
        try:
            if callable(self._base_url_credential):
                self.base_url = self._base_url_credential()
            self._authenticate()
            self._start_keepalive()
        except BaseException:
            self.close()
            raise
        return self

    def _authenticate(self) -> None:
        """Resolve the credentials and log in (or delegate) with them."""
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

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Send a request; see :meth:`MSTRBaseSession.request
        <mstr.requests.rest.httpx_sync.base.MSTRBaseSession.request>`.

        With ``relogin=True``, a request that fails with an expired session
        is sent again after logging in again.
        """
        token = self.headers.get(MSTR_AUTH_TOKEN)
        try:
            return super().request(method, url, **kwargs)
        except SessionException as error:
            if not self._should_relogin(error, url, token, kwargs):
                raise
        with self._auth_lock:
            # Another thread may have logged in again already.
            if self.headers.get(MSTR_AUTH_TOKEN) == token:
                logger.info("Session expired; logging in again")
                self.destroy_auth_token()
                self._authenticate()
        return super().request(method, url, **kwargs)

    def _should_relogin(
        self,
        error: SessionException,
        url: str,
        token: str | None,
        kwargs: dict[str, Any],
    ) -> bool:
        return (
            self.relogin
            and token is not None
            and kwargs.get("include_auth", True)
            and is_session_expired(error)
            and not is_auth_url(url)
        )

    def _start_keepalive(self) -> None:
        if self.keepalive_interval is None:
            return
        self._keepalive_stop.clear()
        self._keepalive_thread = threading.Thread(
            target=self._keepalive_loop,
            args=(self.keepalive_interval,),
            name="mstr-requests-keepalive",
            daemon=True,
        )
        self._keepalive_thread.start()

    def _stop_keepalive(self) -> None:
        thread = self._keepalive_thread
        if thread is None:
            return
        self._keepalive_stop.set()
        thread.join(timeout=5)
        self._keepalive_thread = None

    def _keepalive_loop(self, interval: float) -> None:
        while not self._keepalive_stop.wait(interval):
            try:
                self.extend_session()
            except Exception:
                logger.warning("Keep-alive request failed", exc_info=True)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            self._stop_keepalive()
            if not self._used_delegate:
                self._logout_on_exit(exc_type)
        finally:
            self.close()

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
