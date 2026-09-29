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

"""Code shared by the synchronous and asynchronous httpx-based sessions.

Nothing here performs I/O, so the same mixins serve both
:class:`httpx.Client` and :class:`httpx.AsyncClient`.
"""

from __future__ import annotations

import json
from typing import Any, Dict as DictType, TypeVar

import httpx

from mstr.requests.rest import core
from mstr.requests.rest.exceptions import SessionException

_T = TypeVar("_T", bound="HttpxSessionPersistenceMixin")

# Request extension carrying ``(allowed origin, include_auth)`` from
# ``request()`` to the auth-scope event hook, which runs on every redirect hop.
_AUTH_SCOPE = "mstr_requests.auth_scope"


class HttpxClientStateMixin:
    """Session state held on a wrapped httpx client.

    The host class sets :attr:`client` to an :class:`httpx.Client` or
    :class:`httpx.AsyncClient` and calls :meth:`_install_auth_scope_hook`.
    The auth token lives in the client's headers, but a request event hook
    removes it (and the other ``X-MSTR`` headers) from any request, including
    a redirect, whose origin differs from :attr:`base_url`'s.
    """

    client: httpx.Client | httpx.AsyncClient
    _owns_client: bool

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

    def _install_auth_scope_hook(self) -> None:
        """Register the event hook that keeps the token on the base URL's origin."""
        if isinstance(self.client, httpx.AsyncClient):

            async def hook(request: httpx.Request) -> None:
                self._scope_auth(request)

            self.client.event_hooks["request"].append(hook)
        else:
            self.client.event_hooks["request"].append(self._scope_auth)

    def _auth_scope_extensions(
        self, url: str, include_auth: bool, extensions: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Return request *extensions* with the auth scope for *url* added."""
        return {
            **(extensions or {}),
            _AUTH_SCOPE: (core.auth_scope_origin(self.base_url, url), include_auth),
        }

    def _scope_auth(self, request: httpx.Request) -> None:
        """Remove MicroStrategy headers that must not go with *request*."""
        scope = request.extensions.get(_AUTH_SCOPE)
        if scope is None:
            # Sent through the client directly, not through request().
            scope = (core.url_origin(self.base_url), True)
        origin, include_auth = scope
        if not include_auth:
            request.headers.pop(core.MSTR_AUTH_TOKEN, None)
        if origin is not None and core.url_origin(str(request.url)) != origin:
            for name in core.mstr_header_names(request.headers.keys()):
                request.headers.pop(name, None)

    def _request_headers(
        self,
        url: str,
        headers: dict[str, str] | None,
        include_auth: bool,
        project_id: str | None,
    ) -> dict[str, str]:
        core.warn_on_double_slash(url)
        return core.build_request_headers(
            headers, self.headers, include_auth, project_id
        )

    def _handle_response(self, response: httpx.Response) -> httpx.Response:
        if response.is_error:
            core.raise_for_mstr_error(response)
        else:
            self.headers.update(core.mstr_response_headers(response.headers.items()))
        return response


class HttpxSessionPersistenceMixin:
    """Mixin that adds serialisation and deserialisation to an httpx session.

    The format is the same as
    :class:`~mstr.requests.rest.mixins.SessionPersistenceMixin`, so a session
    saved by any of the session classes (requests, httpx or async) can be
    restored into any other.
    """

    base_url: str
    cookies: httpx.Cookies
    headers: httpx.Headers

    def to_dict(self) -> DictType[str, Any]:
        """Return a dict snapshot of the session state.

        The dict contains ``base_url``, ``cookies``, and ``headers``.

        .. warning::
           The snapshot includes the live auth token and session cookies.
           Anyone holding it can act as the logged-in user until the
           session expires, so store and pass it as a secret.
        """
        return {
            "base_url": self.base_url,
            "cookies": {cookie.name: cookie.value for cookie in self.cookies.jar},
            "headers": dict(self.headers),
        }

    def dict(self) -> DictType[str, Any]:
        """Alias for :meth:`to_dict`. Prefer :meth:`to_dict` for clarity."""
        return self.to_dict()

    def json(self) -> str:
        """Return a JSON string snapshot of the session state."""
        return json.dumps(self.to_dict())

    def update_from_json(self, data: DictType[str, Any] | str) -> None:
        """Restore session state from a dict or JSON string.

        Cookies are restored for the host of the restored ``base_url``
        only.

        Args:
            data: A dict (or JSON string) previously produced by
                :meth:`to_dict` or :meth:`json`, from any of the session classes.

        Raises:
            SessionException: If required keys are missing from *data*.
        """
        if type(data) is dict:
            input_data = data
        elif type(data) is str:
            input_data = json.loads(data)
        else:
            input_data = {}

        try:
            self.base_url = input_data["base_url"]
            cookies = httpx.Cookies()
            domain = core.cookie_domain(self.base_url)
            for name, value in input_data["cookies"].items():
                cookies.set(name, value, domain=domain)
            self.cookies = cookies
            self.headers.update(input_data["headers"])
        except KeyError as e:
            raise SessionException(str(e))

    @classmethod
    def from_dict(cls: type[_T], session_dict: DictType[str, Any], **kwargs: Any) -> _T:
        """Create a new session instance from a dict snapshot.

        Args:
            session_dict: A dict previously produced by :meth:`to_dict`.
            **kwargs: Passed to the session constructor, e.g. ``timeout``.

        Returns:
            A new session with state restored from *session_dict*.
        """
        base_url: str = session_dict.get("base_url", "")
        session: _T = cls(base_url=base_url, **kwargs)  # type: ignore[call-arg]
        session.update_from_json(session_dict)
        return session
