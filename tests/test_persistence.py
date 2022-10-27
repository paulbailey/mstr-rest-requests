from mstr.requests import AuthenticatedMSTRRESTSession
from mstr.requests import MSTRRESTSession


def test_dict_methods():
    with AuthenticatedMSTRRESTSession(
        base_url="https://demo.microstrategy.com/MicroStrategyLibrary/api/"
    ) as session:
        deets = session.dict()
        assert "base_url" in deets
        session2 = MSTRRESTSession.from_dict(deets)
        assert session2.has_session()
        assert isinstance(session2, MSTRRESTSession)
