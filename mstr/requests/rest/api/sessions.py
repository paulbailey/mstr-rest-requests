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

from .utils import check_valid_session


class SessionsMixin:
    """Mixin providing MicroStrategy session-management endpoints."""

    @check_valid_session
    def put_sessions(self):
        """Prolong the session via ``PUT /sessions``.

        Returns:
            A :class:`requests.Response`.
        """
        return self.put("sessions")

    @check_valid_session
    def get_sessions_userinfo(self):
        """Retrieve user information via ``GET /sessions/userInfo``.

        Returns:
            A :class:`requests.Response` whose JSON body contains user
            details.
        """
        return self.get("sessions/userInfo")

    @check_valid_session
    def get_sessions(self):
        """Retrieve session status via ``GET /sessions``.

        Returns:
            A :class:`requests.Response`.
        """
        return self.get("sessions")

    def extend_session(self):
        """Prolong the current session.

        Convenience alias for :meth:`put_sessions`.
        """
        return self.put_sessions()

    def get_userinfo(self):
        """Get the current user's information.

        Convenience alias for :meth:`get_sessions_userinfo`.
        """
        return self.get_sessions_userinfo()

    def get_session_info(self):
        """Get the current session's status.

        Convenience alias for :meth:`get_sessions`.
        """
        return self.get_sessions()
