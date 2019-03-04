from mstr_rest_requests import MSTRRESTSession
from mstr_rest_requests import exceptions

import pytest


TEST_BASE_URL = 'https://demo.microstrategy.com/MicroStrategyLibrary/api/'


def test_login():
    s = MSTRRESTSession(base_url=TEST_BASE_URL)
    assert s.has_session() is False
    s.login()
    assert s.has_session() is True
    s.logout()
    assert s.has_session() is False


def test_prolong_session():
    s = MSTRRESTSession(base_url=TEST_BASE_URL)
    s.login()
    assert s.has_session() is True
    response = s.put('sessions')
    assert response.status_code == 204
    s.logout()


def test_get_session_status():
    s = MSTRRESTSession(base_url=TEST_BASE_URL)
    s.login()
    assert s.has_session() is True
    response = s.get('sessions')
    assert response.status_code == 200
    s.logout()


def test_get_session_failure():
    s = MSTRRESTSession(base_url=TEST_BASE_URL)
    s.login()
    assert s.has_session() is True
    s.post('auth/logout')
    with pytest.raises(exceptions.LoginFailureException):
        s.get('sessions')
