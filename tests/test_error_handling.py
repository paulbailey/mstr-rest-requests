"""Error handling on logout, context-manager exit and non-JSON error
responses, for the httpx, async and requests-based sessions; no network."""

import json
import logging
import warnings
from pathlib import Path

import httpx
import pytest
import requests
from requests.adapters import BaseAdapter

import mstr
from mstr.requests import AuthenticatedMSTRRESTSession, MSTRRESTSession
from mstr.requests.compat import (
    AuthenticatedMSTRRESTSession as CompatAuthenticatedMSTRRESTSession,
    MSTRRESTSession as CompatMSTRRESTSession,
)
from mstr.requests.rest import core, exceptions
from mstr.requests.rest.aio import (
    AsyncAuthenticatedMSTRRESTSession,
    AsyncMSTRRESTSession,
)

BASE_URL = "https://mstr.example.com/api/"
EXPIRED = (
    401,
    {"Content-Type": "application/json"},
    json.dumps({"code": "ERR009", "message": "expired"}).encode(),
)
PROXY_ERROR = (502, {"Content-Type": "text/html"}, b"<h1>Bad gateway</h1>")


@pytest.fixture
def anyio_backend():
    return "asyncio"


class Server:
    """Logs in, then answers every later request with ``self.error`` if set."""

    def __init__(self):
        self.error = None
        self.logout_error = None

    def respond(self, url):
        if url.endswith("/auth/login"):
            return 204, {core.MSTR_AUTH_TOKEN: "token-1"}, b""
        if url.endswith("/auth/logout") and self.logout_error:
            return self.logout_error
        if self.error:
            return self.error
        if url.endswith("/auth/logout"):
            return 204, {}, b""
        return 200, {"Content-Type": "application/json"}, b"{}"

    def __call__(self, request):
        status, headers, body = self.respond(str(request.url))
        return httpx.Response(status, headers=headers, content=body)


class Adapter(BaseAdapter):
    def __init__(self, server):
        super().__init__()
        self.server = server

    def send(self, request, **kwargs):
        status, headers, body = self.server.respond(request.url)
        response = requests.Response()
        response.status_code = status
        response.headers.update(headers)
        response.url = request.url
        response.request = request
        response._content = body
        return response

    def close(self):
        pass


def httpx_auth(server, **kwargs):
    return AuthenticatedMSTRRESTSession(
        BASE_URL, transport=httpx.MockTransport(server), **kwargs
    )


def compat_auth(server, **kwargs):
    session = CompatAuthenticatedMSTRRESTSession(BASE_URL, **kwargs)
    session.mount("https://", Adapter(server))
    return session


def httpx_plain(server, **kwargs):
    return MSTRRESTSession(BASE_URL, transport=httpx.MockTransport(server), **kwargs)


def compat_plain(server, raise_on_http_error=False):
    session = CompatMSTRRESTSession(base_url=BASE_URL)
    session.raise_on_http_error = raise_on_http_error
    session.mount("https://", Adapter(server))
    return session


@pytest.fixture(params=["httpx", "requests"])
def make_auth(request):
    return httpx_auth if request.param == "httpx" else compat_auth


@pytest.fixture(params=["httpx", "requests"])
def make_plain(request):
    return httpx_plain if request.param == "httpx" else compat_plain


# ---------------------------------------------------------------------------
# B2: logout errors on exit
# ---------------------------------------------------------------------------


def test_exit_keeps_original_exception_when_session_expired(make_auth):
    server = Server()
    with pytest.raises(ValueError, match="original"):
        with make_auth(server, username="u", password="p"):
            server.error = EXPIRED
            raise ValueError("original")


def test_exit_keeps_original_exception_when_logout_fails(make_auth, caplog):
    server = Server()
    with caplog.at_level(logging.WARNING, logger="mstr.requests"):
        with pytest.raises(ValueError, match="original"):
            with make_auth(server, username="u", password="p"):
                server.logout_error = (500, {}, b"")
                raise ValueError("original")
    assert "Logout failed" in caplog.text


def test_exit_ignores_expired_session_without_exception(make_auth):
    server = Server()
    with make_auth(server, username="u", password="p") as session:
        server.logout_error = EXPIRED
    assert not session.has_session()


def test_exit_raises_logout_error_without_exception(make_auth):
    server = Server()
    with pytest.raises((httpx.HTTPStatusError, requests.HTTPError)):
        with make_auth(server, username="u", password="p"):
            server.logout_error = (500, {}, b"")


@pytest.mark.anyio
async def test_async_exit_keeps_original_exception():
    server = Server()
    session = AsyncAuthenticatedMSTRRESTSession(
        BASE_URL, transport=httpx.MockTransport(server), username="u", password="p"
    )
    with pytest.raises(ValueError, match="original"):
        async with session:
            server.error = EXPIRED
            raise ValueError("original")


