import pytest

from src.mstr_rest_requests import MSTRRESTSession
from src.mstr_rest_requests.exceptions import ResourceNotFoundException


def test_unimplemented_method():
    s = MSTRRESTSession(base_url='https://demo.microstrategy.com/MicroStrategyLibrary/api/')
    s.login()
    with pytest.raises(ResourceNotFoundException):
        s.get('hello/dave')
