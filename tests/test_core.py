"""Unit tests for the transport-independent core (core.py); no network."""

import warnings
from unittest.mock import MagicMock

import pytest

from mstr.requests.rest import core, exceptions

# ---------------------------------------------------------------------------
# Request headers
# ---------------------------------------------------------------------------


def test_build_request_headers_adds_auth_token_and_project_id():
    headers = core.build_request_headers(
        {"Accept": "application/json"},
        {core.MSTR_AUTH_TOKEN: "tok"},
        include_auth=True,
        project_id="proj",
    )
    assert headers == {
        "Accept": "application/json",
        core.MSTR_AUTH_TOKEN: "tok",
        core.MSTR_PROJECT_ID_HEADER: "proj",
    }


def test_build_request_headers_skips_auth_when_not_requested():
    headers = core.build_request_headers(
        None, {core.MSTR_AUTH_TOKEN: "tok"}, include_auth=False
    )
    assert headers == {}


def test_build_request_headers_skips_auth_when_session_has_none():
    assert core.build_request_headers(None, {}) == {}


def test_build_request_headers_does_not_mutate_caller_headers():
    caller = {"Accept": "application/json"}
    core.build_request_headers(caller, {core.MSTR_AUTH_TOKEN: "tok"}, project_id="p")
    assert caller == {"Accept": "application/json"}


def test_warn_on_double_slash():
    with pytest.warns(UserWarning, match="contains a `//` in the path"):
        core.warn_on_double_slash("https://example.com/api//projects")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        core.warn_on_double_slash("https://example.com/api/projects")


# ---------------------------------------------------------------------------
# Response headers
# ---------------------------------------------------------------------------


def test_mstr_response_headers_keeps_only_x_mstr_headers():
    items = [
        ("X-MSTR-AuthToken", "abc"),
        ("x-mstr-other", "1"),
        ("Content-Type", "application/json"),
    ]
    assert core.mstr_response_headers(items) == {
        "X-MSTR-AuthToken": "abc",
        "x-mstr-other": "1",
    }


@pytest.mark.parametrize(
    "headers, expected",
    [
        ({"content-type": "application/json"}, True),
        ({"Content-Type": "application/json; charset=UTF-8"}, True),
        ({"CONTENT-TYPE": "Application/JSON"}, True),
        ({"Content-Type": "text/html"}, False),
        ({}, False),
    ],
)
def test_is_json_content_type(headers, expected):
    assert core.is_json_content_type(headers) is expected


# ---------------------------------------------------------------------------
# Error translation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code, exception_class",
    [
        ("ERR002", exceptions.IServerException),
        ("ERR0013", exceptions.IServerException),
        ("ERR003", exceptions.LoginFailureException),
        ("ERR004", exceptions.ResourceNotFoundException),
        ("ERR005", exceptions.InvalidRequestException),
        ("ERR006", exceptions.InvalidRequestException),
        ("ERR007", exceptions.InvalidRequestException),
        ("ERR009", exceptions.SessionException),
        ("ERR0014", exceptions.InsufficientPrivilegesException),
        ("ERR0017", exceptions.InsufficientPrivilegesException),
        ("ERR0015", exceptions.ObjectAlreadyExistsException),
    ],
)
def test_exception_for_payload_known_codes(code, exception_class):
    exc = core.exception_for_payload({"code": code, "message": "boom"})
    assert type(exc) is exception_class
    assert exc.code == code


def test_exception_for_payload_unknown_code_is_base_exception():
    exc = core.exception_for_payload({"code": "ERR999", "message": "boom"})
    assert type(exc) is exceptions.MSTRException


def test_exception_for_payload_without_code_is_unknown_exception():
    exc = core.exception_for_payload({"message": "boom"})
    assert type(exc) is exceptions.MSTRUnknownException


def _response(headers, payload=None, json_error=None, text=""):
    response = MagicMock()
    response.headers = headers
    response.text = text
    if json_error is not None:
        response.json.side_effect = json_error
    else:
        response.json.return_value = payload
    return response


def test_raise_for_mstr_error_raises_translated_exception():
    response = _response(
        {"Content-Type": "application/json;charset=UTF-8"},
        {"code": "ERR004", "message": "missing"},
    )
    with pytest.raises(exceptions.ResourceNotFoundException):
        core.raise_for_mstr_error(response)


def test_raise_for_mstr_error_unparseable_json():
    response = _response(
        {"Content-Type": "application/json"}, json_error=ValueError("bad"), text="oops"
    )
    with pytest.raises(exceptions.MSTRException, match="Couldn't parse response: oops"):
        core.raise_for_mstr_error(response)


@pytest.mark.parametrize("headers", [{"Content-Type": "text/html"}, {}])
def test_raise_for_mstr_error_ignores_non_json_bodies(headers):
    response = _response(headers)
    core.raise_for_mstr_error(response)
    response.json.assert_not_called()


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------


def test_login_payload_standard():
    assert core.login_payload("u", "p", application_type=35) == {
        "username": "u",
        "password": "p",
        "loginMode": 1,
        "applicationType": 35,
    }


def test_login_payload_api_key():
    assert core.login_payload(api_key="k") == {
        "username": "k",
        "loginMode": 4096,
        "applicationType": 8,
    }


def test_login_payload_username_only():
    assert core.login_payload(username="u") == {
        "username": "u",
        "loginMode": 4096,
        "applicationType": 8,
    }


def test_login_payload_anonymous():
    assert core.login_payload() == {"loginMode": 8, "applicationType": 8}


def test_delegate_payload():
    assert core.delegate_payload("tok") == {"loginMode": -1, "identityToken": "tok"}


def test_project_lookups():
    by_name, by_id = core.project_lookups(
        [{"name": "A", "id": "1"}, {"name": "B", "id": "2"}]
    )
    assert by_name == {"A": "1", "B": "2"}
    assert by_id == {"1": "A", "2": "B"}
