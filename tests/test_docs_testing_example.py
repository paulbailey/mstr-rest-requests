"""The example in docs/usage/testing.rst, which includes this file."""

import httpx

from mstr.requests import AuthenticatedMSTRRESTSession


# The code under test: something in your application that uses the library.
def project_names(session: AuthenticatedMSTRRESTSession) -> list[str]:
    return sorted(project["name"] for project in session.get_projects())


# A fake MicroStrategy server: a function that turns a request into a response.
def fake_server(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/auth/login"):
        return httpx.Response(204, headers={"X-MSTR-AuthToken": "test-token"})
    if request.url.path.endswith("/auth/logout"):
        return httpx.Response(204)
    if request.url.path.endswith("/projects"):
        assert request.headers["X-MSTR-AuthToken"] == "test-token"
        return httpx.Response(
            200, json=[{"id": "P2", "name": "Sales"}, {"id": "P1", "name": "HR"}]
        )
    return httpx.Response(
        404, json={"code": "ERR004", "message": f"No fake for {request.url.path}"}
    )


def test_project_names():
    with AuthenticatedMSTRRESTSession(
        base_url="https://mstr.test/api/",
        username="dave",
        password="hellodave",
        transport=httpx.MockTransport(fake_server),
    ) as session:
        assert project_names(session) == ["HR", "Sales"]
