# -*- coding: utf-8 -*-
# Copyright 2026 Paul Bailey
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

"""Environment variable credential provider.

Needs no extra packages::

    from mstr.requests.credentials.env import env

    with AuthenticatedMSTRRESTSession(
        base_url=env("MSTR_BASE_URL"),
        username=env("MSTR_USERNAME"),
        password=env("MSTR_PASSWORD"),
    ) as session:
        ...
"""

import os
from collections.abc import Callable

from mstr.requests.rest.exceptions import MissingCredentialException


def env(name: str, default: str | None = None) -> Callable[[], str]:
    """Return a callable that reads the environment variable *name* when invoked.

    The variable is read each time the callable is called, so a session
    that logs in again (``relogin=True``) picks up a changed value.

    Args:
        name: The environment variable to read.
        default: Returned when the variable is unset or empty.  Without a
            default, an unset or empty variable raises.

    Raises:
        MissingCredentialException: When invoked, if the variable is unset
            or empty and there is no *default*.  The message names the
            variable but never includes a value.
    """

    def _read() -> str:
        value = os.environ.get(name)
        if value:
            return value
        if default is not None:
            return default
        raise MissingCredentialException(f"Environment variable {name} is not set")

    return _read
