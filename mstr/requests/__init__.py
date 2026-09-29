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

"""Public API for mstr-rest-requests.

The main entry points are built on `httpx <https://www.python-httpx.org/>`_:

* :class:`MSTRRESTSession` -- manual session lifecycle (login / logout).
* :class:`AuthenticatedMSTRRESTSession` -- context-managed auto login/logout.
* :class:`AsyncMSTRRESTSession` and :class:`AsyncAuthenticatedMSTRRESTSession`
  -- their async counterparts.

The :data:`Credential` and :data:`AsyncCredential` type aliases are
re-exported here so consumers can type-hint their own credential providers.

The requests-based sessions from 1.x are deprecated and live in
:mod:`mstr.requests.compat`, which needs the ``requests`` extra.
"""

from .rest.aio import (
    AsyncAuthenticatedMSTRRESTSession,
    AsyncCredential,
    AsyncMSTRRESTSession,
    AsyncMSTRSessionProtocol,
)
from .rest.core import Credential
from .rest.httpx_sync import (
    AuthenticatedMSTRRESTSession,
    MSTRRESTSession,
    MSTRSessionProtocol,
)

__all__ = [
    "AsyncAuthenticatedMSTRRESTSession",
    "AsyncCredential",
    "AsyncMSTRRESTSession",
    "AsyncMSTRSessionProtocol",
    "AuthenticatedMSTRRESTSession",
    "Credential",
    "MSTRRESTSession",
    "MSTRSessionProtocol",
]
