"""Unit tests for SessionPersistenceMixin (mixins.py)."""

import json

import pytest

from mstr.requests import MSTRRESTSession
from mstr.requests.rest import exceptions


BASE_URL = "https://example.com/api/"


class TestSessionPersistenceMixin:
    """Test to_dict, dict, json, update_from_json, from_dict."""

    def test_to_dict_contains_base_url_cookies_headers(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.headers["X-MSTR-AuthToken"] = "token"
        d = session.to_dict()
        assert d["base_url"] == BASE_URL
        assert "cookies" in d
        assert d["headers"].get("X-MSTR-AuthToken") == "token"

    def test_dict_is_alias_for_to_dict(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        assert session.dict() == session.to_dict()

    def test_json_returns_json_string_of_to_dict(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        s = session.json()
        parsed = json.loads(s)
        assert parsed["base_url"] == BASE_URL
        assert "cookies" in parsed
        assert "headers" in parsed

    def test_update_from_json_with_dict(self):
        session = MSTRRESTSession(base_url="https://old.com/")
        data = {
            "base_url": "https://new.com/api/",
            "cookies": {},
            "headers": {"X-MSTR-AuthToken": "newtoken"},
        }
        session.update_from_json(data)
        assert session.base_url == "https://new.com/api/"
        assert session.headers.get("X-MSTR-AuthToken") == "newtoken"

    def test_update_from_json_with_json_string(self):
        session = MSTRRESTSession(base_url="https://old.com/")
        data = json.dumps(
            {
                "base_url": "https://fromstr.com/",
                "cookies": {},
                "headers": {},
            }
        )
        session.update_from_json(data)
        assert session.base_url == "https://fromstr.com/"

    def test_update_from_json_with_non_dict_non_str_uses_empty_dict_then_raises(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        with pytest.raises(exceptions.SessionException) as exc_info:
            session.update_from_json(123)
        assert "base_url" in str(exc_info.value)

    def test_update_from_json_missing_key_raises_session_exception(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        with pytest.raises(exceptions.SessionException, match="base_url"):
            session.update_from_json({"cookies": {}, "headers": {}})
        with pytest.raises(exceptions.SessionException, match="cookies"):
            session.update_from_json({"base_url": BASE_URL, "headers": {}})
        with pytest.raises(exceptions.SessionException, match="headers"):
            session.update_from_json({"base_url": BASE_URL, "cookies": {}})

    def test_from_dict_creates_session_with_restored_state(self):
        d = {
            "base_url": "https://restored.com/api/",
            "cookies": {},
            "headers": {"X-MSTR-AuthToken": "restored"},
        }
        session = MSTRRESTSession.from_dict(d)
        assert session.base_url == "https://restored.com/api/"
        assert session.headers.get("X-MSTR-AuthToken") == "restored"

    def test_from_dict_with_empty_base_url_uses_default(self):
        d = {
            "base_url": "",
            "cookies": {},
            "headers": {},
        }
        session = MSTRRESTSession.from_dict(d)
        assert session.base_url == ""

    def test_from_dict_with_missing_base_url_key_uses_default_then_raises_on_update(self):
        d = {"cookies": {}, "headers": {}}
        with pytest.raises(exceptions.SessionException):
            MSTRRESTSession.from_dict(d)
