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

import ipaddress
import warnings
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Protocol, TypeAlias
from urllib.parse import urlsplit

from mstr.requests.rest import exceptions

MSTR_AUTH_TOKEN = "X-MSTR-AuthToken"
MSTR_PROJECT_ID_HEADER = "X-MSTR-ProjectID"
MSTR_HEADER_PREFIX = "X-MSTR"
MSTR_IDENTITY_TOKEN = "X-MSTR-IdentityToken"

RETRY_STATUSES = frozenset({502, 503, 504})
"""Response statuses that a session with ``retries`` set will retry."""

IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})
"""Methods that are safe to send again after the server may have seen them."""

MAX_RETRY_DELAY = 60.0
"""Upper bound, in seconds, on the wait between two attempts."""

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
    def status_code(self) -> int: ...

    @property
    def headers(self) -> Mapping[str, str]: ...

    @property
    def text(self) -> str: ...

    def json(self) -> Any: ...


Origin: TypeAlias = tuple[str, str, int | None]
"""A URL's ``(scheme, host, port)``, with the default port given as ``None``."""

_DEFAULT_PORTS = {"http": 80, "https": 443}


def url_origin(url: str) -> Origin | None:
    """Return the origin of *url*, or ``None`` if *url* has no host.

    Scheme and host are lower-cased, and the scheme's default port is
    returned as ``None`` so that ``https://h/`` and ``https://h:443/`` match.
    """
    parts = urlsplit(url)
    if not parts.hostname:
        return None
    scheme = parts.scheme.lower()
    port = parts.port
    if port == _DEFAULT_PORTS.get(scheme):
        port = None
    return (scheme, parts.hostname.lower(), port)


def auth_scope_origin(base_url: str, url: str) -> Origin | None:
    """Return the origin that the auth token may be sent to.

    This is the origin of *base_url*.  A session without a base URL has no
    fixed scope, so the origin of the request *url* itself is used.
    """
    return url_origin(base_url) or url_origin(url)


def mstr_header_names(headers: Iterable[str]) -> list[str]:
    """Return the names in *headers* that start with ``X-MSTR`` (any case)."""
    prefix = MSTR_HEADER_PREFIX.lower()
    return [name for name in headers if name.lower().startswith(prefix)]


def cookie_domain(base_url: str) -> str:
    """Return the cookie domain to use for cookies restored for *base_url*.

    Restored cookies carry no domain of their own, so without one they would
    be sent to every host.  :mod:`http.cookiejar` treats a dotless host such
    as ``localhost`` as ``localhost.local``, so that suffix is added.
    Returns ``""`` when *base_url* has no host.
    """
    host = urlsplit(base_url).hostname or ""
    if host and "." not in host:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            return host + ".local"
    return host


def raise_for_unresolved_credentials(**credentials: tuple[Any, Any]) -> None:
    """Raise if a credential was supplied but resolved to ``None``.

    Each keyword maps a credential name to ``(supplied, resolved)``.  A
    callable that returns ``None`` (an unset environment variable, a missing
    secret) would otherwise silently change the login mode, for example
    turning a username and password into a trusted login.

    Raises:
        MissingCredentialException: Naming the unresolved credentials.
    """
    missing = [
        name
        for name, (supplied, resolved) in credentials.items()
        if supplied is not None and resolved is None
    ]
    if missing:
        raise exceptions.MissingCredentialException(
            "{} resolved to None".format(", ".join(missing))
        )


