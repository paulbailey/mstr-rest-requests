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

import inspect
import logging
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Any, TypeAlias, cast

import anyio
import anyio.abc
import anyio.to_thread
import httpx

from mstr.requests.rest.core import (
    MSTR_AUTH_TOKEN,
    is_auth_url,
    is_session_expired,
    raise_for_unresolved_credentials,
)
from mstr.requests.rest.exceptions import SessionException

from .session import AsyncMSTRRESTSession

logger = logging.getLogger(__name__)

AsyncCredential: TypeAlias = (
    str | Callable[[], str] | Callable[[], Awaitable[str]] | None
)
"""A credential value for the async sessions: a plain string, a zero-argument
callable returning a string, or a zero-argument ``async def`` callable.  Synchronous
callables (such as the providers in :mod:`mstr.requests.credentials`) are run
in a worker thread so that a slow secrets-manager lookup does not block the
event loop."""


def _is_async_callable(value: object) -> bool:
    return inspect.iscoroutinefunction(value) or inspect.iscoroutinefunction(
        getattr(value, "__call__", None)
    )


async def _aresolve(value: AsyncCredential) -> str | None:
    """Resolve an :data:`AsyncCredential` to its string value.

    Async callables (``async def`` functions, partials of them, or objects
    with an ``async def __call__``) are awaited.  Other callables are run in
    a worker thread.
    """
    if not callable(value):
        return value
    if _is_async_callable(value):
        return cast(str, await value())  # type: ignore[misc]
    return cast(str, await anyio.to_thread.run_sync(value))


class AsyncAuthenticatedMSTRRESTSession(AsyncMSTRRESTSession):
    """Async context-managed session that logs in on entry and out on exit.

    The async counterpart of
    :class:`~mstr.requests.AuthenticatedMSTRRESTSession`.  Credentials are
    resolved when the context manager is entered, and the underlying client
    is closed on exit.  ``relogin`` and ``keepalive_interval`` work as they
    do for the synchronous class; the keep-alive runs as a task instead of a
    thread.

    Example::

        async with AsyncAuthenticatedMSTRRESTSession(
            base_url="https://env.example.com/api/",
            username="dave",
            password=fetch_password,  # sync or async callable
        ) as session:
            projects = await session.get_projects()

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
            :meth:`extend_session` while the ``async with`` block runs.
            ``None`` (the default) turns this off.
        **session_kwargs: Passed to
            :class:`~mstr.requests.rest.aio.base.AsyncMSTRBaseSession`, e.g.
            ``timeout`` or ``verify``.
    """

    def __init__(
        self,
        base_url: AsyncCredential = None,
        username: AsyncCredential = None,
        password: AsyncCredential = None,
        identity_token: AsyncCredential = None,
        api_key: AsyncCredential = None,
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
        self._auth_lock: anyio.Lock | None = None
        self._keepalive_group: anyio.abc.TaskGroup | None = None

    async def __aenter__(self) -> AsyncAuthenticatedMSTRRESTSession:
        try:
            if callable(self._base_url_credential):
                self.base_url = await _aresolve(self._base_url_credential) or ""
            await self._authenticate()
            await self._start_keepalive()
        except BaseException:
            await self.aclose()
            raise
        return self

    async def _authenticate(self) -> None:
        """Resolve the credentials and log in (or delegate) with them."""
        identity_token = await _aresolve(self._identity_token)
        api_key = await _aresolve(self._api_key)
        username = await _aresolve(self._username)
        password = await _aresolve(self._password)

        raise_for_unresolved_credentials(
            identity_token=(self._identity_token, identity_token),
            api_key=(self._api_key, api_key),
            username=(self._username, username),
            password=(self._password, password),
        )

        if identity_token is not None:
            await self.delegate(identity_token)
            self._used_delegate = True
        elif api_key is not None:
            await self.login(api_key=api_key, application_type=self._application_type)
            self._used_delegate = False
        else:
            await self.login(
                username=username,
                password=password,
                application_type=self._application_type,
            )
            self._used_delegate = False

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Send a request; see :meth:`AsyncMSTRBaseSession.request
        <mstr.requests.rest.aio.base.AsyncMSTRBaseSession.request>`.

        With ``relogin=True``, a request that fails with an expired session
        is sent again after logging in again.
        """
        token = self.headers.get(MSTR_AUTH_TOKEN)
        try:
            return await super().request(method, url, **kwargs)
        except SessionException as error:
            if not self._should_relogin(error, url, token, kwargs):
                raise
        if self._auth_lock is None:
            self._auth_lock = anyio.Lock()
        async with self._auth_lock:
            # Another task may have logged in again already.
            if self.headers.get(MSTR_AUTH_TOKEN) == token:
                logger.info("Session expired; logging in again")
                self.destroy_auth_token()
                await self._authenticate()
        return await super().request(method, url, **kwargs)

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

    async def _start_keepalive(self) -> None:
        if self.keepalive_interval is None:
            return
        group = anyio.create_task_group()
        await group.__aenter__()
        group.start_soon(self._keepalive_loop, self.keepalive_interval)
        self._keepalive_group = group

    async def _stop_keepalive(self) -> None:
        group = self._keepalive_group
        if group is None:
            return
        self._keepalive_group = None
        group.cancel_scope.cancel()
        await group.__aexit__(None, None, None)

    async def _keepalive_loop(self, interval: float) -> None:
        while True:
            await anyio.sleep(interval)
            try:
                await self.extend_session()
            except Exception:
                logger.warning("Keep-alive request failed", exc_info=True)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            await self._stop_keepalive()
            if not self._used_delegate:
                await self._logout_on_exit(exc_type)
        finally:
            await self.aclose()

    async def _logout_on_exit(self, exc_type: type[BaseException] | None) -> None:
        """Log out, without hiding an exception raised in the ``with`` block.

        An expired session (``SessionException``) is already logged out, so
        it is ignored.  Any other logout error is raised only if the block
        itself succeeded; otherwise it is logged and the block's exception
        propagates.
        """
        try:
            await self.logout()
        except SessionException:
            self.destroy_auth_token()
        except Exception:
            if exc_type is None:
                raise
            logger.warning("Logout failed while handling an exception", exc_info=True)
