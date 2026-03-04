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
from typing import TYPE_CHECKING

from requests.utils import dict_from_cookiejar, cookiejar_from_dict

from .exceptions import SessionException

if TYPE_CHECKING:
    from .protocols import MSTRSessionProtocol


class SessionPersistenceMixin:
    """Mixin that adds serialisation and deserialisation to a session.

    Allows a session (including its auth token and cookies) to be exported
    as JSON and later restored, which is useful for passing authenticated
    sessions between processes.
    """

    def dict(self: MSTRSessionProtocol) -> dict:
        """Return a dict snapshot of the session state.

        The dict contains ``base_url``, ``cookies``, and ``headers``.
        """
        return {
            "base_url": self.base_url,
            "cookies": dict_from_cookiejar(self.cookies),
            "headers": dict(self.headers),
        }

    def json(self) -> str:
        """Return a JSON string snapshot of the session state."""
        return json.dumps(self.dict())

    def update_from_json(self: MSTRSessionProtocol, data: dict | str) -> None:
        """Restore session state from a dict or JSON string.

        Args:
            data: A dict (or JSON string) previously produced by
                :meth:`dict` or :meth:`json`.

        Raises:
            SessionException: If required keys are missing from *data*.
        """
        if type(data) is dict:
            input_data = data
        elif type(data) is str:
            input_data = json.loads(data)
        else:
            input_data = dict()

        try:
            self.base_url = input_data["base_url"]
            self.cookies = cookiejar_from_dict(input_data["cookies"])
            self.headers.update(input_data["headers"])
        except KeyError as e:
            raise SessionException(e)

    @classmethod
    def from_dict(cls, session_dict: dict):
        """Create a new session instance from a dict snapshot.

        Args:
            session_dict: A dict previously produced by :meth:`dict`.

        Returns:
            A new session with state restored from *session_dict*.
        """
        session = cls(base_url=session_dict.get("base_url"))
        session.update_from_json(session_dict)
        return session
