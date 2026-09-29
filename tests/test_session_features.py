"""Tests for re-login, keep-alive, retries, project names, identity tokens and
request logging, on the httpx and async sessions; no network."""

import logging
import threading
import time

import anyio
import httpx
import pytest

from mstr.requests import (
    AsyncAuthenticatedMSTRRESTSession,
    AsyncMSTRRESTSession,
    AuthenticatedMSTRRESTSession,
    MSTRRESTSession,
)
from mstr.requests.rest import core, exceptions
from mstr.requests.rest.core import MSTR_AUTH_TOKEN, MSTR_PROJECT_ID_HEADER
from mstr.requests.rest.httpx_sync.base import MSTRBaseSession

BASE_URL = "https://user:secret@example.com/api/"
PROJECTS = [{"name": "Tutorial", "id": "P1"}, {"name": "Sales", "id": "P2"}]
ERR009 = {"code": "ERR009", "message": "The user's session has expired"}


@pytest.fixture(params=["asyncio", "trio"])
def anyio_backend(request):
    return request.param


class FakeServer:
    """A MicroStrategy REST API whose sessions can be expired on demand.

    ``failures`` is a list of responses (or exceptions) to return, in order,
    for requests to paths other than ``auth/``.
    """

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.logins = 0
        self.valid_tokens: set[str] = set()
        self.failures: list = []
        self.projects = list(PROJECTS)
        self.lock = threading.Lock()

    def expire_sessions(self):
        self.valid_tokens.clear()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        with self.lock:
            return self._handle(request)

    def _handle(self, request):
        self.requests.append(request)
        path = request.url.path
        if path.endswith("/auth/login") or path.endswith("/auth/delegate"):
            self.logins += 1
            token = f"token-{self.logins}"
            self.valid_tokens.add(token)
            return httpx.Response(204, headers={MSTR_AUTH_TOKEN: token})
        if path.endswith("/auth/logout"):
            return httpx.Response(204)
        if self.failures:
            failure = self.failures.pop(0)
            if isinstance(failure, Exception):
                raise failure
            return failure
        if request.headers.get(MSTR_AUTH_TOKEN) not in self.valid_tokens:
            return httpx.Response(401, json=ERR009)
        if path.endswith("/auth/identityToken"):
            return httpx.Response(201, headers={"X-MSTR-IdentityToken": "identity-1"})
        if path.endswith("/projects"):
            return httpx.Response(200, json=self.projects)
        return httpx.Response(200, json={"ok": True})

    def paths(self):
        return [r.url.path.removeprefix("/api/") for r in self.requests]


@pytest.fixture
def server():
    return FakeServer()


def sync_session(server, cls=AuthenticatedMSTRRESTSession, **kwargs):
    kwargs.setdefault("username", "dave")
    kwargs.setdefault("password", "hellodave")
    return cls(BASE_URL, transport=httpx.MockTransport(server), **kwargs)


def async_session(server, cls=AsyncAuthenticatedMSTRRESTSession, **kwargs):
    kwargs.setdefault("username", "dave")
    kwargs.setdefault("password", "hellodave")
    return cls(BASE_URL, transport=httpx.MockTransport(server), **kwargs)


# Re-login


def test_expired_session_raises_without_relogin(server):
    with sync_session(server) as session:
        server.expire_sessions()
        with pytest.raises(exceptions.SessionException):
            session.get("sessions")
    assert server.logins == 1


def test_relogin_logs_in_again_and_retries(server):
    with sync_session(server, relogin=True) as session:
        server.expire_sessions()
        response = session.get("sessions")
        assert response.json() == {"ok": True}
        assert session.headers[MSTR_AUTH_TOKEN] == "token-2"
    assert server.logins == 2
    assert server.paths() == [
        "auth/login",
        "sessions",
        "auth/login",
        "sessions",
        "auth/logout",
    ]


def test_relogin_resolves_credentials_again(server):
    passwords = iter(["first", "second"])
    with sync_session(server, relogin=True, password=lambda: next(passwords)) as s:
        server.expire_sessions()
        s.get("sessions")
    logins = [r for r in server.requests if r.url.path.endswith("auth/login")]
    assert [b"first" in r.content for r in logins] == [True, False]
    assert b"second" in logins[1].content


def test_relogin_retries_only_once(server):
    with sync_session(server, relogin=True) as session:
        server.failures = [httpx.Response(401, json=ERR009)] * 2
        with pytest.raises(exceptions.SessionException):
            session.get("sessions")
    assert server.logins == 2


def test_relogin_skips_auth_endpoints_and_include_auth_false(server):
    with sync_session(server, relogin=True) as session:
        server.expire_sessions()
        with pytest.raises(exceptions.SessionException):
            session.post("auth/identityToken")
        with pytest.raises(exceptions.SessionException):
            session.get("sessions", include_auth=False)
    assert server.logins == 1


