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

The two main entry points are:

* :class:`MSTRRESTSession` -- manual session lifecycle (login / logout).
* :class:`AuthenticatedMSTRRESTSession` -- context-managed auto login/logout.

The :data:`Credential` type alias is re-exported here so consumers can
type-hint their own callable credential providers.

Async counterparts (:class:`AsyncMSTRRESTSession`,
:class:`AsyncAuthenticatedMSTRRESTSession`) are also importable from here
when the ``async`` extra is installed; they are loaded on first access so
that ``httpx`` is only needed by code that uses them.
"""

import importlib
from typing import TYPE_CHECKING, Any

from .rest.authenticated_session import AuthenticatedMSTRRESTSession, Credential
from .rest.protocols import MSTRSessionProtocol
from .rest.session import MSTRRESTSession

if TYPE_CHECKING:
    from .rest.aio import (
        AsyncAuthenticatedMSTRRESTSession,
        AsyncCredential,
        AsyncMSTRSessionProtocol,
        AsyncMSTRRESTSession,
    )

_ASYNC_NAMES = {
    "AsyncAuthenticatedMSTRRESTSession",
    "AsyncCredential",
    "AsyncMSTRRESTSession",
    "AsyncMSTRSessionProtocol",
}


def __getattr__(name: str) -> Any:
    if name in _ASYNC_NAMES:
        try:
            aio = importlib.import_module(".rest.aio", __name__)
        except ImportError as e:
            raise ImportError(
                f"{name} requires the 'async' extra: "
                "pip install mstr-rest-requests[async]"
            ) from e
        return getattr(aio, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# The async names are deliberately left out of __all__ so that
# ``from mstr.requests import *`` works without the ``async`` extra.
__all__ = [
    "AuthenticatedMSTRRESTSession",
    "Credential",
    "MSTRRESTSession",
    "MSTRSessionProtocol",
]
