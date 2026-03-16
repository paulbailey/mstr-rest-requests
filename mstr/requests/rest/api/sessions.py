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

from typing import TYPE_CHECKING, cast

from requests import Response

from .utils import check_valid_session

if TYPE_CHECKING:
    from mstr.requests.rest.protocols import MSTRSessionProtocol


class SessionsMixin:
    """Mixin providing MicroStrategy session-management endpoints."""

    @check_valid_session
    def put_sessions(self: MSTRSessionProtocol) -> Response:
        """Prolong the session via ``PUT /sessions``.

        Returns:
            A :class:`requests.Response`.
        """
        return cast(Response, self.put("sessions"))

    @check_valid_session
    def get_sessions_userinfo(self: MSTRSessionProtocol) -> Response:
        """Retrieve user information via ``GET /sessions/userInfo``.

        Returns:
            A :class:`requests.Response` whose JSON body contains user
            details.
        """
        return cast(Response, self.get("sessions/userInfo"))

    @check_valid_session
    def get_sessions(self: MSTRSessionProtocol) -> Response:
        """Retrieve session status via ``GET /sessions``.

        Returns:
            A :class:`requests.Response`.
        """
        return cast(Response, self.get("sessions"))

    def extend_session(self) -> Response:
        """Prolong the current session.

        Convenience alias for :meth:`put_sessions`.
        """
        return cast(Response, self.put_sessions())

    def get_userinfo(self) -> Response:
        """Get the current user's information.

        Convenience alias for :meth:`get_sessions_userinfo`.
        """
        return cast(Response, self.get_sessions_userinfo())

    def get_session_info(self) -> Response:
        """Get the current session's status.

        Convenience alias for :meth:`get_sessions`.
        """
        return cast(Response, self.get_sessions())
