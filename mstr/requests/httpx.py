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

"""httpx-based synchronous sessions (opt-in until 2.0).

Requires the ``httpx`` extra: ``pip install mstr-rest-requests[httpx]``.
The classes have the same names and arguments as those in
:mod:`mstr.requests`, so switching is a change of import::

    from mstr.requests.httpx import AuthenticatedMSTRRESTSession

In 2.0 these become the default classes exported by :mod:`mstr.requests`.
"""

from .rest.authenticated_session import Credential
from .rest.httpx_sync import (
    AuthenticatedMSTRRESTSession,
    MSTRRESTSession,
    MSTRSessionProtocol,
)

__all__ = [
    "AuthenticatedMSTRRESTSession",
    "Credential",
    "MSTRRESTSession",
    "MSTRSessionProtocol",
]
