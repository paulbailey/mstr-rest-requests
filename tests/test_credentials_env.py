"""Tests for the environment variable credential provider."""

import httpx
import pytest

from mstr.requests import AuthenticatedMSTRRESTSession
from mstr.requests.credentials.env import env
from mstr.requests.rest.exceptions import MissingCredentialException


def test_env_reads_variable_when_called(monkeypatch):
    provider = env("MSTR_TEST_PASSWORD")
    monkeypatch.setenv("MSTR_TEST_PASSWORD", "first")
    assert provider() == "first"
    monkeypatch.setenv("MSTR_TEST_PASSWORD", "second")
    assert provider() == "second"


@pytest.mark.parametrize("value", [None, ""])
def test_env_unset_or_empty_raises(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("MSTR_TEST_PASSWORD", raising=False)
    else:
        monkeypatch.setenv("MSTR_TEST_PASSWORD", value)
    with pytest.raises(MissingCredentialException, match="MSTR_TEST_PASSWORD"):
        env("MSTR_TEST_PASSWORD")()


def test_env_default(monkeypatch):
    monkeypatch.delenv("MSTR_TEST_PASSWORD", raising=False)
    assert env("MSTR_TEST_PASSWORD", default="fallback")() == "fallback"


def test_env_missing_password_stops_login(monkeypatch):
    monkeypatch.delenv("MSTR_TEST_PASSWORD", raising=False)
    requests = []
    session = AuthenticatedMSTRRESTSession(
        "https://example.com/api/",
        username="dave",
        password=env("MSTR_TEST_PASSWORD"),
        transport=httpx.MockTransport(lambda r: requests.append(r)),
    )
    with pytest.raises(MissingCredentialException):
        with session:
            pass
    assert requests == []
