"""Unit tests for the synchronous httpx-based sessions (rest/httpx_sync); no network."""

import functools
import json
import warnings

import httpx
import pytest

from mstr.requests import MSTRRESTSession
from mstr.requests.rest import exceptions
from mstr.requests.httpx import (
    AuthenticatedMSTRRESTSession as HttpxAuthenticatedMSTRRESTSession,
    MSTRRESTSession as HttpxMSTRRESTSession,
    MSTRSessionProtocol as HttpxMSTRSessionProtocol,
)
from mstr.requests.rest.base import MSTR_AUTH_TOKEN, MSTR_PROJECT_ID_HEADER

BASE_URL = "https://example.com/api/"
PROJECTS = [{"name": "Tutorial", "id": "P1"}, {"name": "Sales", "id": "P2"}]


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


def make_session(server, cls=HttpxMSTRRESTSession, **kwargs):
    return cls(base_url=BASE_URL, transport=httpx.MockTransport(server), **kwargs)


# ---------------------------------------------------------------------------
# Base session
# ---------------------------------------------------------------------------


def test_request_adds_auth_and_project_headers(server):
    with make_session(server) as session:
        session.headers[MSTR_AUTH_TOKEN] = "tok"
        session.get("reports", project_id="P1")
    assert server.last.url == "https://example.com/api/reports"
    assert server.last.headers[MSTR_AUTH_TOKEN] == "tok"
    assert server.last.headers[MSTR_PROJECT_ID_HEADER] == "P1"


@pytest.mark.parametrize(
    "method", ["options", "head", "post", "put", "patch", "delete"]
)
def test_verb_methods_send_matching_method(server, method):
    with make_session(server) as session:
        getattr(session, method)("thing")
    assert server.last.method == method.upper()


def test_request_captures_x_mstr_response_headers(server):
    server.error = (200, {"X-MSTR-Something": "1", "Other": "2"}, b"")
    with make_session(server) as session:
        session.get("x")
        assert session.headers["X-MSTR-Something"] == "1"
        assert "Other" not in session.headers


def test_request_translates_json_errors(server):
    body = json.dumps({"code": "ERR004", "message": "missing"}).encode()
    server.error = (404, {"Content-Type": "application/json;charset=UTF-8"}, body)
    with make_session(server) as session:
        with pytest.raises(exceptions.ResourceNotFoundException):
            session.get("missing")


def test_request_returns_non_json_errors(server):
    server.error = (500, {"Content-Type": "text/html"}, b"<html/>")
    with make_session(server) as session:
        response = session.get("broken")
    assert response.status_code == 500


def test_request_warns_on_double_slash(server):
    with make_session(server) as session:
        with pytest.warns(UserWarning, match="contains a `//`"):
            session.get("a//b//c")


def test_defaults_match_sync_session(server):
    with make_session(server) as session:
        assert session.client.timeout == httpx.Timeout(None)
        assert session.client.follow_redirects is True
        assert session.base_url == BASE_URL
        assert isinstance(session, HttpxMSTRSessionProtocol)


def test_supplied_client_is_not_closed(server):
    client = httpx.Client(transport=httpx.MockTransport(server))
    with HttpxMSTRRESTSession(base_url=BASE_URL, client=client):
        pass
    assert client.is_closed is False
    client.close()


def test_owned_client_is_closed(server):
    session = make_session(server)
    with session:
        pass
    assert session.client.is_closed is True


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_login_and_logout(server):
    with make_session(server) as session:
        assert session.has_session() is False
        session.login(username="u", password="p")
        assert session.has_session() is True
        assert json.loads(server.last.content)["loginMode"] == 1
        assert session.cookies["JSESSIONID"] == "abc"

        session.get("x")
        assert server.last.headers[MSTR_AUTH_TOKEN] == "token-1"

        session.logout()
        assert session.has_session() is False


def test_login_failure_raises_http_status_error(server):
    server.login_status = 401
    with make_session(server) as session:
        with pytest.raises(httpx.HTTPStatusError):
            session.login(username="u", password="p")


def test_delegate(server):
    with make_session(server) as session:
        session.delegate("id-token")
    assert json.loads(server.last.content) == {
        "loginMode": -1,
        "identityToken": "id-token",
    }


def test_delegate_failure_raises_http_status_error(server):
    server.login_status = 500
    with make_session(server) as session:
        with pytest.raises(httpx.HTTPStatusError):
            session.delegate("id-token")


def test_logout_keeps_token_on_unexpected_status(server):
    with make_session(server) as session:
        session.login()
        server.error = (200, {}, b"")
        session.logout()
        assert session.has_session() is True


# ---------------------------------------------------------------------------
# Sessions and projects
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method, path",
    [
        ("extend_session", "/api/sessions"),
        ("get_userinfo", "/api/sessions/userInfo"),
        ("get_session_info", "/api/sessions"),
    ],
)
def test_session_endpoints(server, method, path):
    with make_session(server) as session:
        session.login()
        response = getattr(session, method)()
    assert response.json() == {"path": path}


@pytest.mark.parametrize(
    "method", ["extend_session", "get_userinfo", "get_session_info", "get_projects"]
)
def test_endpoints_require_a_session(server, method):
    with make_session(server) as session:
        with pytest.raises(exceptions.SessionException):
            getattr(session, method)()
    assert server.requests == []


