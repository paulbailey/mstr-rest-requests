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

"""Deprecated requests-based sessions from mstr-rest-requests 1.x.

These classes behave exactly as :mod:`mstr.requests` did in 1.x: they
subclass :class:`requests.Session` and return :class:`requests.Response`
objects.  They need the ``requests`` extra
(``pip install mstr-rest-requests[requests]``), emit a
:class:`DeprecationWarning` when created, and will be removed in 3.0.

To keep 1.x behaviour while you migrate, change::

    from mstr.requests import AuthenticatedMSTRRESTSession

to::

    from mstr.requests.compat import AuthenticatedMSTRRESTSession
"""

try:
    from .rest.authenticated_session import AuthenticatedMSTRRESTSession
    from .rest.base import MSTRBaseSession
    from .rest.protocols import MSTRSessionProtocol
    from .rest.session import MSTRRESTSession
except ImportError as e:  # pragma: no cover - exercised in an isolated test
    raise ImportError(
        "mstr.requests.compat needs the 'requests' extra: "
        "pip install mstr-rest-requests[requests]"
    ) from e

from .rest.core import Credential

__all__ = [
    "AuthenticatedMSTRRESTSession",
    "Credential",
    "MSTRBaseSession",
    "MSTRRESTSession",
    "MSTRSessionProtocol",
]
