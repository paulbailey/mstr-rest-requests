"""Unit tests for REST API mixins (auth, projects, sessions, utils) with mocks; no network."""

from unittest.mock import MagicMock, patch

import pytest
from requests import Response

from mstr.requests import MSTRRESTSession
from mstr.requests.rest import exceptions
from mstr.requests.rest.base import MSTR_AUTH_TOKEN


BASE_URL = "https://example.com/api/"


# ---------------------------------------------------------------------------
# Auth API (api/auth.py)
# ---------------------------------------------------------------------------


class TestAuthMixin:
    """Test AuthMixin post_login branches, post_logout, login, logout, delegate."""

    def test_post_login_username_password_sends_login_mode_1(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.post = MagicMock(return_value=MagicMock(status_code=204))
        session.post_login(username="u", password="p")
        session.post.assert_called_once()
        call_kw = session.post.call_args[1]
        assert call_kw["json"]["loginMode"] == 1
        assert call_kw["json"]["username"] == "u"
        assert call_kw["json"]["password"] == "p"

    def test_post_login_api_key_sends_login_mode_4096(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.post = MagicMock(return_value=MagicMock(status_code=204))
        session.post_login(api_key="mykey")
        call_kw = session.post.call_args[1]
        assert call_kw["json"]["loginMode"] == 4096
        assert call_kw["json"]["username"] == "mykey"

    def test_post_login_username_only_sends_login_mode_4096(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.post = MagicMock(return_value=MagicMock(status_code=204))
        session.post_login(username="u", password=None)
        call_kw = session.post.call_args[1]
        assert call_kw["json"]["loginMode"] == 4096
        assert call_kw["json"]["username"] == "u"

    def test_post_login_anonymous_sends_login_mode_8(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.post = MagicMock(return_value=MagicMock(status_code=204))
        session.post_login()
        call_kw = session.post.call_args[1]
        assert call_kw["json"]["loginMode"] == 8
        assert "username" not in call_kw["json"]

    def test_post_login_non_204_raises_for_status(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        bad_resp = MagicMock(status_code=401)
        bad_resp.raise_for_status = MagicMock(side_effect=Exception("401"))
        session.post = MagicMock(return_value=bad_resp)
        with pytest.raises(Exception, match="401"):
            session.post_login(username="u", password="p")
        bad_resp.raise_for_status.assert_called_once()

    def test_post_logout_204_calls_destroy_auth_token(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.post = MagicMock(return_value=MagicMock(status_code=204))
        session.destroy_auth_token = MagicMock()
        session.post_logout()
        session.destroy_auth_token.assert_called_once()

    def test_post_logout_non_204_does_not_destroy_token(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.post = MagicMock(return_value=MagicMock(status_code=500))
        session.destroy_auth_token = MagicMock()
        session.post_logout()
        session.destroy_auth_token.assert_not_called()

    def test_login_calls_post_login(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.post_login = MagicMock(return_value=MagicMock())
        session.login(username="u", password="p")
        session.post_login.assert_called_once_with("u", "p", None, 8)

    def test_logout_calls_post_logout(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.post_logout = MagicMock()
        session.logout()
        session.post_logout.assert_called_once()

    def test_delegate_success_returns_response(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        resp = MagicMock(status_code=204)
        session.post = MagicMock(return_value=resp)
        out = session.delegate("token123")
        assert out is resp
        session.post.assert_called_once_with(
            "auth/delegate", json={"loginMode": -1, "identityToken": "token123"}
        )

    def test_delegate_non_204_raises_for_status(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        bad_resp = MagicMock(status_code=403)
        bad_resp.raise_for_status = MagicMock(side_effect=Exception("forbidden"))
        session.post = MagicMock(return_value=bad_resp)
        with pytest.raises(Exception, match="forbidden"):
            session.delegate("token")
        bad_resp.raise_for_status.assert_called_once()


# ---------------------------------------------------------------------------
# Projects API (api/projects.py)
# ---------------------------------------------------------------------------


class TestProjectsMixin:
    """Test ProjectsMixin get_projects, load_projects, get_project_id."""

    def test_get_projects_returns_json(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.headers[MSTR_AUTH_TOKEN] = "x"
        session.get = MagicMock(return_value=MagicMock(json=MagicMock(return_value=[{"id": "a", "name": "Proj"}])))
        result = session.get_projects()
        session.get.assert_called_once_with("projects")
        assert result == [{"id": "a", "name": "Proj"}]

    def test_load_projects_populates_lookups(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.headers[MSTR_AUTH_TOKEN] = "x"
        session.get = MagicMock(
            return_value=MagicMock(
                json=MagicMock(
                    return_value=[
                        {"id": "id1", "name": "First"},
                        {"id": "id2", "name": "Second"},
                    ]
                )
            )
        )
        session.load_projects()
        assert session.projects_by_name == {"First": "id1", "Second": "id2"}
        assert session.projects_by_id == {"id1": "First", "id2": "Second"}

    def test_get_project_id_after_load_returns_id(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.headers[MSTR_AUTH_TOKEN] = "x"
        session.get = MagicMock(
            return_value=MagicMock(json=MagicMock(return_value=[{"id": "pid", "name": "MyProj"}]))
        )
        session.load_projects()
        assert session.get_project_id("MyProj") == "pid"

    def test_get_project_id_missing_returns_none(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.headers[MSTR_AUTH_TOKEN] = "x"
        session.get = MagicMock(return_value=MagicMock(json=MagicMock(return_value=[{"id": "pid", "name": "MyProj"}])))
        session.load_projects()
        assert session.get_project_id("Nonexistent") is None

    def test_get_project_id_before_load_raises_session_exception(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.headers[MSTR_AUTH_TOKEN] = "x"
        with pytest.raises(exceptions.SessionException, match="load_projects"):
            session.get_project_id("Any")


# ---------------------------------------------------------------------------
# Sessions API (api/sessions.py) and utils (check_valid_session)
# ---------------------------------------------------------------------------


class TestSessionsMixin:
    """Test SessionsMixin put_sessions, get_sessions_userinfo, get_sessions and aliases."""

    def test_put_sessions_calls_put(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.headers[MSTR_AUTH_TOKEN] = "x"
        session.put = MagicMock(return_value=MagicMock())
        session.put_sessions()
        session.put.assert_called_once_with("sessions")

    def test_get_sessions_userinfo_calls_get(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.headers[MSTR_AUTH_TOKEN] = "x"
        session.get = MagicMock(return_value=MagicMock())
        session.get_sessions_userinfo()
        session.get.assert_called_once_with("sessions/userInfo")

    def test_get_sessions_calls_get(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.headers[MSTR_AUTH_TOKEN] = "x"
        session.get = MagicMock(return_value=MagicMock())
        session.get_sessions()
        session.get.assert_called_once_with("sessions")

    def test_extend_session_calls_put_sessions(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.headers[MSTR_AUTH_TOKEN] = "x"
        session.put_sessions = MagicMock(return_value=MagicMock())
        session.extend_session()
        session.put_sessions.assert_called_once()

    def test_get_userinfo_calls_get_sessions_userinfo(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.headers[MSTR_AUTH_TOKEN] = "x"
        session.get_sessions_userinfo = MagicMock(return_value=MagicMock())
        session.get_userinfo()
        session.get_sessions_userinfo.assert_called_once()

    def test_get_session_info_calls_get_sessions(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        session.headers[MSTR_AUTH_TOKEN] = "x"
        session.get_sessions = MagicMock(return_value=MagicMock())
        session.get_session_info()
        session.get_sessions.assert_called_once()


class TestCheckValidSession:
    """Test utils.check_valid_session raises when has_session is False."""

    def test_put_sessions_without_session_raises(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        assert not session.has_session()
        with pytest.raises(exceptions.SessionException, match="no valid session"):
            session.put_sessions()

    def test_get_sessions_without_session_raises(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        with pytest.raises(exceptions.SessionException, match="no valid session"):
            session.get_sessions()

    def test_get_sessions_userinfo_without_session_raises(self):
        session = MSTRRESTSession(base_url=BASE_URL)
        with pytest.raises(exceptions.SessionException, match="no valid session"):
            session.get_sessions_userinfo()
