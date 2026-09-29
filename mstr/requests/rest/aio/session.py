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

from mstr.requests.rest.httpx_common import HttpxSessionPersistenceMixin

from .api import AsyncAuthMixin, AsyncProjectsMixin, AsyncSessionsMixin
from .base import AsyncMSTRBaseSession

# Kept for backwards compatibility; the mixin is shared with the sync httpx session.
AsyncSessionPersistenceMixin = HttpxSessionPersistenceMixin


class AsyncMSTRRESTSession(
    AsyncAuthMixin,
    AsyncSessionsMixin,
    AsyncProjectsMixin,
    HttpxSessionPersistenceMixin,
    AsyncMSTRBaseSession,
):
    """Full-featured async session for the MicroStrategy REST API.

    The async counterpart of :class:`~mstr.requests.MSTRRESTSession`: the
    same methods, awaited, returning :class:`httpx.Response` objects.  Use
    ``async with`` (or :meth:`~mstr.requests.AsyncMSTRRESTSession.aclose`) to release the underlying connection
    pool; login and logout are up to you.  For automatic login/logout use
    :class:`~mstr.requests.AsyncAuthenticatedMSTRRESTSession`.

    Example::

        async with AsyncMSTRRESTSession(base_url="https://.../api/") as session:
            await session.login(username="dave", password="hellodave")
            projects = await session.get_projects()
            await session.logout()
    """
