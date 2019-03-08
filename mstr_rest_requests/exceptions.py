from .errors import iserver_error_codes


class MSTRException(Exception):
    def __init__(self, message=None, *args, **kwargs):
        self.code = kwargs.get('code', 'N/A')
        self.message = "{}: {}.".format(self.code, message)
        self.iserver_code = kwargs.get('iServerCode', None)
        if self.iserver_code:
            self.iserver_message = iserver_error_codes.get(self.iserver_code)
            self.message += "  [I-Server error code {} ({})]".format(self.iserver_message, self.iserver_code)
        super().__init__(self.message, *args)


class LoginFailureException(MSTRException):
    pass


class SessionException(MSTRException):
    pass


class ExecutionCancelledException(MSTRException):
    pass


class MSTRUnknownException(MSTRException):
    pass


class ExecutionFailedException(MSTRException):
    pass


class ResourceNotFoundException(MSTRException):
    pass