def test_relogin_ignores_other_session_errors(server):
    with sync_session(server, relogin=True) as session:
        server.failures = [httpx.Response(400, json={"code": "ERR005"})]
        with pytest.raises(exceptions.InvalidRequestException):
            session.get("sessions")
    assert server.logins == 1


def test_relogin_from_many_threads_logs_in_once(server):
    with sync_session(server, relogin=True) as session:
        server.expire_sessions()
        threads = [
            threading.Thread(target=session.get, args=("sessions",)) for _ in range(5)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert server.logins == 2


def test_keepalive_extends_session_until_exit(server):
    with sync_session(server, keepalive_interval=0.01) as session:
        deadline = time.monotonic() + 2
        while server.paths().count("sessions") < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        thread = session._keepalive_thread
    assert server.paths().count("sessions") >= 2
    assert thread is not None and not thread.is_alive()
    assert [r.method for r in server.requests if r.url.path.endswith("/sessions")][
        0
    ] == "PUT"
    count = len(server.requests)
    time.sleep(0.05)
    assert len(server.requests) == count


def test_keepalive_logs_failures_and_keeps_going(server, caplog):
    with sync_session(server, keepalive_interval=0.01):
        server.failures = [httpx.Response(400, json={"code": "ERR005"})]
        deadline = time.monotonic() + 2
        while server.paths().count("sessions") < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
    assert "Keep-alive request failed" in caplog.text


@pytest.mark.anyio
async def test_async_relogin_logs_in_again_and_retries(server):
    async with async_session(server, relogin=True) as session:
        server.expire_sessions()
        response = await session.get("sessions")
        assert response.json() == {"ok": True}
    assert server.logins == 2


@pytest.mark.anyio
async def test_async_relogin_from_many_tasks_logs_in_once(server):
    async with async_session(server, relogin=True) as session:
        server.expire_sessions()
        async with anyio.create_task_group() as group:
            for _ in range(5):
                group.start_soon(session.get, "sessions")
    assert server.logins == 2


@pytest.mark.anyio
async def test_async_expired_session_raises_without_relogin(server):
    async with async_session(server) as session:
        server.expire_sessions()
        with pytest.raises(exceptions.SessionException):
            await session.get("sessions")


@pytest.mark.anyio
async def test_async_keepalive_extends_session_until_exit(server):
    async with async_session(server, keepalive_interval=0.01):
        with anyio.fail_after(2):
            while server.paths().count("sessions") < 2:
                await anyio.sleep(0.01)
    count = len(server.requests)
    await anyio.sleep(0.05)
    assert len(server.requests) == count
    assert server.paths()[-1] == "auth/logout"


@pytest.mark.anyio
async def test_async_keepalive_stops_when_block_raises(server):
    with pytest.raises(ValueError):
        async with async_session(server, keepalive_interval=0.01):
            raise ValueError("boom")
    assert server.paths()[-1] == "auth/logout"


# Retries


def plain_session(server, **kwargs):
    kwargs.setdefault("backoff_factor", 0)
    return MSTRRESTSession(BASE_URL, transport=httpx.MockTransport(server), **kwargs)


def test_no_retries_by_default(server):
    server.failures = [httpx.Response(503)]
    assert plain_session(server).get("thing").status_code == 503


@pytest.mark.parametrize("status", [502, 503, 504])
def test_retries_gateway_errors_for_get(server, status):
    server.valid_tokens.add(None)
    server.failures = [httpx.Response(status), httpx.Response(status)]
    response = plain_session(server, retries=2).get("thing")
    assert response.status_code == 200
    assert len(server.requests) == 3


def test_gives_up_after_retries(server):
    server.failures = [httpx.Response(503)] * 3
    response = plain_session(server, retries=2).get("thing")
    assert response.status_code == 503
    assert len(server.requests) == 3


def test_does_not_retry_post_on_status(server):
    server.failures = [httpx.Response(503)]
    assert plain_session(server, retries=2).post("thing").status_code == 503
    assert len(server.requests) == 1


def test_does_not_retry_500(server):
    server.failures = [httpx.Response(500)]
    assert plain_session(server, retries=2).get("thing").status_code == 500


def test_retries_connect_errors_for_any_method(server):
    server.valid_tokens.add(None)
    server.failures = [httpx.ConnectError("refused")]
    assert plain_session(server, retries=1).post("thing").status_code == 200


def test_retries_read_timeouts_only_for_idempotent_methods(server):
    server.valid_tokens.add(None)
    server.failures = [httpx.ReadTimeout("slow")]
    assert plain_session(server, retries=1).get("thing").status_code == 200
    server.failures = [httpx.ReadTimeout("slow")]
    with pytest.raises(httpx.ReadTimeout):
        plain_session(server, retries=1).post("thing")


def test_retry_waits_with_backoff(server, monkeypatch):
    waits = []
    monkeypatch.setattr(time, "sleep", waits.append)
    server.valid_tokens.add(None)
    server.failures = [
        httpx.Response(503),
        httpx.Response(503, headers={"Retry-After": "3"}),
        httpx.Response(503),
    ]
    plain_session(server, retries=3, backoff_factor=0.5).get("thing")
    assert waits == [0.5, 3.0, 2.0]


def test_retry_logs_redacted_url(server, caplog):
    server.valid_tokens.add(None)
    server.failures = [httpx.Response(503)]
    plain_session(server, retries=1).get("thing")
    assert "GET https://example.com/api/thing returned 503; retry 1 of 1" in caplog.text
    assert "secret" not in caplog.text


@pytest.mark.parametrize(
    "attempt, factor, retry_after, expected",
    [
        (1, 0.5, None, 0.5),
        (3, 0.5, None, 2.0),
        (1, 0.5, "10", 10.0),
        (1, 0.5, "Wed, 21 Oct 2015 07:28:00 GMT", 0.5),
        (20, 1, None, core.MAX_RETRY_DELAY),
        (1, 0, "600", core.MAX_RETRY_DELAY),
    ],
)
def test_retry_delay(attempt, factor, retry_after, expected):
    assert core.retry_delay(attempt, factor, retry_after) == expected


@pytest.mark.anyio
async def test_async_retries(server, monkeypatch):
    server.valid_tokens.add(None)
    server.failures = [httpx.Response(503), httpx.ConnectError("refused")]
    session = AsyncMSTRRESTSession(
        BASE_URL, transport=httpx.MockTransport(server), retries=2, backoff_factor=0
    )
    assert (await session.get("thing")).status_code == 200
    assert len(server.requests) == 3


# Projects by name


def test_project_name_sends_project_id(server):
    with sync_session(server) as session:
        session.get("reports", project="Sales")
        session.get("reports", project="Tutorial")
    sent = [r for r in server.requests if r.url.path.endswith("/reports")]
    assert [r.headers[MSTR_PROJECT_ID_HEADER] for r in sent] == ["P2", "P1"]
    assert server.paths().count("projects") == 1


def test_unknown_project_name_reloads_once_then_raises(server):
    with sync_session(server) as session:
        session.load_projects()
        server.projects.append({"name": "New", "id": "P3"})
        session.get("reports", project="New")
        assert server.paths().count("projects") == 2
        with pytest.raises(exceptions.ResourceNotFoundException, match="Missing"):
            session.get("reports", project="Missing")
        assert server.paths().count("projects") == 3


def test_project_and_project_id_together_raise(server):
    with sync_session(server) as session:
        with pytest.raises(ValueError):
            session.get("reports", project="Sales", project_id="P2")


def test_project_name_needs_project_helpers(server):
    session = MSTRBaseSession(BASE_URL, transport=httpx.MockTransport(server))
    with pytest.raises(TypeError, match="project helpers"):
        session.get("reports", project="Sales")


@pytest.mark.anyio
async def test_async_project_name_sends_project_id(server):
    async with async_session(server) as session:
        await session.get("reports", project="Sales")
        assert await session.resolve_project_id("Tutorial") == "P1"
    sent = [r for r in server.requests if r.url.path.endswith("/reports")]
    assert sent[0].headers[MSTR_PROJECT_ID_HEADER] == "P2"


# Identity tokens


def test_create_identity_token(server):
    with sync_session(server) as session:
        assert session.create_identity_token() == "identity-1"
        assert "X-MSTR-IdentityToken" not in session.headers
    request = server.requests[-2]
    assert request.method == "POST"
    assert request.url.path == "/api/auth/identityToken"


def test_create_identity_token_needs_a_session(server):
    with pytest.raises(exceptions.SessionException):
        plain_session(server).create_identity_token()


def test_create_identity_token_without_header_raises(server):
    with sync_session(server) as session:
        server.failures = [httpx.Response(201)]
        with pytest.raises(exceptions.MSTRException, match="identity token"):
            session.create_identity_token()


@pytest.mark.anyio
async def test_async_create_identity_token(server):
    async with async_session(server) as session:
        assert await session.create_identity_token() == "identity-1"
        assert "X-MSTR-IdentityToken" not in session.headers


# Logging


def test_requests_are_logged_without_secrets(server, caplog):
    caplog.set_level(logging.DEBUG, logger="mstr.requests")
    with sync_session(server):
        pass
    messages = [r.getMessage() for r in caplog.records]
    assert any(
        m.startswith("POST https://example.com/api/auth/login -> 204 (")
        for m in messages
    )
    assert "secret" not in caplog.text
    assert "hellodave" not in caplog.text
    assert "token-1" not in caplog.text


def test_redact_url():
    assert core.redact_url("https://u:p@h.example/x?y=1") == "https://h.example/x?y=1"
    assert core.redact_url("https://h.example/x") == "https://h.example/x"
