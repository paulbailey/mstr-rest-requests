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
from typing import Any, TypeVar

import anyio
import httpx

from mstr.requests.rest import core
from mstr.requests.rest.httpx_common import HttpxClientStateMixin

_B = TypeVar("_B", bound="AsyncMSTRBaseSession")


class AsyncMSTRBaseSession(HttpxClientStateMixin):
    """Low-level async session that manages auth-token headers and error translation.

    Wraps an :class:`httpx.AsyncClient` (available as ``client``) rather
    than subclassing it, so that the verb methods can accept the
    MicroStrategy-specific ``include_auth`` and ``project_id`` arguments.

    Response headers beginning with ``X-MSTR`` are captured and stored on the
    session, and JSON error payloads are translated into
    :mod:`~mstr.requests.rest.exceptions` types, exactly as the synchronous
    :class:`~mstr.requests.rest.base.MSTRBaseSession` does.

    Unlike httpx's own defaults, requests have no timeout and redirects are
    followed, matching the behaviour of the synchronous session.

    Args:
        base_url: MicroStrategy REST API root URL.  Relative request URLs
            are appended to it.
        timeout: Passed to :class:`httpx.AsyncClient`.  Defaults to no
            timeout.
        follow_redirects: Passed to :class:`httpx.AsyncClient`.
        client: An existing :class:`httpx.AsyncClient` to use instead of
            creating one.  The session does not close a client it was given.
        raise_on_http_error: Raise
            :class:`~mstr.requests.rest.exceptions.MSTRHTTPError` for an
            error response without a MicroStrategy JSON body, such as a
            proxy's HTML error page.  By default such responses are returned
            as they are.
        retries: How many times to retry a request that failed to connect,
            or (for ``GET``, ``HEAD``, ``OPTIONS``, ``PUT`` and ``DELETE``)
            that timed out, hit a network error or got a ``502``, ``503`` or
            ``504``.  Defaults to ``0``, no retries.
        backoff_factor: Seconds to wait before the first retry; the wait
            doubles for each further retry, up to 60 seconds.  A longer
            ``Retry-After`` from the server is honoured.
        **client_kwargs: Any other :class:`httpx.AsyncClient` arguments,
            such as ``verify``, ``limits``, ``http2`` or ``transport``.
    """

    def __init__(
        self,
        base_url: str = "",
        *,
        timeout: Any = None,
        follow_redirects: bool = True,
        client: httpx.AsyncClient | None = None,
        raise_on_http_error: bool = False,
        retries: int = 0,
        backoff_factor: float = 0.5,
        **client_kwargs: Any,
    ) -> None:
        self.raise_on_http_error = raise_on_http_error
        self.retries = retries
        self.backoff_factor = backoff_factor
        self._owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(
                timeout=timeout, follow_redirects=follow_redirects, **client_kwargs
            )
        self.client: httpx.AsyncClient = client
        self.base_url = base_url
        self._install_auth_scope_hook()

    async def request(
        self,
        method: str,
        url: str,
        *,
        include_auth: bool = True,
        project_id: str | None = None,
        project: str | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send a request, injecting MicroStrategy headers automatically.

        Args:
            method: HTTP method (``GET``, ``POST``, etc.).
            url: URL path relative to the session's *base_url*.
            include_auth: Send the ``X-MSTR-AuthToken`` header when
                ``True`` (the default).  The token is only ever sent to the
                origin of *base_url*: absolute URLs and redirects to another
                scheme, host or port go without it.
            project_id: If given, sent as the ``X-MSTR-ProjectID`` header.
            project: A project name, sent as the matching
                ``X-MSTR-ProjectID``.  The project list is fetched the first
                time a name is used (and again for a name it doesn't
                contain).  Pass *project* or *project_id*, not both.
            headers: Extra headers for this request.
            **kwargs: Passed through to :meth:`httpx.AsyncClient.request`.

        Returns:
            An :class:`httpx.Response`.

        Raises:
            MSTRException: Or a subclass, on a MicroStrategy JSON error
                response, or on any error response when the session was
                created with ``raise_on_http_error=True``.  See :meth:`MSTRBaseSession.request
                <mstr.requests.rest.base.MSTRBaseSession.request>` for the
                full mapping.
        """
        core.check_project_arguments(project, project_id)
        if project is not None:
            project_id = await self.resolve_project_id(project)
        request_headers = self._request_headers(url, headers, include_auth, project_id)
        kwargs["extensions"] = self._auth_scope_extensions(
            url, include_auth, kwargs.get("extensions")
        )
        attempt = 0
        while True:
            attempt += 1
            try:
                response = await self.client.request(
                    method, url, headers=request_headers, **kwargs
                )
            except httpx.TransportError as error:
                delay = self._retry_delay_after_error(method, error, attempt)
                if delay is None:
                    raise
                await anyio.sleep(delay)
                continue
            delay = self._retry_delay_after_response(method, response, attempt)
            if delay is None:
                break
            await response.aclose()
            await anyio.sleep(delay)
        self._log_response(response)
        return self._handle_response(response)

    async def resolve_project_id(self, project_name: str) -> str:
        """Return the ID of the project called *project_name*.

        Needs the project helpers of the full session classes; see
        ``ProjectsMixin.resolve_project_id``.
        """
        raise TypeError(self._NO_PROJECT_HELPERS)

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a ``GET`` request.  See :meth:`request`."""
        return await self.request("GET", url, **kwargs)

    async def options(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send an ``OPTIONS`` request.  See :meth:`request`."""
        return await self.request("OPTIONS", url, **kwargs)

    async def head(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a ``HEAD`` request.  See :meth:`request`."""
        return await self.request("HEAD", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a ``POST`` request.  See :meth:`request`."""
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a ``PUT`` request.  See :meth:`request`."""
        return await self.request("PUT", url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a ``PATCH`` request.  See :meth:`request`."""
        return await self.request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a ``DELETE`` request.  See :meth:`request`."""
        return await self.request("DELETE", url, **kwargs)

    async def aclose(self) -> None:
        """Close the underlying client, unless it was supplied by the caller."""
        if self._owns_client:
            await self.client.aclose()

    async def __aenter__(self: _B) -> _B:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.aclose()
