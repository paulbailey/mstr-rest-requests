"""Unit tests for MSTRBaseSession (base.py) with mocks; no network."""

import warnings
from unittest.mock import MagicMock, patch

import pytest
from requests_toolbelt.sessions import BaseUrlSession

from mstr.requests.compat import MSTRRESTSession
from mstr.requests.rest import exceptions
from mstr.requests.rest.base import MSTR_AUTH_TOKEN, MSTR_PROJECT_ID_HEADER


@pytest.fixture
def session():
    return MSTRRESTSession(base_url="https://example.com/api/")


def test_request_warns_on_double_slash_in_path(session):
    """Request with path containing multiple '//' triggers warning."""
    with patch.object(BaseUrlSession, "request", return_value=MagicMock(ok=True, headers={})) as mock_request:
        with pytest.warns(UserWarning, match="contains a `//` in the path"):
            session.request("GET", "path//with//slashes")
    mock_request.assert_called_once()


def test_destroy_auth_token_when_no_token_does_not_raise(session):
    """destroy_auth_token with no token present hits KeyError path and passes."""
    assert session.has_session() is False
    session.destroy_auth_token()  # no exception
    assert session.has_session() is False


def test_request_value_error_on_non_json_error_body(session):
    """When response is not ok and .json() raises ValueError, MSTRException is raised."""
    resp = MagicMock()
    resp.ok = False
    resp.headers = {"content-type": "application/json"}
    resp.json.side_effect = ValueError("invalid json")
    resp.text = "not valid json"

    with patch.object(BaseUrlSession, "request", return_value=resp):
        with pytest.raises(exceptions.MSTRException) as exc_info:
            session.request("GET", "test")
    assert "Couldn't parse response" in str(exc_info.value)


def test_request_captures_x_mstr_headers_on_success(session):
    """Successful response with X-MSTR-* headers updates session.headers."""
    resp = MagicMock()
    resp.ok = True
    resp.headers = {"X-MSTR-AuthToken": "abc123", "Content-Type": "application/json"}

    with patch.object(BaseUrlSession, "request", return_value=resp):
        session.request("GET", "test")

    assert session.headers.get("X-MSTR-AuthToken") == "abc123"


def test_request_includes_auth_header_when_session_has_token(session):
    """When session has auth token, request passes it in headers (covers include_auth path)."""
    session.headers[MSTR_AUTH_TOKEN] = "existing-token"
    with patch.object(BaseUrlSession, "request", return_value=MagicMock(ok=True, headers={})) as mock_request:
        session.request("GET", "path")
    call_kw = mock_request.call_args[1]
    assert call_kw["headers"].get(MSTR_AUTH_TOKEN) == "existing-token"


def test_request_includes_project_id_header_when_given(session):
    """When project_id is passed, request includes X-MSTR-ProjectID header."""
    with patch.object(BaseUrlSession, "request", return_value=MagicMock(ok=True, headers={})) as mock_request:
        session.request("GET", "path", project_id="proj-123")
    call_kw = mock_request.call_args[1]
    assert call_kw["headers"].get(MSTR_PROJECT_ID_HEADER) == "proj-123"


def test_request_error_with_charset_in_content_type_is_translated(session):
    """A JSON error body with a charset parameter is still translated."""
    resp = MagicMock()
    resp.ok = False
    resp.headers = {"Content-Type": "application/json;charset=UTF-8"}
    resp.json.return_value = {"code": "ERR004", "message": "missing"}

    with patch.object(BaseUrlSession, "request", return_value=resp):
        with pytest.raises(exceptions.ResourceNotFoundException):
            session.request("GET", "test")


def test_request_error_without_content_type_returns_response(session):
    """A failed response with no Content-Type header is returned, not a KeyError."""
    resp = MagicMock()
    resp.ok = False
    resp.headers = {}

    with patch.object(BaseUrlSession, "request", return_value=resp):
        assert session.request("GET", "test") is resp


def test_request_does_not_mutate_caller_headers(session):
    """Headers passed by the caller are copied, not modified."""
    session.headers[MSTR_AUTH_TOKEN] = "existing-token"
    caller_headers = {"Accept": "application/json"}
    with patch.object(BaseUrlSession, "request", return_value=MagicMock(ok=True, headers={})):
        session.request("GET", "path", headers=caller_headers, project_id="p")
    assert caller_headers == {"Accept": "application/json"}
