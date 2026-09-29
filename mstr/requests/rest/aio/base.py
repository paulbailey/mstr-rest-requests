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

import httpx

from mstr.requests.rest import core

_B = TypeVar("_B", bound="AsyncMSTRBaseSession")


class AsyncMSTRBaseSession:
    """Low-level async session that manages auth-token headers and error translation.

    Wraps an :class:`httpx.AsyncClient` (available as :attr:`client`) rather
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
        **client_kwargs: Any,
    ) -> None:
        self._owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(
                timeout=timeout, follow_redirects=follow_redirects, **client_kwargs
            )
        self.client = client
        self.base_url = base_url

    @property
    def base_url(self) -> str:
        """The REST API root URL that relative request URLs are appended to."""
        return str(self.client.base_url)

    @base_url.setter
    def base_url(self, value: str) -> None:
        self.client.base_url = value

    @property
    def headers(self) -> httpx.Headers:
        """Headers sent with every request, including the auth token."""
        return self.client.headers

    @property
    def cookies(self) -> httpx.Cookies:
        """Cookies sent with every request."""
        return self.client.cookies

    @cookies.setter
    def cookies(self, value: httpx.Cookies) -> None:
        self.client.cookies = value

    def has_session(self) -> bool:
        """Return ``True`` if the session holds a valid auth token."""
        return core.MSTR_AUTH_TOKEN in self.headers

    def destroy_auth_token(self) -> None:
        """Remove the ``X-MSTR-AuthToken`` header, if present."""
        self.headers.pop(core.MSTR_AUTH_TOKEN, None)

    async def request(
        self,
        method: str,
        url: str,
        *,
        include_auth: bool = True,
        project_id: str | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send a request, injecting MicroStrategy headers automatically.

        Args:
            method: HTTP method (``GET``, ``POST``, etc.).
            url: URL path relative to the session's *base_url*.
            include_auth: Attach the ``X-MSTR-AuthToken`` header when
                ``True`` (the default).
            project_id: If given, sent as the ``X-MSTR-ProjectID`` header.
            headers: Extra headers for this request.
            **kwargs: Passed through to :meth:`httpx.AsyncClient.request`.

        Returns:
            An :class:`httpx.Response`.

        Raises:
            MSTRException: Or a subclass, on a MicroStrategy JSON error
                response.  See :meth:`MSTRBaseSession.request
                <mstr.requests.rest.base.MSTRBaseSession.request>` for the
                full mapping.
        """
        core.warn_on_double_slash(url)
        request_headers = core.build_request_headers(
            headers, self.headers, include_auth, project_id
        )
        response = await self.client.request(
            method, url, headers=request_headers, **kwargs
        )
        if response.is_error:
            core.raise_for_mstr_error(response)
        else:
            self.headers.update(core.mstr_response_headers(response.headers.items()))
        return response

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