def test_load_projects_and_get_project_id(server):
    with make_session(server) as session:
        with pytest.raises(exceptions.SessionException):
            session.get_project_id("Tutorial")
        session.login()
        assert session.get_projects() == PROJECTS
        session.load_projects()
    assert session.get_project_id("Sales") == "P2"
    assert session.get_project_id("Nope") is None
    assert session.projects_by_id == {"P1": "Tutorial", "P2": "Sales"}


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_round_trip_between_requests_and_httpx(server):
    sync_session = MSTRRESTSession(base_url=BASE_URL)
    sync_session.headers[MSTR_AUTH_TOKEN] = "tok"
    sync_session.cookies.set("JSESSIONID", "abc")

    httpx_session = HttpxMSTRRESTSession.from_dict(
        sync_session.to_dict(), transport=httpx.MockTransport(server)
    )
    with httpx_session:
        assert httpx_session.has_session() is True
        httpx_session.get("x")
        assert server.last.headers[MSTR_AUTH_TOKEN] == "tok"
        assert server.last.headers["cookie"] == "JSESSIONID=abc"

        restored = MSTRRESTSession.from_dict(json.loads(httpx_session.json()))
    assert restored.headers[MSTR_AUTH_TOKEN] == "tok"
    assert restored.cookies["JSESSIONID"] == "abc"
    assert restored.base_url == BASE_URL


def test_update_from_json_string_and_dict_alias(server):
    with make_session(server) as session:
        session.update_from_json(
            json.dumps(
                {"base_url": "https://other/api/", "cookies": {}, "headers": {"A": "1"}}
            )
        )
        assert session.base_url == "https://other/api/"
        assert session.dict() == session.to_dict()
        assert session.to_dict()["headers"]["a"] == "1"


@pytest.mark.parametrize("data", [{"base_url": BASE_URL}, 42])
def test_update_from_json_rejects_incomplete_data(server, data):
    with make_session(server) as session:
        with pytest.raises(exceptions.SessionException):
            session.update_from_json(data)


# ---------------------------------------------------------------------------
# Authenticated session
# ---------------------------------------------------------------------------


def test_authenticated_session_logs_in_and_out(server):
    session = make_session(
        server, HttpxAuthenticatedMSTRRESTSession, username="u", password="p"
    )
    with session as s:
        assert s is session
        assert s.has_session() is True
    assert server.paths() == ["/api/auth/login", "/api/auth/logout"]
    assert session.client.is_closed is True


def test_authenticated_session_api_key(server):
    with make_session(
        server, HttpxAuthenticatedMSTRRESTSession, api_key="k", application_type=35
    ):
        body = json.loads(server.requests[0].content)
    assert body == {"username": "k", "loginMode": 4096, "applicationType": 35}


def test_authenticated_session_identity_token_skips_logout(server):
    with make_session(server, HttpxAuthenticatedMSTRRESTSession, identity_token="id"):
        pass
    assert server.paths() == ["/api/auth/delegate"]


def test_authenticated_session_resolves_callables(server):
    session = HttpxAuthenticatedMSTRRESTSession(
        base_url=lambda: BASE_URL,
        username=lambda: "u",
        password=functools.partial(str, "p"),
        transport=httpx.MockTransport(server),
    )
    assert session.base_url == ""
    with session:
        body = json.loads(server.requests[0].content)
    assert body["username"] == "u" and body["password"] == "p"
    assert server.requests[0].url == "https://example.com/api/auth/login"


def test_authenticated_session_closes_client_on_login_failure(server):
    server.login_status = 401
    session = make_session(
        server, HttpxAuthenticatedMSTRRESTSession, username="u", password="p"
    )
    with pytest.raises(httpx.HTTPStatusError):
        with session:
            pass  # pragma: no cover
    assert session.client.is_closed is True


# ---------------------------------------------------------------------------
# Parity and deprecation
# ---------------------------------------------------------------------------


def _public_methods(cls):
    return {name for name in dir(cls) if not name.startswith("_")}


def test_httpx_and_async_sessions_match_requests_session_api():
    from mstr.requests.rest.aio import (
        AsyncAuthenticatedMSTRRESTSession,
        AsyncMSTRRESTSession,
    )
    from mstr.requests.rest.api import AuthMixin, ProjectsMixin, SessionsMixin
    from mstr.requests.rest.mixins import SessionPersistenceMixin

    expected = set()
    for mixin in (AuthMixin, SessionsMixin, ProjectsMixin, SessionPersistenceMixin):
        expected |= _public_methods(mixin)
    expected |= {"has_session", "destroy_auth_token", "request", "get", "post"}
    expected |= {"put", "patch", "delete", "head", "options", "base_url"}
    expected |= {"headers", "cookies"}

    for cls in (
        HttpxMSTRRESTSession,
        HttpxAuthenticatedMSTRRESTSession,
        AsyncMSTRRESTSession,
        AsyncAuthenticatedMSTRRESTSession,
    ):
        assert expected <= _public_methods(cls), cls


def test_requests_session_emits_pending_deprecation_warning():
    with pytest.warns(PendingDeprecationWarning, match="mstr.requests.httpx"):
        MSTRRESTSession(base_url=BASE_URL)


def test_httpx_session_does_not_warn(server):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        make_session(server).close()


def test_public_module_exports():
    import mstr.requests
    import mstr.requests.httpx

    assert mstr.requests.httpx.Credential is mstr.requests.Credential
    assert set(mstr.requests.httpx.__all__) == {
        "AuthenticatedMSTRRESTSession",
        "Credential",
        "MSTRRESTSession",
        "MSTRSessionProtocol",
    }
