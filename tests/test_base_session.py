import pytest

from mstr.requests.compat import MSTRRESTSession

pytestmark = pytest.mark.live


def test_project_id():
    session = MSTRRESTSession(
        base_url="https://demo.microstrategy.com/MicroStrategyLibrary/api/"
    )
    response = session.get("status", project_id="blah")
    assert response.ok
