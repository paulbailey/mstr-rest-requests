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

from .api import AuthMixin, ProjectsMixin, SessionsMixin
from .base import MSTRBaseSession


class MSTRRESTSession(
    AuthMixin,
    SessionsMixin,
    ProjectsMixin,
    HttpxSessionPersistenceMixin,
    MSTRBaseSession,
):
    """Full-featured httpx-based session for the MicroStrategy REST API.

    The httpx counterpart of the requests-based
    :class:`~mstr.requests.MSTRRESTSession`: the same methods, returning
    :class:`httpx.Response` objects.  Exported as
    :class:`mstr.requests.MSTRRESTSession`.  Use ``with`` (or
    :meth:`close`) to release the underlying connection pool; login and
    logout are up to you.  For automatic login/logout use
    :class:`~mstr.requests.rest.httpx_sync.AuthenticatedMSTRRESTSession`.

    Example::

        with MSTRRESTSession(base_url="https://.../api/") as session:
            session.login(username="dave", password="hellodave")
            projects = session.get_projects()
            session.logout()
    """
