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

import json
from typing import Any, Dict as DictType, TypeVar

import httpx

from mstr.requests.rest.exceptions import SessionException

from .api import AsyncAuthMixin, AsyncProjectsMixin, AsyncSessionsMixin
from .base import AsyncMSTRBaseSession

_T = TypeVar("_T", bound="AsyncSessionPersistenceMixin")


class AsyncSessionPersistenceMixin:
    """Mixin that adds serialisation and deserialisation to an async session.

    The format is the same as
    :class:`~mstr.requests.rest.mixins.SessionPersistenceMixin`, so a session
    saved by the synchronous class can be restored into the async one and
    vice versa.
    """

    base_url: str
    cookies: httpx.Cookies
    headers: httpx.Headers

    def to_dict(self) -> DictType[str, Any]:
        """Return a dict snapshot of the session state.

        The dict contains ``base_url``, ``cookies``, and ``headers``.
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

        Args:
            data: A dict (or JSON string) previously produced by
                :meth:`to_dict` or :meth:`json`, from either the async or the
                synchronous session.

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
            self.cookies = httpx.Cookies(input_data["cookies"])
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


class AsyncMSTRRESTSession(
    AsyncAuthMixin,
    AsyncSessionsMixin,
    AsyncProjectsMixin,
    AsyncSessionPersistenceMixin,
    AsyncMSTRBaseSession,
):
    """Full-featured async session for the MicroStrategy REST API.

    The async counterpart of :class:`~mstr.requests.MSTRRESTSession`: the
    same methods, awaited, returning :class:`httpx.Response` objects.  Use
    ``async with`` (or :meth:`aclose`) to release the underlying connection
    pool; login and logout are up to you.  For automatic login/logout use
    :class:`~mstr.requests.rest.aio.AsyncAuthenticatedMSTRRESTSession`.

    Example::

        async with AsyncMSTRRESTSession(base_url="https://.../api/") as session:
            await session.login(username="dave", password="hellodave")
            projects = await session.get_projects()
            await session.logout()
    """
