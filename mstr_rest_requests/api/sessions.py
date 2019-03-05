from ..exceptions import SessionException


class SessionsMixin:

    def put_sessions(self):
        if self.has_session():
            self.put('sessions')
        else:
            raise SessionException('There is no session to extend.')

    def extend_session(self):
        self.put_sessions()
