"""The auth token stays on the base URL's origin, and restored cookies stay on
its host, for the httpx, async and requests-based sessions; no network."""

import httpx
import pytest
import requests
from requests.adapters import BaseAdapter

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
TOKEN = core.MSTR_AUTH_TOKEN
SAVED = {
    "base_url": BASE_URL,
    "cookies": {"JSESSIONID": "abc"},
    "headers": {TOKEN: "token-1"},
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def route(method, url):
    """Return ``(status, headers)`` for a request to the fake servers."""
    if url.endswith("/api/redirect-away"):
        return 302, {"Location": "https://evil.example.net/steal"}
    if url.endswith("/api/redirect-home"):
        return 302, {"Location": "https://mstr.example.com/api/landed"}
    if url.endswith("/api/redirect-port"):
        return 302, {"Location": "https://mstr.example.com:8443/api/landed"}
    if url.endswith("/api/redirect-http"):
        return 302, {"Location": "http://mstr.example.com/api/landed"}
    if url.endswith("/auth/logout"):
        return 204, {}
    return 200, {}


class Recorder:
    """An httpx MockTransport handler that records each request."""

    def __init__(self):
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        status, headers = route(request.method, str(request.url))
        return httpx.Response(status, headers=headers)

    def sent(self):
        """Return ``{url: token or None}`` for every request sent."""
        return {str(r.url): r.headers.get(TOKEN) for r in self.requests}


class RequestsRecorder(BaseAdapter):
    """A requests transport adapter that records each request."""

    def __init__(self):
        super().__init__()
        self.requests = []

    def send(self, request, **kwargs):
        self.requests.append(request)
        status, headers = route(request.method, request.url)
        response = requests.Response()
        response.status_code = status
        response.headers.update(headers)
        response.url = request.url
        response.request = request
        response._content = b""
        return response

    def close(self):
        pass

    def sent(self):
        return {r.url: r.headers.get(TOKEN) for r in self.requests}


def httpx_session(base_url=BASE_URL):
    recorder = Recorder()
    session = MSTRRESTSession(base_url, transport=httpx.MockTransport(recorder))
    session.headers[TOKEN] = "token-1"
    return session, recorder


def compat_session(base_url=BASE_URL):
    recorder = RequestsRecorder()
    session = CompatMSTRRESTSession(base_url=base_url or None)
    session.mount("https://", recorder)
    session.mount("http://", recorder)
    session.headers[TOKEN] = "token-1"
    return session, recorder


@pytest.fixture(params=["httpx", "requests"])
def make_sync(request):
    return httpx_session if request.param == "httpx" else compat_session


# ---------------------------------------------------------------------------
# Sync sessions (httpx and the deprecated requests classes)
# ---------------------------------------------------------------------------


def test_token_sent_to_base_url(make_sync):
    session, recorder = make_sync()
    session.get("projects")
    assert recorder.sent() == {BASE_URL + "projects": "token-1"}


def test_token_not_sent_to_absolute_url_on_other_host(make_sync):
    session, recorder = make_sync()
    session.get("https://other.example.org/y", headers={"X-MSTR-ProjectID": "P1"})
    request = recorder.requests[-1]
    assert request.headers.get(TOKEN) is None
    assert request.headers.get("X-MSTR-ProjectID") is None


def test_token_sent_to_absolute_url_on_same_origin(make_sync):
    session, recorder = make_sync()
    session.get("https://mstr.example.com:443/api/projects")
    assert recorder.requests[-1].headers.get(TOKEN) == "token-1"


@pytest.mark.parametrize(
    "path", ["redirect-away", "redirect-port", "redirect-http"]
)
def test_token_stripped_on_cross_origin_redirect(make_sync, path):
    session, recorder = make_sync()
    session.get(path)
    first, second = recorder.requests
    assert first.headers.get(TOKEN) == "token-1"
    assert second.headers.get(TOKEN) is None


def test_token_kept_on_same_origin_redirect(make_sync):
    session, recorder = make_sync()
    session.get("redirect-home")
    assert [r.headers.get(TOKEN) for r in recorder.requests] == [
        "token-1",
        "token-1",
    ]


def test_include_auth_false_omits_token(make_sync):
    session, recorder = make_sync()
    session.get("projects", include_auth=False)
    assert recorder.requests[-1].headers.get(TOKEN) is None
    # The token is still held for later requests.
    assert session.has_session()
    session.get("projects")
    assert recorder.requests[-1].headers.get(TOKEN) == "token-1"


def test_include_auth_false_omits_token_after_redirect(make_sync):
    session, recorder = make_sync()
    session.get("redirect-home", include_auth=False)
    assert [r.headers.get(TOKEN) for r in recorder.requests] == [None, None]


def test_without_base_url_token_goes_to_absolute_url_but_not_redirects(make_sync):
    session, recorder = make_sync(base_url="")
    session.get(BASE_URL + "projects")
    session.get(BASE_URL + "redirect-away")
    assert [r.headers.get(TOKEN) for r in recorder.requests] == [
        "token-1",
        "token-1",
        None,
    ]


def test_restored_cookies_only_go_to_base_url_host(make_sync):
    session, recorder = make_sync()
    session.update_from_json(SAVED)
    session.get("projects")
    session.get("https://other.example.org/y")
    first, second = recorder.requests
    assert first.headers.get("Cookie") == "JSESSIONID=abc"
    assert second.headers.get("Cookie") is None


def test_restored_cookies_sent_to_localhost(make_sync):
    session, recorder = make_sync(base_url="http://localhost:8080/api/")
    session.update_from_json({**SAVED, "base_url": "http://localhost:8080/api/"})
    session.get("projects")
    assert recorder.requests[-1].headers.get("Cookie") == "JSESSIONID=abc"


def test_httpx_client_used_directly_is_scoped_to_base_url():
    session, recorder = httpx_session()
    session.client.get("projects")
    session.client.get("https://other.example.org/y")
    assert [r.headers.get(TOKEN) for r in recorder.requests] == ["token-1", None]


def test_httpx_include_auth_false_keeps_caller_extensions():
    session, recorder = httpx_session()
    session.get("projects", include_auth=False, extensions={"custom": 1})
    assert recorder.requests[-1].extensions["custom"] == 1


# ---------------------------------------------------------------------------
# Async session
# ---------------------------------------------------------------------------


def async_session(base_url=BASE_URL):
    recorder = Recorder()
    session = AsyncMSTRRESTSession(base_url, transport=httpx.MockTransport(recorder))
    session.headers[TOKEN] = "token-1"
    return session, recorder


@pytest.mark.anyio
async def test_async_token_stripped_on_cross_origin_redirect_and_absolute_url():
    session, recorder = async_session()
    async with session:
        await session.get("redirect-away")
        await session.get("https://other.example.org/y")
        await session.get("redirect-home")
    assert [r.headers.get(TOKEN) for r in recorder.requests] == [
        "token-1",
        None,
        None,
        "token-1",
        "token-1",
    ]


@pytest.mark.anyio
async def test_async_include_auth_false_omits_token():
    session, recorder = async_session()
    async with session:
        await session.get("projects", include_auth=False)
        await session.get("projects")
    assert [r.headers.get(TOKEN) for r in recorder.requests] == [None, "token-1"]


@pytest.mark.anyio
async def test_async_restored_cookies_only_go_to_base_url_host():
    session, recorder = async_session()
    async with session:
        session.update_from_json(SAVED)
        await session.get("projects")
        await session.get("https://other.example.org/y")
    first, second = recorder.requests
    assert first.headers.get("Cookie") == "JSESSIONID=abc"
    assert second.headers.get("Cookie") is None


# ---------------------------------------------------------------------------
# Credentials that resolve to None
# ---------------------------------------------------------------------------

UNRESOLVED = [
    ({"username": "dave", "password": lambda: None}, "password"),
    ({"username": lambda: None, "password": "pw"}, "username"),
    ({"api_key": lambda: None}, "api_key"),
    ({"identity_token": lambda: None}, "identity_token"),
]


@pytest.mark.parametrize("kwargs,name", UNRESOLVED)
def test_unresolved_credential_raises_before_login(kwargs, name):
    recorder = Recorder()
    session = AuthenticatedMSTRRESTSession(
        BASE_URL, transport=httpx.MockTransport(recorder), **kwargs
    )
    with pytest.raises(exceptions.MissingCredentialException, match=name):
        with session:
            pass
    assert recorder.requests == []


@pytest.mark.parametrize("kwargs,name", UNRESOLVED)
def test_compat_unresolved_credential_raises_before_login(kwargs, name):
    session = CompatAuthenticatedMSTRRESTSession(BASE_URL, **kwargs)
    recorder = RequestsRecorder()
    session.mount("https://", recorder)
    with pytest.raises(exceptions.MissingCredentialException, match=name):
        with session:
            pass
    assert recorder.requests == []


@pytest.mark.anyio
@pytest.mark.parametrize("kwargs,name", UNRESOLVED)
async def test_async_unresolved_credential_raises_before_login(kwargs, name):
    recorder = Recorder()
    session = AsyncAuthenticatedMSTRRESTSession(
        BASE_URL, transport=httpx.MockTransport(recorder), **kwargs
    )
    with pytest.raises(exceptions.MissingCredentialException, match=name):
        async with session:
            pass
    assert recorder.requests == []


def test_missing_credential_is_a_login_failure():
    assert issubclass(
        exceptions.MissingCredentialException, exceptions.LoginFailureException
    )


def test_username_without_password_is_still_trusted_login():
    assert core.login_payload(username="dave")["loginMode"] == 4096
