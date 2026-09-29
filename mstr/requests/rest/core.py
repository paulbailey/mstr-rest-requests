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

"""Transport-independent MicroStrategy REST API logic.

Everything here is pure: no function performs I/O or depends on a particular
HTTP library.  The session classes call these helpers so that the rules for
headers, error translation and request payloads live in one place.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Protocol, TypeAlias

from mstr.requests.rest import exceptions

MSTR_AUTH_TOKEN = "X-MSTR-AuthToken"
MSTR_PROJECT_ID_HEADER = "X-MSTR-ProjectID"
MSTR_HEADER_PREFIX = "X-MSTR"

Credential: TypeAlias = str | Callable[[], str] | None
"""A credential value: either a plain string or a zero-argument callable that
returns a string.  Callables are resolved lazily when the session's context
manager is entered, making it easy to integrate secrets managers or other
deferred-lookup strategies."""


def resolve_credential(value: Credential) -> str | None:
    """Resolve a :data:`~mstr.requests.Credential` to its string value.

    If *value* is callable it is invoked and the result returned; otherwise
    *value* is returned as-is.
    """
    if callable(value):
        return value()
    return value


_ERROR_CODES: dict[str, type[exceptions.MSTRException]] = {
    "ERR003": exceptions.LoginFailureException,
    "ERR002": exceptions.IServerException,
    "ERR0013": exceptions.IServerException,
    "ERR004": exceptions.ResourceNotFoundException,
    "ERR005": exceptions.InvalidRequestException,
    "ERR006": exceptions.InvalidRequestException,
    "ERR007": exceptions.InvalidRequestException,
    "ERR009": exceptions.SessionException,
    "ERR0014": exceptions.InsufficientPrivilegesException,
    "ERR0017": exceptions.InsufficientPrivilegesException,
    "ERR0015": exceptions.ObjectAlreadyExistsException,
}


class ErrorResponse(Protocol):
    """The parts of an HTTP response needed to translate an error."""

    @property
    def headers(self) -> Mapping[str, str]: ...

    @property
    def text(self) -> str: ...

    def json(self) -> Any: ...


def warn_on_double_slash(url: str) -> None:
    """Warn if *url* contains a ``//`` beyond the scheme separator."""
    if url.count("//") > 1:
        warnings.warn(
            f"Your fully composed request ({url}) contains a `//` in the path, which is probably an error."
        )


def build_request_headers(
    headers: Mapping[str, str] | None,
    session_headers: Mapping[str, str],
    include_auth: bool = True,
    project_id: str | None = None,
) -> dict[str, str]:
    """Return per-request headers with MicroStrategy headers added.

    The caller's *headers* mapping is copied, never modified.

    Args:
        headers: Headers supplied for this request, if any.
        session_headers: The session's persistent headers, used to look up
            the current auth token.
        include_auth: Add ``X-MSTR-AuthToken`` when the session holds one.
        project_id: If given, sent as the ``X-MSTR-ProjectID`` header.
    """
    result = dict(headers) if headers else {}
    if include_auth and MSTR_AUTH_TOKEN in session_headers:
        result[MSTR_AUTH_TOKEN] = session_headers[MSTR_AUTH_TOKEN]
    if project_id is not None:
        result[MSTR_PROJECT_ID_HEADER] = project_id
    return result


def mstr_response_headers(
    response_headers: Iterable[tuple[str, str]],
) -> dict[str, str]:
    """Return the ``X-MSTR*`` headers from a successful response's header items."""
    return {
        key: value
        for key, value in response_headers
        if key.upper().startswith(MSTR_HEADER_PREFIX)
    }


def is_json_content_type(headers: Mapping[str, str]) -> bool:
    """Return ``True`` if *headers* declare a JSON body.

    The lookup is case-insensitive and ignores media-type parameters such as
    ``charset``.  A missing ``Content-Type`` header returns ``False``.
    """
    for key, value in headers.items():
        if key.lower() == "content-type":
            return value.split(";", 1)[0].strip().lower() == "application/json"
    return False


def exception_for_payload(payload: Mapping[str, Any]) -> exceptions.MSTRException:
    """Return the exception matching a MicroStrategy JSON error *payload*."""
    try:
        code = payload["code"]
    except KeyError:
        return exceptions.MSTRUnknownException(**payload)
    exception_class = _ERROR_CODES.get(code, exceptions.MSTRException)
    return exception_class(**payload)


def raise_for_mstr_error(response: ErrorResponse) -> None:
    """Raise the matching MicroStrategy exception for a failed *response*.

    Call this only for responses with an unsuccessful status.  Responses
    without a JSON body are left for the caller to handle.

    Raises:
        MSTRException: Or a subclass, chosen by the payload's ``code``.
    """
    if not is_json_content_type(response.headers):
        return
    try:
        payload = response.json()
    except ValueError:
        raise exceptions.MSTRException(
            "Couldn't parse response: {}".format(response.text)
        )
    raise exception_for_payload(payload)


def login_payload(
    username: str | None = None,
    password: str | None = None,
    api_key: str | None = None,
    application_type: int = 8,
) -> dict[str, Any]:
    """Return the ``POST /auth/login`` body for the given credentials.

    The *login mode* is inferred from which arguments are supplied:

    * ``username`` **and** ``password`` -- standard auth (mode 1).
    * ``api_key`` -- trusted / API-key auth (mode 4096).
    * ``username`` only -- trusted / API-key auth (mode 4096).
    * Neither -- anonymous auth (mode 8).
    """
    if username is not None and password is not None:
        return {
            "username": username,
            "password": password,
            "loginMode": 1,
            "applicationType": application_type,
        }
    if api_key is not None:
        return {
            "username": api_key,
            "loginMode": 4096,
            "applicationType": application_type,
        }
    if username is not None:
        return {
            "username": username,
            "loginMode": 4096,
            "applicationType": application_type,
        }
    return {
        "loginMode": 8,
        "applicationType": application_type,
    }


def delegate_payload(identity_token: str) -> dict[str, Any]:
    """Return the ``POST /auth/delegate`` body for *identity_token*."""
    return {"loginMode": -1, "identityToken": identity_token}


def project_lookups(
    projects: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, str], dict[str, str]]:
    """Return ``(projects_by_name, projects_by_id)`` for a ``GET /projects`` result."""
    by_name: dict[str, str] = {}
    by_id: dict[str, str] = {}
    for project in projects:
        by_name[project["name"]] = project["id"]
        by_id[project["id"]] = project["name"]
    return by_name, by_id
