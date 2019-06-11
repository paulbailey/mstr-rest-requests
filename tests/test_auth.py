from mstr.requests import MSTRRESTSession
from mstr.requests.rest import exceptions

import pytest


@pytest.fixture(scope="function")
def session():
    return MSTRRESTSession(base_url='https://demo.microstrategy.com/MicroStrategyLibrary/api/')


@pytest.fixture(scope="function")
def logged_in_session():
    session = MSTRRESTSession(base_url='https://demo.microstrategy.com/MicroStrategyLibrary/api/')
    session.login()
    assert session.has_session() is True
    yield session
    session.logout()


def test_login(session):
    assert session.has_session() is False
    session.login()
    assert session.has_session() is True
    session.logout()
    assert session.has_session() is False


def test_prolong_session(logged_in_session):
    response = logged_in_session.put_sessions()
    assert response.status_code == 204


def test_get_session_status(logged_in_session):
    response = logged_in_session.get_sessions()
    assert response.status_code == 200


def test_get_session_failure(session):
    session.login()
    assert session.has_session() is True
    session.logout()
    with pytest.raises(exceptions.SessionException):
        session.get_sessions()


def test_remote_session_issue(logged_in_session):
    logged_in_session.headers.update({'x-mstr-authtoken': "You're my wife now"})
    with pytest.raises(exceptions.MSTRException):
        logged_in_session.get_sessions()
