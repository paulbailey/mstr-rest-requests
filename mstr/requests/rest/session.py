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

from .base import MSTRBaseSession
from .mixins import SessionPersistenceMixin
from mstr.requests.rest.api import (
    AuthMixin,
    ProjectsMixin,
    SessionsMixin,
)


class MSTRRESTSession(
    AuthMixin,
    SessionsMixin,
    ProjectsMixin,
    SessionPersistenceMixin,
    MSTRBaseSession,
):
    """Full-featured session for the MicroStrategy REST API.

    Combines authentication, session management, project helpers, and
    serialisation into a single :class:`requests.Session` subclass.  Use
    this class directly when you need manual control over the session
    lifecycle, or prefer :class:`~mstr.requests.rest.authenticated_session.AuthenticatedMSTRRESTSession`
    for automatic login/logout via a context manager.
    """
