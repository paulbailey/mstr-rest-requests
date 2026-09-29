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

"""Alias for the httpx-based sessions, kept for code written against 1.3.

Since 2.0 these are the default classes exported by :mod:`mstr.requests`,
so new code should import from there.
"""

from .rest.core import Credential
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
