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

"""Structural type describing the interface that API mixins expect.

Mixins such as :class:`~mstr.requests.rest.api.auth.AuthMixin` and
:class:`~mstr.requests.rest.api.sessions.SessionsMixin` call HTTP
verbs and header helpers on ``self``.  This protocol makes those
implicit requirements explicit so that type checkers can verify
mixin composition and contributors can discover the available
surface without reading the base-class source.
"""

from __future__ import annotations

from http.cookiejar import CookieJar
from typing import Any, MutableMapping, Protocol, runtime_checkable

from requests import Response


@runtime_checkable
class MSTRSessionProtocol(Protocol):
    """Structural contract that all API mixins expect from the host session.

    :class:`~mstr.requests.rest.base.MSTRBaseSession` satisfies this
    protocol via its inheritance from
    :class:`~requests_toolbelt.sessions.BaseUrlSession` and
    :class:`requests.Session`.
    """

    base_url: str
    headers: MutableMapping[str, str]
    cookies: CookieJar

    def has_session(self) -> bool: ...
    def destroy_auth_token(self) -> None: ...
    def to_dict(self) -> dict[str, Any]: ...
    def delete(self, url: str, **kwargs: Any) -> Response: ...
    def get(self, url: str, **kwargs: Any) -> Response: ...
    def head(self, url: str, **kwargs: Any) -> Response: ...
    def options(self, url: str, **kwargs: Any) -> Response: ...
    def patch(self, url: str, **kwargs: Any) -> Response: ...
    def post(self, url: str, **kwargs: Any) -> Response: ...
    def put(self, url: str, **kwargs: Any) -> Response: ...
