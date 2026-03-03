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
"""

from .rest.authenticated_session import AuthenticatedMSTRRESTSession, Credential
from .rest.session import MSTRRESTSession

__all__ = ["AuthenticatedMSTRRESTSession", "Credential", "MSTRRESTSession"]