def warn_on_double_slash(url: str) -> None:
    """Warn if the path of *url* contains ``//``.

    The query string and fragment are ignored, so a URL passed as a query
    parameter does not warn.
    """
    if "//" in urlsplit(url).path:
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
    """Return the ``X-MSTR*`` headers from a successful response's header items.

    ``X-MSTR-IdentityToken`` is left out: it is returned to the caller by
    ``create_identity_token()``, and must not become a session-wide header.
    """
    identity_token = MSTR_IDENTITY_TOKEN.upper()
    return {
        key: value
        for key, value in response_headers
        if key.upper().startswith(MSTR_HEADER_PREFIX)
        and key.upper() != identity_token
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


def exception_for_payload(payload: Any) -> exceptions.MSTRException:
    """Return the exception matching a MicroStrategy JSON error *payload*.

    A payload that is not a JSON object (a list or a string, say) gives an
    :class:`~mstr.requests.rest.exceptions.MSTRUnknownException`.
    """
    if not isinstance(payload, Mapping):
        return exceptions.MSTRUnknownException(str(payload))
    try:
        code = payload["code"]
    except KeyError:
        return exceptions.MSTRUnknownException(**payload)
    exception_class = _ERROR_CODES.get(code, exceptions.MSTRException)
    return exception_class(**payload)


def raise_for_mstr_error(
    response: ErrorResponse, raise_on_http_error: bool = False
) -> None:
    """Raise the matching MicroStrategy exception for a failed *response*.

    Call this only for responses with an unsuccessful status.  The raised
    exception carries the response and its ``status_code``.

    Args:
        response: The failed response.
        raise_on_http_error: Raise
            :class:`~mstr.requests.rest.exceptions.MSTRHTTPError` for a
            response without a JSON body.  When ``False`` (the default) such
            responses are left for the caller to handle.

    Raises:
        MSTRException: Or a subclass, chosen by the payload's ``code``.
        MSTRHTTPError: For a non-JSON body, if *raise_on_http_error* is set.
    """
    error: exceptions.MSTRException
    if not is_json_content_type(response.headers):
        if not raise_on_http_error:
            return
        error = exceptions.MSTRHTTPError(f"HTTP {response.status_code} error")
    else:
        try:
            payload = response.json()
        except ValueError:
            error = exceptions.MSTRException(
                "Couldn't parse response: {}".format(response.text)
            )
        else:
            error = exception_for_payload(payload)
    error.status_code = response.status_code
    error.response = response
    raise error


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


def is_retryable_status(method: str, status_code: int) -> bool:
    """Return ``True`` if a response with *status_code* should be retried.

    Only ``502``, ``503`` and ``504`` from an idempotent *method* are
    retried, since the server may have acted on anything else.
    """
    return status_code in RETRY_STATUSES and method.upper() in IDEMPOTENT_METHODS


def retry_delay(
    attempt: int, backoff_factor: float, retry_after: str | None = None
) -> float:
    """Return the seconds to wait before retry number *attempt* (from 1).

    The delay is ``backoff_factor * 2 ** (attempt - 1)``, or the server's
    ``Retry-After`` seconds when that is longer, capped at
    :data:`MAX_RETRY_DELAY`.  A ``Retry-After`` HTTP date is ignored.
    """
    delay = backoff_factor * float(2 ** (attempt - 1))
    if retry_after is not None:
        try:
            delay = max(delay, float(retry_after))
        except ValueError:
            pass
    return max(0.0, min(delay, MAX_RETRY_DELAY))


def redact_url(url: str) -> str:
    """Return *url* without any ``user:password@`` part, for logging."""
    parts = urlsplit(url)
    if "@" not in parts.netloc:
        return url
    return parts._replace(netloc=parts.netloc.rsplit("@", 1)[1]).geturl()


def is_session_expired(error: BaseException) -> bool:
    """Return ``True`` if *error* says the session is invalid or timed out (``ERR009``)."""
    return (
        isinstance(error, exceptions.SessionException)
        and getattr(error, "code", None) == "ERR009"
    )


def is_auth_url(url: str) -> bool:
    """Return ``True`` if *url* is an ``auth/`` endpoint (login, logout, delegate...)."""
    path = urlsplit(url).path.lstrip("/")
    return path.startswith("auth/") or "/auth/" in path


def check_project_arguments(project: str | None, project_id: str | None) -> None:
    """Raise :class:`ValueError` if both *project* and *project_id* are given."""
    if project is not None and project_id is not None:
        raise ValueError("Pass either project or project_id, not both")


def project_id_for_name(lookup: Mapping[str, str], name: str) -> str:
    """Return the ID of the project called *name* in *lookup*.

    Raises:
        ResourceNotFoundException: If there is no such project.
    """
    try:
        return lookup[name]
    except KeyError:
        raise exceptions.ResourceNotFoundException(
            f"No project named {name!r} is available to this session"
        ) from None
