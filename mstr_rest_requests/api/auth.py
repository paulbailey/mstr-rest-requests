class AuthMixin:

    def post_login(self, username=None, password=None):
        if username is not None and password is not None:
            data = {
                'username': username,
                'password': password,
                'loginMode': 1
            }
        else:
            data = {
                'loginMode': 8
            }
        login_response = self.post('auth/login', data=data)
        if login_response.status_code != 204:
            login_response.raise_for_status()
        return login_response

    def post_logout(self):
        logout_response = self.post('auth/logout')
        if logout_response.status_code == 204:
            self.destroy_auth_token()

    # "Friendly" method aliases
    def login(self, username=None, password=None):
        return self.post_login(username, password)

    def logout(self):
        return self.post_logout()
