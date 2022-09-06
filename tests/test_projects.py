from mstr.requests import AuthenticatedMSTRRESTSession


def test_list_projects():
    with AuthenticatedMSTRRESTSession(
        base_url="https://demo.microstrategy.com/MicroStrategyLibrary/api/"
    ) as session:
        projects = session.get_projects()
        assert projects
