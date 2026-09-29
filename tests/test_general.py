import pytest

from mstr.requests.compat import MSTRRESTSession
from mstr.requests.rest.exceptions import ResourceNotFoundException

pytestmark = pytest.mark.live


def test_unimplemented_method():
    s = MSTRRESTSession(base_url='https://demo.microstrategy.com/MicroStrategyLibrary/api/')
    s.login()
    with pytest.raises(ResourceNotFoundException):
        s.get('hello/dave')
