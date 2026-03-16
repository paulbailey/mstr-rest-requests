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

import json
from typing import TYPE_CHECKING, Any, Dict as DictType, TypeVar

from requests.utils import dict_from_cookiejar, cookiejar_from_dict

from .exceptions import SessionException

if TYPE_CHECKING:
    from .protocols import MSTRSessionProtocol

_S = TypeVar("_S", bound="MSTRSessionProtocol")
_T = TypeVar("_T", bound="SessionPersistenceMixin")


class SessionPersistenceMixin:
    """Mixin that adds serialisation and deserialisation to a session.

    Allows a session (including its auth token and cookies) to be exported
    as JSON and later restored, which is useful for passing authenticated
    sessions between processes.
    """

    def to_dict(self: _S) -> DictType[str, Any]:
        """Return a dict snapshot of the session state.

        The dict contains ``base_url``, ``cookies``, and ``headers``.
        """
        return {
            "base_url": self.base_url,
            "cookies": dict_from_cookiejar(self.cookies),
            "headers": dict(self.headers),
        }

    def dict(self: _S) -> DictType[str, Any]:
        """Alias for :meth:`to_dict`. Prefer :meth:`to_dict` for clarity."""
        return self.to_dict()

    def json(self) -> str:
        """Return a JSON string snapshot of the session state."""
        return json.dumps(self.to_dict())  # type: ignore[misc]

    def update_from_json(self: _S, data: DictType[str, Any] | str) -> None:
        """Restore session state from a dict or JSON string.

        Args:
            data: A dict (or JSON string) previously produced by
                :meth:`to_dict` or :meth:`json`.

        Raises:
            SessionException: If required keys are missing from *data*.
        """
        if type(data) is dict:
            input_data = data
        elif type(data) is str:
            input_data = json.loads(data)
        else:
            input_data = {}

        try:
            self.base_url = input_data["base_url"]
            self.cookies = cookiejar_from_dict(input_data["cookies"])
            self.headers.update(input_data["headers"])
        except KeyError as e:
            raise SessionException(str(e))

    @classmethod
    def from_dict(cls: type[_T], session_dict: DictType[str, Any]) -> _T:
        """Create a new session instance from a dict snapshot.

        Subclasses must accept ``base_url`` as their first constructor argument.

        Args:
            session_dict: A dict previously produced by :meth:`to_dict`.

        Returns:
            A new session with state restored from *session_dict*.
        """
        base_url: str = session_dict.get("base_url", "")
        session: _T = cls(base_url=base_url)  # type: ignore[call-arg]
        session.update_from_json(session_dict)  # type: ignore[misc]
        return session
