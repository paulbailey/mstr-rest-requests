"""Unit tests for the async httpx-based sessions (rest/aio); no network."""

import functools
import json
import threading

import httpx
import pytest

from mstr.requests.compat import MSTRRESTSession
from mstr.requests.rest import exceptions
from mstr.requests.rest.aio import (
    AsyncAuthenticatedMSTRRESTSession,
    AsyncMSTRRESTSession,
    AsyncMSTRSessionProtocol,
)
from mstr.requests.rest.base import MSTR_AUTH_TOKEN, MSTR_PROJECT_ID_HEADER

BASE_URL = "https://example.com/api/"
PROJECTS = [{"name": "Tutorial", "id": "P1"}, {"name": "Sales", "id": "P2"}]


@pytest.fixture(params=["asyncio", "trio"])
def anyio_backend(request):
    return request.param


class FakeServer:
    """A minimal MicroStrategy REST API, served through httpx.MockTransport."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.login_status = 204
        self.error: tuple[int, dict, bytes] | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if self.error is not None:
            status, headers, body = self.error
            return httpx.Response(status, headers=headers, content=body)
        if path.endswith("/auth/login") or path.endswith("/auth/delegate"):
            if self.login_status != 204:
                return httpx.Response(self.login_status, text="nope")
            return httpx.Response(
                204,
                headers={
                    MSTR_AUTH_TOKEN: "token-1",
                    "Set-Cookie": "JSESSIONID=abc; Path=/",
                },
            )
        if path.endswith("/auth/logout"):
            return httpx.Response(204)
        if path.endswith("/projects"):
            return httpx.Response(200, json=PROJECTS)
        if "/sessions" in path:
            return httpx.Response(200, json={"path": path})
        return httpx.Response(200, json={"ok": True})

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]

    def paths(self) -> list[str]:
        return [r.url.path for r in self.requests]


@pytest.fixture
def server():
    return FakeServer()


def make_session(server, cls=AsyncMSTRRESTSession, **kwargs):
    return cls(base_url=BASE_URL, transport=httpx.MockTransport(server), **kwargs)


# ---------------------------------------------------------------------------
# Base session
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_request_adds_auth_and_project_headers(server):
    async with make_session(server) as session:
        session.headers[MSTR_AUTH_TOKEN] = "tok"
        await session.get("reports", project_id="P1")
    assert server.last.url == "https://example.com/api/reports"
    assert server.last.headers[MSTR_AUTH_TOKEN] == "tok"
    assert server.last.headers[MSTR_PROJECT_ID_HEADER] == "P1"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "method", ["options", "head", "post", "put", "patch", "delete"]
)
async def test_verb_methods_send_matching_method(server, method):
    async with make_session(server) as session:
        await getattr(session, method)("thing")
    assert server.last.method == method.upper()


@pytest.mark.anyio
async def test_request_captures_x_mstr_response_headers(server):
    server.error = (200, {"X-MSTR-Something": "1", "Other": "2"}, b"")
    async with make_session(server) as session:
        await session.get("x")
        assert session.headers["X-MSTR-Something"] == "1"
        assert "Other" not in session.headers


@pytest.mark.anyio
async def test_request_translates_json_errors(server):
    body = json.dumps({"code": "ERR004", "message": "missing"}).encode()
    server.error = (404, {"Content-Type": "application/json;charset=UTF-8"}, body)
    async with make_session(server) as session:
        with pytest.raises(exceptions.ResourceNotFoundException):
            await session.get("missing")


@pytest.mark.anyio
async def test_request_returns_non_json_errors(server):
    server.error = (500, {"Content-Type": "text/html"}, b"<html/>")
    async with make_session(server) as session:
        response = await session.get("broken")
    assert response.status_code == 500


@pytest.mark.anyio
async def test_request_warns_on_double_slash(server):
    async with make_session(server) as session:
        with pytest.warns(UserWarning, match="contains a `//`"):
            await session.get("a//b//c")


@pytest.mark.anyio
async def test_defaults_match_sync_session(server):
    async with make_session(server) as session:
        assert session.client.timeout == httpx.Timeout(None)
        assert session.client.follow_redirects is True
        assert session.base_url == BASE_URL
        assert isinstance(session, AsyncMSTRSessionProtocol)


@pytest.mark.anyio
async def test_supplied_client_is_not_closed(server):
    client = httpx.AsyncClient(transport=httpx.MockTransport(server))
    async with AsyncMSTRRESTSession(base_url=BASE_URL, client=client):
        pass
    assert client.is_closed is False
    await client.aclose()


@pytest.mark.anyio
async def test_owned_client_is_closed(server):
    session = make_session(server)
    async with session:
        pass
    assert session.client.is_closed is True


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_login_and_logout(server):
    async with make_session(server) as session:
        assert session.has_session() is False
        await session.login(username="u", password="p")
        assert session.has_session() is True
        assert json.loads(server.last.content)["loginMode"] == 1
        assert session.cookies["JSESSIONID"] == "abc"

        await session.get("x")
        assert server.last.headers[MSTR_AUTH_TOKEN] == "token-1"

        await session.logout()
        assert session.has_session() is False


@pytest.mark.anyio
async def test_login_failure_raises_http_status_error(server):
    server.login_status = 401
    async with make_session(server) as session:
        with pytest.raises(httpx.HTTPStatusError):
            await session.login(username="u", password="p")


@pytest.mark.anyio
async def test_delegate(server):
    async with make_session(server) as session:
        await session.delegate("id-token")
    assert json.loads(server.last.content) == {
        "loginMode": -1,
        "identityToken": "id-token",
    }


@pytest.mark.anyio
async def test_delegate_failure_raises_http_status_error(server):
    server.login_status = 500
    async with make_session(server) as session:
        with pytest.raises(httpx.HTTPStatusError):
            await session.delegate("id-token")


@pytest.mark.anyio
async def test_logout_keeps_token_on_unexpected_status(server):
    async with make_session(server) as session:
        await session.login()
        server.error = (200, {}, b"")
        await session.logout()
        assert session.has_session() is True


# ---------------------------------------------------------------------------
# Sessions and projects
# ---------------------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(
    "method, path",
    [
        ("extend_session", "/api/sessions"),
        ("get_userinfo", "/api/sessions/userInfo"),
        ("get_session_info", "/api/sessions"),
    ],
)
async def test_session_endpoints(server, method, path):
    async with make_session(server) as session:
        await session.login()
        response = await getattr(session, method)()
    assert response.json() == {"path": path}


@pytest.mark.anyio
@pytest.mark.parametrize(
    "method", ["extend_session", "get_userinfo", "get_session_info", "get_projects"]
)
async def test_endpoints_require_a_session(server, method):
    async with make_session(server) as session:
        with pytest.raises(exceptions.SessionException):
            await getattr(session, method)()
    assert server.requests == []


@pytest.mark.anyio
async def test_load_projects_and_get_project_id(server):
    async with make_session(server) as session:
        with pytest.raises(exceptions.SessionException):
            session.get_project_id("Tutorial")
        await session.login()
        assert await session.get_projects() == PROJECTS
        await session.load_projects()
    assert session.get_project_id("Sales") == "P2"
    assert session.get_project_id("Nope") is None
    assert session.projects_by_id == {"P1": "Tutorial", "P2": "Sales"}


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_round_trip_between_sync_and_async(server):
    sync_session = MSTRRESTSession(base_url=BASE_URL)
    sync_session.headers[MSTR_AUTH_TOKEN] = "tok"
    sync_session.cookies.set("JSESSIONID", "abc")

    async_session = AsyncMSTRRESTSession.from_dict(
        sync_session.to_dict(), transport=httpx.MockTransport(server)
    )
    async with async_session:
        assert async_session.has_session() is True
        await async_session.get("x")
        assert server.last.headers[MSTR_AUTH_TOKEN] == "tok"
        assert server.last.headers["cookie"] == "JSESSIONID=abc"

        restored = MSTRRESTSession.from_dict(json.loads(async_session.json()))
    assert restored.headers[MSTR_AUTH_TOKEN] == "tok"
    assert restored.cookies["JSESSIONID"] == "abc"
    assert restored.base_url == BASE_URL


@pytest.mark.anyio
async def test_update_from_json_string_and_dict_alias(server):
    async with make_session(server) as session:
        session.update_from_json(
            json.dumps(
                {"base_url": "https://other/api/", "cookies": {}, "headers": {"A": "1"}}
            )
        )
        assert session.base_url == "https://other/api/"
        assert session.dict() == session.to_dict()
        assert session.to_dict()["headers"]["a"] == "1"


@pytest.mark.anyio
@pytest.mark.parametrize("data", [{"base_url": BASE_URL}, 42])
async def test_update_from_json_rejects_incomplete_data(server, data):
    async with make_session(server) as session:
        with pytest.raises(exceptions.SessionException):
            session.update_from_json(data)


# ---------------------------------------------------------------------------
# Authenticated session
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_authenticated_session_logs_in_and_out(server):
    session = make_session(
        server, AsyncAuthenticatedMSTRRESTSession, username="u", password="p"
    )
    async with session as s:
        assert s is session
        assert s.has_session() is True
    assert server.paths() == ["/api/auth/login", "/api/auth/logout"]
    assert session.client.is_closed is True


@pytest.mark.anyio
async def test_authenticated_session_api_key(server):
    async with make_session(
        server, AsyncAuthenticatedMSTRRESTSession, api_key="k", application_type=35
    ):
        body = json.loads(server.requests[0].content)
    assert body == {"username": "k", "loginMode": 4096, "applicationType": 35}


@pytest.mark.anyio
async def test_authenticated_session_identity_token_skips_logout(server):
    async with make_session(
        server, AsyncAuthenticatedMSTRRESTSession, identity_token="id"
    ):
        pass
    assert server.paths() == ["/api/auth/delegate"]


@pytest.mark.anyio
async def test_authenticated_session_resolves_sync_and_async_callables(server):
    threads = []

    def sync_username():
        threads.append(threading.current_thread())
        return "u"

    async def async_password():
        return "p"

    async def async_base_url():
        return BASE_URL

    session = AsyncAuthenticatedMSTRRESTSession(
        base_url=async_base_url,
        username=sync_username,
        password=async_password,
        transport=httpx.MockTransport(server),
    )
    assert session.base_url == ""
    async with session:
        body = json.loads(server.requests[0].content)
    assert body["username"] == "u" and body["password"] == "p"
    assert server.requests[0].url == "https://example.com/api/auth/login"
    assert threads[0] is not threading.main_thread()


@pytest.mark.anyio
async def test_authenticated_session_awaits_partials_and_async_call_objects(server):
    async def fetch(value):
        return value

    class Secret:
        async def __call__(self):
            return "p"

    async with make_session(
        server,
        AsyncAuthenticatedMSTRRESTSession,
        username=functools.partial(fetch, "u"),
        password=Secret(),
    ):
        body = json.loads(server.requests[0].content)
    assert body["username"] == "u" and body["password"] == "p"


@pytest.mark.anyio
async def test_authenticated_session_closes_client_on_login_failure(server):
    server.login_status = 401
    session = make_session(
        server, AsyncAuthenticatedMSTRRESTSession, username="u", password="p"
    )
    with pytest.raises(httpx.HTTPStatusError):
        async with session:
            pass  # pragma: no cover
    assert session.client.is_closed is True


# ---------------------------------------------------------------------------
# Top-level exports
# ---------------------------------------------------------------------------


def test_top_level_exports():
    import mstr.requests

    assert mstr.requests.AsyncMSTRRESTSession is AsyncMSTRRESTSession
    assert (
        mstr.requests.AsyncAuthenticatedMSTRRESTSession
        is AsyncAuthenticatedMSTRRESTSession
    )
