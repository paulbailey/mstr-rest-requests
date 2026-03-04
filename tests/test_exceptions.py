"""Tests for error-code-to-exception mapping in MSTRBaseSession.request."""

import json
from unittest.mock import MagicMock, patch

import pytest
from requests_toolbelt.sessions import BaseUrlSession

from mstr.requests import MSTRRESTSession
from mstr.requests.rest import exceptions


def _mock_error_response(code: str, message: str = "something went wrong"):
    """Build a mock requests.Response that triggers error handling."""
    body = {"code": code, "message": message}
    resp = MagicMock()
    resp.ok = False
    resp.headers = {"content-type": "application/json"}
    resp.json.return_value = body
    resp.text = json.dumps(body)
    return resp


def _mock_error_response_no_code():
    body = {"message": "mysterious failure"}
    resp = MagicMock()
    resp.ok = False
    resp.headers = {"content-type": "application/json"}
    resp.json.return_value = body
    resp.text = json.dumps(body)
    return resp


@pytest.fixture
def session():
    return MSTRRESTSession(base_url="https://example.com/api/")


_ERROR_CODE_CASES = [
    ("ERR003", exceptions.LoginFailureException),
    ("ERR002", exceptions.IServerException),
    ("ERR0013", exceptions.IServerException),
    ("ERR004", exceptions.ResourceNotFoundException),
    ("ERR005", exceptions.InvalidRequestException),
    ("ERR006", exceptions.InvalidRequestException),
    ("ERR007", exceptions.InvalidRequestException),
    ("ERR009", exceptions.SessionException),
    ("ERR0014", exceptions.InsufficientPrivilegesException),
    ("ERR0017", exceptions.InsufficientPrivilegesException),
    ("ERR0015", exceptions.ObjectAlreadyExistsException),
]


@pytest.mark.parametrize("code,expected_exc", _ERROR_CODE_CASES, ids=[c for c, _ in _ERROR_CODE_CASES])
def test_error_code_raises_correct_exception(session, code, expected_exc):
    with patch.object(BaseUrlSession, "request", return_value=_mock_error_response(code)):
        with pytest.raises(expected_exc) as exc_info:
            session.request("GET", "test")
        assert exc_info.value.code == code


_FALLTHROUGH_CODES = ["ERR001", "ERR008", "ERR0010", "ERR0016", "ERR0020"]


@pytest.mark.parametrize("code", _FALLTHROUGH_CODES)
def test_unhandled_codes_raise_base_exception(session, code):
    with patch.object(BaseUrlSession, "request", return_value=_mock_error_response(code)):
        with pytest.raises(exceptions.MSTRException) as exc_info:
            session.request("GET", "test")
        assert exc_info.value.code == code


def test_missing_code_raises_unknown_exception(session):
    with patch.object(BaseUrlSession, "request", return_value=_mock_error_response_no_code()):
        with pytest.raises(exceptions.MSTRUnknownException):
            session.request("GET", "test")


def test_all_exceptions_inherit_from_mstr_exception():
    for _, exc_class in _ERROR_CODE_CASES:
        assert issubclass(exc_class, exceptions.MSTRException)
    assert issubclass(exceptions.MSTRUnknownException, exceptions.MSTRException)
    assert issubclass(exceptions.ExecutionCancelledException, exceptions.MSTRException)
