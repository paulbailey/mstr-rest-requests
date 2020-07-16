from .session import MSTRRESTSession


class AuthenticatedMSTRRESTSession(MSTRRESTSession):
    def __init__(self, base_url, username=None, password=None):
        super(AuthenticatedMSTRRESTSession, self).__init__(base_url)
        self._username = username
        self._password = password

    def __enter__(self):
        self.login(self._username, self._password)
        return self

    def __exit__(self, t, v, tb):
        self.logout()
