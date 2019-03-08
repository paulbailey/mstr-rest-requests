from mstr_rest_requests import MSTRRESTSession
from mstr_rest_requests import exceptions

import pytest


@pytest.fixture()
def session():
    return MSTRRESTSession(base_url='https://demo.microstrategy.com/MicroStrategyLibrary/api/')


def test_login(session):
    assert session.has_session() is False
    session.login()
    assert session.has_session() is True
    session.logout()
    assert session.has_session() is False


def test_prolong_session(session):
    session.login()
    assert session.has_session() is True
    response = session.put_sessions()
    assert response.status_code == 204
    session.logout()


def test_get_session_status(session):
    session.login()
    assert session.has_session() is True
    response = session.get_sessions()
    assert response.status_code == 200
    session.logout()


def test_get_session_failure(session):
    session.login()
    assert session.has_session() is True
    session.logout()
    with pytest.raises(exceptions.SessionException):
        session.get_sessions()


def test_remote_session_issue(session):
    session.login()
    assert session.has_session() is True
    session.headers.update({'x-mstr-authtoken': "You're my wife now"})
    with pytest.raises(exceptions.MSTRException):
        session.get_sessions()
