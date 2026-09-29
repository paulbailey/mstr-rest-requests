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

from mstr.requests.rest.httpx_common import HttpxClientStateMixin

_B = TypeVar("_B", bound="MSTRBaseSession")


class MSTRBaseSession(HttpxClientStateMixin):
    """Low-level httpx session that manages auth-token headers and error translation.

    Wraps an :class:`httpx.Client` (available as ``client``) rather
    than subclassing it, so that the verb methods can accept the
    MicroStrategy-specific ``include_auth`` and ``project_id`` arguments.

    Response headers beginning with ``X-MSTR`` are captured and stored on the
    session, and JSON error payloads are translated into
    :mod:`~mstr.requests.rest.exceptions` types.

    Unlike httpx's own defaults, requests have no timeout and redirects are
    followed, matching the 1.x requests-based sessions.

    Args:
        base_url: MicroStrategy REST API root URL.  Relative request URLs
            are appended to it.
        timeout: Passed to :class:`httpx.Client`.  Defaults to no
            timeout.
        follow_redirects: Passed to :class:`httpx.Client`.
        client: An existing :class:`httpx.Client` to use instead of
            creating one.  The session does not close a client it was given.
        raise_on_http_error: Raise
            :class:`~mstr.requests.rest.exceptions.MSTRHTTPError` for an
            error response without a MicroStrategy JSON body, such as a
            proxy's HTML error page.  By default such responses are returned
            as they are.
        **client_kwargs: Any other :class:`httpx.Client` arguments,
            such as ``verify``, ``limits``, ``http2`` or ``transport``.
    """

    def __init__(
        self,
        base_url: str = "",
        *,
        timeout: Any = None,
        follow_redirects: bool = True,
        client: httpx.Client | None = None,
        raise_on_http_error: bool = False,
        **client_kwargs: Any,
    ) -> None:
        self.raise_on_http_error = raise_on_http_error
        self._owns_client = client is None
        if client is None:
            client = httpx.Client(
                timeout=timeout, follow_redirects=follow_redirects, **client_kwargs
            )
        self.client: httpx.Client = client
        self.base_url = base_url
        self._install_auth_scope_hook()

    def request(
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
            include_auth: Send the ``X-MSTR-AuthToken`` header when
                ``True`` (the default).  The token is only ever sent to the
                origin of *base_url*: absolute URLs and redirects to another
                scheme, host or port go without it.
            project_id: If given, sent as the ``X-MSTR-ProjectID`` header.
            headers: Extra headers for this request.
            **kwargs: Passed through to :meth:`httpx.Client.request`.

        Returns:
            An :class:`httpx.Response`.

        Raises:
            MSTRException: Or a subclass, on a MicroStrategy JSON error
                response, or on any error response when the session was
                created with ``raise_on_http_error=True``.  See :meth:`MSTRBaseSession.request
                <mstr.requests.rest.base.MSTRBaseSession.request>` for the
                full mapping.
        """
        request_headers = self._request_headers(url, headers, include_auth, project_id)
        kwargs["extensions"] = self._auth_scope_extensions(
            url, include_auth, kwargs.get("extensions")
        )
        response = self.client.request(method, url, headers=request_headers, **kwargs)
        return self._handle_response(response)

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a ``GET`` request.  See :meth:`request`."""
        return self.request("GET", url, **kwargs)

    def options(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send an ``OPTIONS`` request.  See :meth:`request`."""
        return self.request("OPTIONS", url, **kwargs)

    def head(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a ``HEAD`` request.  See :meth:`request`."""
        return self.request("HEAD", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a ``POST`` request.  See :meth:`request`."""
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a ``PUT`` request.  See :meth:`request`."""
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a ``PATCH`` request.  See :meth:`request`."""
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a ``DELETE`` request.  See :meth:`request`."""
        return self.request("DELETE", url, **kwargs)

    def close(self) -> None:
        """Close the underlying client, unless it was supplied by the caller."""
        if self._owns_client:
            self.client.close()

    def __enter__(self: _B) -> _B:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
