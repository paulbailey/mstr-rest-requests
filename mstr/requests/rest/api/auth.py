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


class AuthMixin:
    def post_login(
        self, username: str = None, password: str = None, application_type: int = 8
    ):
        """``POST``s a login request."""
        if username is not None and password is not None:
            data = {
                "username": username,
                "password": password,
                "loginMode": 1,
                "applicationType": application_type,
            }
        else:
            data = {
                "loginMode": 8,
                "applicationType": application_type,
            }
        login_response = self.post("auth/login", json=data)
        if login_response.status_code != 204:
            login_response.raise_for_status()
        return login_response

    def post_logout(self):
        logout_response = self.post("auth/logout")
        if logout_response.status_code == 204:
            self.destroy_auth_token()

    # "Friendly" method aliases
    def login(
        self, username: str = None, password: str = None, application_type: int = 8
    ):
        """Logs in to MicroStrategy REST API.

        These credentials must be using MicroStrategy's standard authentication.

        If no credentials are provided, the session will attempt to establish an anonymous connection.

        Returns:
            A ``requests`` response object with result of the login request
        """
        return self.post_login(username, password, application_type)

    def logout(self):
        """Closes the REST API session associated with the session object."""
        return self.post_logout()

    def delegate(self, identity_token: str):
        delegate_response = self.post(
            "auth/delegate", json={"loginMode": -1, "identityToken": identity_token}
        )
        if delegate_response.status_code != 204:
            delegate_response.raise_for_status()
        return delegate_response
