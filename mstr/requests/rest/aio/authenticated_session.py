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
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Any, TypeAlias, cast

import anyio.to_thread

from .session import AsyncMSTRRESTSession

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
    is closed on exit.

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

    async def __aenter__(self) -> AsyncAuthenticatedMSTRRESTSession:
        try:
            if callable(self._base_url_credential):
                self.base_url = await _aresolve(self._base_url_credential) or ""

            identity_token = await _aresolve(self._identity_token)
            api_key = await _aresolve(self._api_key)
            username = await _aresolve(self._username)
            password = await _aresolve(self._password)

            if identity_token is not None:
                await self.delegate(identity_token)
                self._used_delegate = True
            elif api_key is not None:
                await self.login(
                    api_key=api_key, application_type=self._application_type
                )
                self._used_delegate = False
            else:
                await self.login(
                    username=username,
                    password=password,
                    application_type=self._application_type,
                )
                self._used_delegate = False
        except BaseException:
            await self.aclose()
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            if not self._used_delegate:
                await self.logout()
        finally:
            await self.aclose()
