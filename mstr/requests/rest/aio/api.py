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

"""Async counterparts of the MicroStrategy REST API mixins.

Each method has the same name, arguments and behaviour as its synchronous
counterpart in :mod:`mstr.requests.rest.api`, but is a coroutine and returns
an :class:`httpx.Response`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, cast

from mstr.requests.rest import core
from mstr.requests.rest.api.utils import check_valid_session
from mstr.requests.rest.exceptions import SessionException

if TYPE_CHECKING:
    import httpx

    from .protocols import AsyncMSTRSessionProtocol

_T = TypeVar("_T", bound="AsyncMSTRSessionProtocol")


class AsyncAuthMixin:
    """Async mixin providing MicroStrategy REST API authentication methods."""

    async def post_login(
        self: _T,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        application_type: int = 8,
    ) -> httpx.Response:
        """Create an authenticated session via ``POST /auth/login``.

        See :func:`~mstr.requests.rest.core.login_payload` for how the login
        mode is chosen from the arguments.

        Raises:
            httpx.HTTPStatusError: If the server returns a non-204 status.
        """
        data = core.login_payload(username, password, api_key, application_type)
        login_response = await self.post("auth/login", json=data)
        if login_response.status_code != 204:
            login_response.raise_for_status()
        return login_response

    async def post_logout(self: _T) -> None:
        """Close the session via ``POST /auth/logout``.

        On success (``204``) the auth token is removed from the session
        headers.  Any other successful status leaves it in place.

        Raises:
            httpx.HTTPStatusError: If the server returns an error status without a
                MicroStrategy JSON error body.
        """
        logout_response = await self.post("auth/logout")
        if logout_response.status_code == 204:
            self.destroy_auth_token()
        else:
            logout_response.raise_for_status()

    async def login(
        self,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        application_type: int = 8,
    ) -> httpx.Response:
        """Log in to the MicroStrategy REST API.

        Convenience alias for :meth:`post_login`.  If no credentials are
        provided the session attempts an anonymous connection.
        """
        return await self.post_login(  # type: ignore[misc]
            username, password, api_key, application_type
        )

    async def logout(self) -> None:
        """Log out and close the current REST API session.

        Convenience alias for :meth:`post_logout`.
        """
        await self.post_logout()  # type: ignore[misc]

    async def delegate(self: _T, identity_token: str) -> httpx.Response:
        """Authenticate with a delegated identity token via ``POST /auth/delegate``.

        Raises:
            httpx.HTTPStatusError: If the server returns a non-204 status.
        """
        delegate_response = await self.post(
            "auth/delegate", json=core.delegate_payload(identity_token)
        )
        if delegate_response.status_code != 204:
            delegate_response.raise_for_status()
        return delegate_response


class AsyncSessionsMixin:
    """Async mixin providing MicroStrategy session-management endpoints."""

    @check_valid_session
    async def put_sessions(self: AsyncMSTRSessionProtocol) -> httpx.Response:
        """Prolong the session via ``PUT /sessions``."""
        return await self.put("sessions")

    @check_valid_session
    async def get_sessions_userinfo(
        self: AsyncMSTRSessionProtocol,
    ) -> httpx.Response:
        """Retrieve user information via ``GET /sessions/userInfo``."""
        return await self.get("sessions/userInfo")

    @check_valid_session
    async def get_sessions(self: AsyncMSTRSessionProtocol) -> httpx.Response:
        """Retrieve session status via ``GET /sessions``."""
        return await self.get("sessions")

    async def extend_session(self) -> httpx.Response:
        """Prolong the current session.

        Convenience alias for :meth:`put_sessions`.
        """
        return cast("httpx.Response", await self.put_sessions())

    async def get_userinfo(self) -> httpx.Response:
        """Get the current user's information.

        Convenience alias for :meth:`get_sessions_userinfo`.
        """
        return cast("httpx.Response", await self.get_sessions_userinfo())

    async def get_session_info(self) -> httpx.Response:
        """Get the current session's status.

        Convenience alias for :meth:`get_sessions`.
        """
        return cast("httpx.Response", await self.get_sessions())


class AsyncProjectsMixin:
    """Async mixin providing MicroStrategy project-related helpers."""

    @check_valid_session
    async def get_projects(
        self: AsyncMSTRSessionProtocol,
    ) -> list[dict[str, Any]]:
        """Fetch the list of projects via ``GET /projects``."""
        response = await self.get("projects")
        return cast(list[dict[str, Any]], response.json())

    async def load_projects(self) -> None:
        """Fetch projects and populate ``projects_by_name`` / ``projects_by_id`` look-ups."""
        self.projects_by_name, self.projects_by_id = core.project_lookups(
            await self.get_projects()
        )

    def get_project_id(self, project_name: str) -> str | None:
        """Return the project ID for *project_name*, or ``None`` if not found.

        :meth:`load_projects` must be awaited first.

        Raises:
            SessionException: If :meth:`load_projects` has not been awaited.
        """
        try:
            return self.projects_by_name.get(project_name, None)
        except AttributeError:
            raise SessionException("Call load_projects() before get_project_id()")
