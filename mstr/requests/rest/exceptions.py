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

from typing import Any

from .errors import iserver_error_codes


class MSTRException(Exception):
    """Base exception for all MicroStrategy REST API errors.

    Attributes:
        code: The MicroStrategy error code (e.g. ``ERR001``), or ``"N/A"``.
        message: Human-readable error description.
        iserver_code: Optional I-Server error code, when present in the
            API response.
        iserver_message: Looked-up description for *iserver_code*.
        status_code: The HTTP status of the response that caused the error,
            or ``None`` if the error did not come from a response.
        response: That response (:class:`httpx.Response` or
            :class:`requests.Response`), or ``None``.
    """

    status_code: int | None = None
    response: Any = None

    def __init__(self, message: str | None = None, *args, **kwargs):
        self.code = kwargs.get("code", "N/A")
        msg = message if message is not None else kwargs.get("message", "Unknown error")
        msg = str(msg)
        self.message = (
            f"{self.code}: {msg}" if msg.endswith(".") else f"{self.code}: {msg}."
        )
        self.iserver_code = kwargs.get("iServerCode", None)
        if self.iserver_code:
            self.iserver_message = iserver_error_codes.get(self.iserver_code)
            self.message += (
                f"  [I-Server error code {self.iserver_message} ({self.iserver_code})]"
            )
        super().__init__(self.message, *args)


class MSTRUnknownException(MSTRException):
    """Raised when the error response lacks a recognised ``code`` field."""


class MSTRHTTPError(MSTRException):
    """Raised for an error response without a MicroStrategy JSON error body.

    For example a proxy's HTML error page, or a ``502`` with no body.  Only
    raised by sessions created with ``raise_on_http_error=True``; otherwise
    such responses are returned as they are.
    """


class LoginFailureException(MSTRException):
    """Raised when authentication fails (``ERR003``)."""


class MissingCredentialException(LoginFailureException):
    """Raised before logging in when a supplied credential resolves to ``None``.

    For example, a ``password`` callable that returns ``None`` because an
    environment variable is unset.
    """


class IServerException(MSTRException):
    """Raised on Intelligence Server errors (``ERR002``, ``ERR0013``)."""


class ResourceNotFoundException(MSTRException):
    """Raised when a requested resource does not exist (``ERR004``)."""


class InvalidRequestException(MSTRException):
    """Raised on invalid input or missing required fields (``ERR005``, ``ERR006``, ``ERR007``)."""


class SessionException(MSTRException):
    """Raised when the session is invalid or has timed out (``ERR009``)."""


class InsufficientPrivilegesException(MSTRException):
    """Raised when the user lacks required privileges or permissions (``ERR0014``, ``ERR0017``)."""


class ObjectAlreadyExistsException(MSTRException):
    """Raised when attempting to create an object that already exists (``ERR0015``)."""


class ExecutionCancelledException(MSTRException):
    """Raised when a report or cube execution is cancelled."""
