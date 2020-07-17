class AuthMixin:
    def post_login(self, username=None, password=None):
        """``POST``s a login request."""
        if username is not None and password is not None:
            data = {"username": username, "password": password, "loginMode": 1}
        else:
            data = {"loginMode": 8}
        login_response = self.post("auth/login", json=data)
        if login_response.status_code != 204:
            login_response.raise_for_status()
        return login_response

    def post_logout(self):
        logout_response = self.post("auth/logout")
        if logout_response.status_code == 204:
            self.destroy_auth_token()

    # "Friendly" method aliases
    def login(self, username: str = None, password: str = None):
        """Logs in to MicroStrategy REST API.
        
        These credentials must be using MicroStrategy's standard authentication. 
        
        If no credentials are provided, the session will attempt to establish an anonymous connection.

        Returns:
            A ``requests`` response object with result of the login request
        """
        return self.post_login(username, password)

    def logout(self):
        """Closes the REST API session associated with the session object."""
        return self.post_logout()
