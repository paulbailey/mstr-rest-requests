from .utils import check_valid_session


class SessionsMixin:

    @check_valid_session
    def put_sessions(self):
        return self.put('sessions')

    @check_valid_session
    def get_sessions_userinfo(self):
        return self.get('sessions/userInfo')

    @check_valid_session
    def get_sessions(self):
        return self.get('sessions')

    # "Friendly" method aliases
    def extend_session(self):
        return self.put_sessions()

    def get_userinfo(self):
        return self.get_sessions_userinfo()

    def get_session_info(self):
        return self.get_sessions()

