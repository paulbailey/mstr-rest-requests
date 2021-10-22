# -*- coding: utf-8 -*-
# Copyright 2020 Paul Bailey
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        https://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from .errors import iserver_error_codes


class MSTRException(Exception):
    def __init__(self, message: str = None, *args, **kwargs):
        self.code = kwargs.get("code", "N/A")
        self.message = "{}: {}.".format(self.code, message)
        self.iserver_code = kwargs.get("iServerCode", None)
        if self.iserver_code:
            self.iserver_message = iserver_error_codes.get(self.iserver_code)
            self.message += "  [I-Server error code {} ({})]".format(
                self.iserver_message, self.iserver_code
            )
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
