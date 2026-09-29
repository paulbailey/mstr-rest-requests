"""httpx-based sync sessions against the public MicroStrategy demo server (network)."""

import pytest

from mstr.requests import AuthenticatedMSTRRESTSession, MSTRRESTSession
from mstr.requests.rest import exceptions

BASE_URL = "https://demo.microstrategy.com/MicroStrategyLibrary/api/"


def test_login_session_info_and_logout():
    with MSTRRESTSession(base_url=BASE_URL) as session:
        session.login()
        assert session.has_session() is True
        response = session.get_session_info()
        assert response.status_code == 200
        session.logout()
        assert session.has_session() is False
        with pytest.raises(exceptions.SessionException):
            session.get_session_info()


def test_context_manager_and_error_translation():
    with AuthenticatedMSTRRESTSession(base_url=BASE_URL) as session:
        assert session.has_session() is True
        with pytest.raises(exceptions.ResourceNotFoundException):
            session.get("hello/dave")
