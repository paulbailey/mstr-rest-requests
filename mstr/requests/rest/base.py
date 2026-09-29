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

from typing import Any, cast

from requests import PreparedRequest, Response
from requests_toolbelt.sessions import BaseUrlSession

from mstr.requests.rest import core
from mstr.requests.rest.core import (  # noqa: F401 -- re-exported for compatibility
    MSTR_AUTH_TOKEN,
    MSTR_HEADER_PREFIX,
    MSTR_PROJECT_ID_HEADER,
)


class MSTRBaseSession(BaseUrlSession):
    """Low-level session that manages auth-token headers and error translation.

    Extends :class:`~requests_toolbelt.sessions.BaseUrlSession` so that every
    request is automatically scoped to the MicroStrategy REST API base URL.
    Response headers beginning with ``X-MSTR`` are captured and stored on the
    session, and JSON error payloads are translated into
    :mod:`~mstr.requests.rest.exceptions` types.

    The auth token (and the other ``X-MSTR`` headers) are only sent to the
    origin of *base_url*: absolute URLs and redirects to another scheme,
    host or port go without them.

    Set :attr:`raise_on_http_error` to ``True`` to raise
    :class:`~mstr.requests.rest.exceptions.MSTRHTTPError` for error
    responses without a MicroStrategy JSON body.
    """

    raise_on_http_error: bool = False

    def has_session(self) -> bool:
        """Return ``True`` if the session holds a valid auth token."""
        return MSTR_AUTH_TOKEN in self.headers

    def destroy_auth_token(self) -> None:
        """Remove the ``X-MSTR-AuthToken`` header, if present."""
        try:
            del self.headers[MSTR_AUTH_TOKEN]
        except KeyError:
            pass

    def request(
        self,
        method: str,
        url: str,
        include_auth: bool = True,
        project_id: str | None = None,
        *args,
        **kwargs,
    ) -> Response:
        """Send a request, injecting MicroStrategy headers automatically.

        Args:
            method: HTTP method (``GET``, ``POST``, etc.).
            url: URL path relative to the session's *base_url*.
            include_auth: Attach the ``X-MSTR-AuthToken`` header when
                ``True`` (the default).
            project_id: If given, sent as the ``X-MSTR-ProjectID`` header.
            *args: Passed through to :meth:`requests.Session.request`.
            **kwargs: Passed through to :meth:`requests.Session.request`.

        Returns:
            A :class:`requests.Response`.

        Raises:
            LoginFailureException: On ``ERR003`` responses.
            IServerException: On ``ERR002`` / ``ERR0013`` responses.
            ResourceNotFoundException: On ``ERR004`` responses.
            InvalidRequestException: On ``ERR005`` / ``ERR006`` / ``ERR007``.
            SessionException: On ``ERR009`` responses.
            InsufficientPrivilegesException: On ``ERR0014`` / ``ERR0017``.
            ObjectAlreadyExistsException: On ``ERR0015`` responses.
            MSTRException: On any other MicroStrategy error response.
        """

        core.warn_on_double_slash(url)

        headers: dict[str, Any] = core.build_request_headers(
            kwargs.get("headers"), self.headers, include_auth, project_id
        )
        # requests drops session headers whose per-request value is None.
        if not include_auth:
            headers[MSTR_AUTH_TOKEN] = None
        full_url = self.create_url(url)
        if core.url_origin(full_url) != core.auth_scope_origin(
            self.base_url or "", full_url
        ):
            for name in core.mstr_header_names([*self.headers, *headers]):
                headers[name] = None
        kwargs["headers"] = headers

        response = super(MSTRBaseSession, self).request(method, url, *args, **kwargs)

        if not response.ok:
            core.raise_for_mstr_error(response, self.raise_on_http_error)
        else:
            self.headers.update(core.mstr_response_headers(response.headers.items()))
        return cast(Response, response)

    def rebuild_auth(
        self, prepared_request: PreparedRequest, response: Response
    ) -> None:
        """Also remove ``X-MSTR`` headers on a redirect to another origin."""
        super().rebuild_auth(prepared_request, response)
        url = prepared_request.url or ""
        scope = core.auth_scope_origin(self.base_url or "", response.request.url or "")
        if core.url_origin(url) != scope:
            for name in core.mstr_header_names(list(prepared_request.headers)):
                del prepared_request.headers[name]
