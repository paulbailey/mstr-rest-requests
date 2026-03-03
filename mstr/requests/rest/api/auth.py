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
    """Mixin providing MicroStrategy REST API authentication methods."""

    def post_login(
        self, username: str = None, password: str = None, application_type: int = 8
    ):
        """Create an authenticated session via ``POST /auth/login``.

        The *login mode* is inferred from which arguments are supplied:

        * ``username`` **and** ``password`` -- standard auth (mode 1).
        * ``username`` only -- trusted / API-key auth (mode 4096).
        * Neither -- anonymous auth (mode 8).

        Args:
            username: MicroStrategy username or API key.
            password: Password for standard authentication.
            application_type: MicroStrategy application type identifier.

        Returns:
            A :class:`requests.Response` for the login request.

        Raises:
            requests.HTTPError: If the server returns a non-204 status.
        """
        if username is not None and password is not None:
            data = {
                "username": username,
                "password": password,
                "loginMode": 1,
                "applicationType": application_type,
            }
        elif username is not None and password is None:
            data = {
                "username": username,
                "loginMode": 4096,
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
        """Close the session via ``POST /auth/logout``.

        On success the auth token is removed from the session headers.
        """
        logout_response = self.post("auth/logout")
        if logout_response.status_code == 204:
            self.destroy_auth_token()

    def login(
        self, username: str = None, password: str = None, application_type: int = 8
    ):
        """Log in to the MicroStrategy REST API.

        Convenience alias for :meth:`post_login`.  If no credentials are
        provided the session attempts an anonymous connection.

        Args:
            username: MicroStrategy username or API key.
            password: Password for standard authentication.
            application_type: MicroStrategy application type identifier.

        Returns:
            A :class:`requests.Response` for the login request.
        """
        return self.post_login(username, password, application_type)

    def logout(self):
        """Log out and close the current REST API session.

        Convenience alias for :meth:`post_logout`.
        """
        return self.post_logout()

    def delegate(self, identity_token: str):
        """Authenticate with a delegated identity token via ``POST /auth/delegate``.

        Args:
            identity_token: A valid MicroStrategy identity token.

        Returns:
            A :class:`requests.Response` for the delegate request.

        Raises:
            requests.HTTPError: If the server returns a non-204 status.
        """
        delegate_response = self.post(
            "auth/delegate", json={"loginMode": -1, "identityToken": identity_token}
        )
        if delegate_response.status_code != 204:
            delegate_response.raise_for_status()
        return delegate_response
