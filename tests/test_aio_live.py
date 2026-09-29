"""Async sessions against the public MicroStrategy demo server (network)."""

import pytest

from mstr.requests import AsyncAuthenticatedMSTRRESTSession, AsyncMSTRRESTSession
from mstr.requests.rest import exceptions

BASE_URL = "https://demo.microstrategy.com/MicroStrategyLibrary/api/"

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_login_session_info_and_logout():
    async with AsyncMSTRRESTSession(base_url=BASE_URL) as session:
        await session.login()
        assert session.has_session() is True
        response = await session.get_session_info()
        assert response.status_code == 200
        await session.logout()
        assert session.has_session() is False
        with pytest.raises(exceptions.SessionException):
            await session.get_session_info()


async def test_context_manager_and_error_translation():
    async with AsyncAuthenticatedMSTRRESTSession(base_url=BASE_URL) as session:
        assert session.has_session() is True
        with pytest.raises(exceptions.ResourceNotFoundException):
            await session.get("hello/dave")