@pytest.mark.anyio
async def test_async_exit_ignores_expired_session():
    server = Server()
    session = AsyncAuthenticatedMSTRRESTSession(
        BASE_URL, transport=httpx.MockTransport(server), username="u", password="p"
    )
    async with session:
        server.logout_error = EXPIRED
    assert not session.has_session()


@pytest.mark.anyio
async def test_async_exit_logs_logout_failure_during_exception(caplog):
    server = Server()
    session = AsyncAuthenticatedMSTRRESTSession(
        BASE_URL, transport=httpx.MockTransport(server), username="u", password="p"
    )
    with caplog.at_level(logging.WARNING, logger="mstr.requests"):
        with pytest.raises(ValueError, match="original"):
            async with session:
                server.logout_error = (500, {}, b"")
                raise ValueError("original")
    assert "Logout failed" in caplog.text


@pytest.mark.anyio
async def test_async_exit_raises_logout_error_without_exception():
    server = Server()
    session = AsyncAuthenticatedMSTRRESTSession(
        BASE_URL, transport=httpx.MockTransport(server), username="u", password="p"
    )
    with pytest.raises(httpx.HTTPStatusError):
        async with session:
            server.logout_error = (500, {}, b"")


# ---------------------------------------------------------------------------
# B4: failed logout
# ---------------------------------------------------------------------------


def test_logout_error_status_raises_and_keeps_token(make_plain):
    server = Server()
    session = make_plain(server)
    session.login()
    server.logout_error = (500, {}, b"")
    with pytest.raises((httpx.HTTPStatusError, requests.HTTPError)):
        session.logout()
    assert session.has_session()


# ---------------------------------------------------------------------------
# B3: non-JSON error responses
# ---------------------------------------------------------------------------


def test_non_json_error_returned_by_default(make_plain):
    server = Server()
    server.error = PROXY_ERROR
    response = make_plain(server).get("projects")
    assert response.status_code == 502


def test_non_json_error_raises_when_opted_in(make_plain):
    server = Server()
    server.error = PROXY_ERROR
    session = make_plain(server, raise_on_http_error=True)
    with pytest.raises(exceptions.MSTRHTTPError, match="HTTP 502") as info:
        session.get("projects")
    assert info.value.status_code == 502
    assert info.value.response.status_code == 502


def test_authenticated_session_passes_raise_on_http_error():
    server = Server()
    with httpx_auth(
        server, username="u", password="p", raise_on_http_error=True
    ) as session:
        server.error = PROXY_ERROR
        with pytest.raises(exceptions.MSTRHTTPError):
            session.get("projects")
        server.error = None


@pytest.mark.anyio
async def test_async_non_json_error_raises_when_opted_in():
    server = Server()
    server.error = PROXY_ERROR
    async with AsyncMSTRRESTSession(
        BASE_URL, transport=httpx.MockTransport(server), raise_on_http_error=True
    ) as session:
        with pytest.raises(exceptions.MSTRHTTPError):
            await session.get("projects")


def test_json_error_carries_status_and_response(make_plain):
    server = Server()
    server.error = EXPIRED
    with pytest.raises(exceptions.SessionException) as info:
        make_plain(server).get("projects")
    assert info.value.status_code == 401
    assert info.value.response is not None


# ---------------------------------------------------------------------------
# B5: error translation edge cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("payload", [["a", "b"], "just a string", 42])
def test_non_object_json_error_payload(payload):
    error = core.exception_for_payload(payload)
    assert isinstance(error, exceptions.MSTRUnknownException)
    assert str(payload) in error.message


def test_message_ending_in_full_stop_is_not_doubled():
    assert exceptions.MSTRException(code="ERR001", message="Bad.").message == (
        "ERR001: Bad."
    )
    assert exceptions.MSTRException(code="ERR001", message="Bad").message == (
        "ERR001: Bad."
    )


def test_exception_without_response_has_no_status():
    error = exceptions.MSTRException("x")
    assert error.status_code is None
    assert error.response is None


# ---------------------------------------------------------------------------
# B6: double-slash warning
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "projects",
        "https://env.example.com/api/projects",
        "auth/login?redirect=https://other.example.org/x",
        "search#https://x",
    ],
)
def test_no_double_slash_warning(url):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        core.warn_on_double_slash(url)


@pytest.mark.parametrize(
    "url", ["projects//x", "https://env.example.com/api//projects"]
)
def test_double_slash_warning(url):
    with pytest.warns(UserWarning, match="//"):
        core.warn_on_double_slash(url)


# ---------------------------------------------------------------------------
# Packaging
# ---------------------------------------------------------------------------


def test_package_is_marked_typed():
    assert (Path(mstr.__file__).parent / "py.typed").is_file()
