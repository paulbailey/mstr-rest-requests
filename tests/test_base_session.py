from mstr.requests import MSTRRESTSession


def test_project_id():
    session = MSTRRESTSession(
        base_url="https://demo.microstrategy.com/MicroStrategyLibrary/api/"
    )
    response = session.get("status", project_id="blah")
    assert response.ok
