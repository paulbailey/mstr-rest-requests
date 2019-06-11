from mstr.requests.rest.exceptions import SessionException


def check_valid_session(f, *args, **kwargs):
    def check(self, *args, **kwargs):
        if self.has_session():
            return f(self, *args, **kwargs)
        else:
            raise SessionException('There is no valid session available.')
    return check
