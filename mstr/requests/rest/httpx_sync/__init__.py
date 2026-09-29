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

"""Synchronous sessions for the MicroStrategy REST API, built on httpx.

These will replace the requests-based classes as the default in 2.0.  Import
them from :mod:`mstr.requests.httpx`.
"""

from .api import AuthMixin, ProjectsMixin, SessionsMixin
from .authenticated_session import AuthenticatedMSTRRESTSession
from .base import MSTRBaseSession
from .protocols import MSTRSessionProtocol
from .session import MSTRRESTSession

__all__ = [
    "AuthMixin",
    "AuthenticatedMSTRRESTSession",
    "MSTRBaseSession",
    "MSTRRESTSession",
    "MSTRSessionProtocol",
    "ProjectsMixin",
    "SessionsMixin",
]
