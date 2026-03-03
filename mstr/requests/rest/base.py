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

import warnings
from requests_toolbelt.sessions import BaseUrlSession

from mstr.requests.rest import exceptions

MSTR_AUTH_TOKEN = "X-MSTR-AuthToken"
MSTR_PROJECT_ID_HEADER = "X-MSTR-ProjectID"
MSTR_HEADER_PREFIX = "X-MSTR"


class MSTRBaseSession(BaseUrlSession):
    """Low-level session that manages auth-token headers and error translation.

    Extends :class:`~requests_toolbelt.sessions.BaseUrlSession` so that every
    request is automatically scoped to the MicroStrategy REST API base URL.
    Response headers beginning with ``X-MSTR`` are captured and stored on the
    session, and JSON error payloads are translated into
    :mod:`~mstr.requests.rest.exceptions` types.
    """

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
        include_auth=True,
        project_id: str = None,
        *args,
        **kwargs,
    ):
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
            LoginFailureException: On ``ERR001`` / ``ERR003`` responses.
            SessionException: On ``ERR009`` responses.
            ResourceNotFoundException: On ``ERR004`` responses.
            MSTRException: On any other MicroStrategy error response.
        """

        # Warn if the session and request in combination contain an extra `//`; that's probably in error.
        if url.count("//") > 1:
            warnings.warn(
                f"Your fully composed request ({url}) contains a `//` in the path, which is probably an error."
            )

        headers = kwargs.get("headers", {})

        if include_auth and MSTR_AUTH_TOKEN in self.headers:
            headers.update({MSTR_AUTH_TOKEN: self.headers[MSTR_AUTH_TOKEN]})

        if project_id is not None:
            headers.update({MSTR_PROJECT_ID_HEADER: project_id})

        kwargs["headers"] = headers

        response = super(MSTRBaseSession, self).request(method, url, *args, **kwargs)

        if not response.ok and response.headers["content-type"] == "application/json":
            try:
                resp_json = response.json()
                try:
                    resp_code = resp_json["code"]
                except KeyError:
                    raise exceptions.MSTRUnknownException(**resp_json)
                match resp_code:
                    case "ERR001" | "ERR003":
                        raise exceptions.LoginFailureException(**resp_json)
                    case "ERR009":
                        raise exceptions.SessionException(**resp_json)
                    case "ERR004":
                        raise exceptions.ResourceNotFoundException(**resp_json)
                    case _:
                        raise exceptions.MSTRException(**resp_json)
            except ValueError:
                raise exceptions.MSTRException(
                    "Couldn't parse response: {}".format(response.text)
                )
        if response.ok:
            for key, value in response.headers.items():
                if key.upper().startswith("X-MSTR"):
                    self.headers.update({key: value})
        return response
