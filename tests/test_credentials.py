import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from mstr.requests import AuthenticatedMSTRRESTSession, Credential
from mstr.requests.rest.authenticated_session import _resolve


BASE_URL = "https://example.com/api/"


class TestResolve:
    def test_returns_string_unchanged(self):
        assert _resolve("hello") == "hello"

    def test_returns_none_unchanged(self):
        assert _resolve(None) is None

    def test_calls_callable(self):
        provider = MagicMock(return_value="secret")
        assert _resolve(provider) == "secret"
        provider.assert_called_once()


class TestCallableCredentials:
    def _make_session(self, **kwargs):
        session = AuthenticatedMSTRRESTSession(base_url=BASE_URL, **kwargs)
        session.login = MagicMock()
        session.delegate = MagicMock()
        session.logout = MagicMock()
        return session

    def test_plain_strings_still_work(self):
        session = self._make_session(username="user", password="pass")
        session.__enter__()
        session.login.assert_called_once_with(username="user", password="pass", application_type=8)

    def test_callable_username_and_password(self):
        session = self._make_session(
            username=lambda: "lazy_user", password=lambda: "lazy_pass"
        )
        session.__enter__()
        session.login.assert_called_once_with(username="lazy_user", password="lazy_pass", application_type=8)

    def test_callable_api_key(self):
        session = self._make_session(api_key=lambda: "my_key")
        session.__enter__()
        session.login.assert_called_once_with(api_key="my_key", application_type=8)

    def test_callable_identity_token(self):
        session = self._make_session(identity_token=lambda: "my_token")
        session.__enter__()
        session.delegate.assert_called_once_with("my_token")

    def test_callable_identity_token_skips_logout(self):
        session = self._make_session(identity_token=lambda: "my_token")
        session.__enter__()
        session.__exit__(None, None, None)
        session.logout.assert_not_called()

    def test_string_identity_token_skips_logout(self):
        session = self._make_session(identity_token="my_token")
        session.__enter__()
        session.__exit__(None, None, None)
        session.logout.assert_not_called()

    def test_password_auth_calls_logout(self):
        session = self._make_session(username="user", password="pass")
        session.__enter__()
        session.__exit__(None, None, None)
        session.logout.assert_called_once()

    def test_callables_not_invoked_at_init_time(self):
        username_provider = MagicMock(return_value="user")
        password_provider = MagicMock(return_value="pass")
        self._make_session(username=username_provider, password=password_provider)
        username_provider.assert_not_called()
        password_provider.assert_not_called()

    def test_callables_invoked_at_enter_time(self):
        username_provider = MagicMock(return_value="user")
        password_provider = MagicMock(return_value="pass")
        session = self._make_session(
            username=username_provider, password=password_provider
        )
        session.__enter__()
        username_provider.assert_called_once()
        password_provider.assert_called_once()

    def test_anonymous_login_with_no_credentials(self):
        session = self._make_session()
        session.__enter__()
        session.login.assert_called_once_with(username=None, password=None, application_type=8)

    def test_callable_base_url(self):
        session = AuthenticatedMSTRRESTSession(
            base_url=lambda: "https://resolved.example.com/api/",
            username="user",
            password="pass",
        )
        session.login = MagicMock()
        session.logout = MagicMock()
        assert session.base_url != "https://resolved.example.com/api/"
        session.__enter__()
        assert session.base_url == "https://resolved.example.com/api/"

    def test_string_base_url_unchanged(self):
        session = self._make_session()
        assert session.base_url == BASE_URL

    def test_callable_base_url_not_resolved_at_init(self):
        provider = MagicMock(return_value="https://example.com/api/")
        AuthenticatedMSTRRESTSession(base_url=provider)
        provider.assert_not_called()


class TestSecretsManagerHelper:
    def test_returns_callable(self):
        from mstr.requests.credentials.aws import secrets_manager

        provider = secrets_manager("my-secret", key="username")
        assert callable(provider)

    def test_fetches_plain_secret(self):
        from mstr.requests.credentials.aws import secrets_manager

        mock_boto3 = MagicMock()
        mock_client = mock_boto3.client.return_value
        mock_client.get_secret_value.return_value = {"SecretString": "raw_value"}

        provider = secrets_manager("my-secret")
        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            result = provider()

        mock_boto3.client.assert_called_once_with("secretsmanager", region_name=None)
        mock_client.get_secret_value.assert_called_once_with(SecretId="my-secret")
        assert result == "raw_value"

    def test_fetches_json_key(self):
        from mstr.requests.credentials.aws import secrets_manager

        mock_boto3 = MagicMock()
        mock_client = mock_boto3.client.return_value
        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps({"username": "admin", "password": "s3cret"})
        }

        provider = secrets_manager("my-secret", key="password")
        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            result = provider()

        assert result == "s3cret"

    def test_passes_region(self):
        from mstr.requests.credentials.aws import secrets_manager

        mock_boto3 = MagicMock()
        mock_client = mock_boto3.client.return_value
        mock_client.get_secret_value.return_value = {"SecretString": "val"}

        provider = secrets_manager("my-secret", region_name="us-west-2")
        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            provider()

        mock_boto3.client.assert_called_once_with(
            "secretsmanager", region_name="us-west-2"
        )


class TestSecretsManagerSecret:
    def _make_mock_boto3(self, secret_data=None, raw_string=None):
        mock_boto3 = MagicMock()
        mock_client = mock_boto3.client.return_value
        if secret_data is not None:
            mock_client.get_secret_value.return_value = {
                "SecretString": json.dumps(secret_data)
            }
        elif raw_string is not None:
            mock_client.get_secret_value.return_value = {
                "SecretString": raw_string
            }
        return mock_boto3

    def test_field_returns_callable(self):
        from mstr.requests.credentials.aws import SecretsManagerSecret

        secret = SecretsManagerSecret("my-secret")
        provider = secret.field("username")
        assert callable(provider)

    def test_field_resolves_correct_value(self):
        from mstr.requests.credentials.aws import SecretsManagerSecret

        mock_boto3 = self._make_mock_boto3(
            {"username": "admin", "password": "s3cret", "base_url": "https://mstr/api/"}
        )
        secret = SecretsManagerSecret("my-secret")

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            assert secret.field("username")() == "admin"
            assert secret.field("password")() == "s3cret"
            assert secret.field("base_url")() == "https://mstr/api/"

    def test_fetches_only_once(self):
        from mstr.requests.credentials.aws import SecretsManagerSecret

        mock_boto3 = self._make_mock_boto3({"a": "1", "b": "2"})
        mock_client = mock_boto3.client.return_value
        secret = SecretsManagerSecret("my-secret")

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            secret.field("a")()
            secret.field("b")()
            secret.field("a")()

        mock_client.get_secret_value.assert_called_once()

    def test_not_fetched_until_field_called(self):
        from mstr.requests.credentials.aws import SecretsManagerSecret

        mock_boto3 = self._make_mock_boto3({"x": "y"})
        mock_client = mock_boto3.client.return_value
        secret = SecretsManagerSecret("my-secret")
        _ = secret.field("x")

        mock_client.get_secret_value.assert_not_called()

    def test_passes_region(self):
        from mstr.requests.credentials.aws import SecretsManagerSecret

        mock_boto3 = self._make_mock_boto3({"k": "v"})
        secret = SecretsManagerSecret("my-secret", region_name="eu-west-1")

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            secret.field("k")()

        mock_boto3.client.assert_called_once_with(
            "secretsmanager", region_name="eu-west-1"
        )

    def test_missing_key_raises_key_error(self):
        from mstr.requests.credentials.aws import SecretsManagerSecret

        mock_boto3 = self._make_mock_boto3({"username": "admin"})
        secret = SecretsManagerSecret("my-secret")

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            with pytest.raises(KeyError):
                secret.field("nonexistent")()


# ---------------------------------------------------------------------------
# AWS SSM Parameter Store
# ---------------------------------------------------------------------------


class TestParameterStoreHelper:
    def _make_mock_boto3(self, value):
        mock_boto3 = MagicMock()
        mock_client = mock_boto3.client.return_value
        mock_client.get_parameter.return_value = {"Parameter": {"Value": value}}
        return mock_boto3

    def test_returns_callable(self):
        from mstr.requests.credentials.aws import parameter_store

        provider = parameter_store("/app/username")
        assert callable(provider)

    def test_fetches_value(self):
        from mstr.requests.credentials.aws import parameter_store

        mock_boto3 = self._make_mock_boto3("admin")

        provider = parameter_store("/app/username")
        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            result = provider()

        mock_boto3.client.assert_called_once_with("ssm", region_name=None)
        mock_boto3.client.return_value.get_parameter.assert_called_once_with(
            Name="/app/username", WithDecryption=True
        )
        assert result == "admin"

    def test_passes_region(self):
        from mstr.requests.credentials.aws import parameter_store

        mock_boto3 = self._make_mock_boto3("val")

        provider = parameter_store("/app/key", region_name="eu-west-1")
        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            provider()

        mock_boto3.client.assert_called_once_with("ssm", region_name="eu-west-1")


class TestParameterStoreValues:
    def _make_mock_boto3(self, params):
        """params: dict mapping Name -> Value."""
        mock_boto3 = MagicMock()
        mock_client = mock_boto3.client.return_value
        mock_client.get_parameter.side_effect = lambda Name, **kw: {
            "Parameter": {"Value": params[Name]}
        }
        return mock_boto3

    def test_parameter_returns_callable(self):
        from mstr.requests.credentials.aws import ParameterStoreValues

        params = ParameterStoreValues()
        assert callable(params.parameter("/app/user"))

    def test_resolves_values(self):
        from mstr.requests.credentials.aws import ParameterStoreValues

        mock_boto3 = self._make_mock_boto3(
            {"/app/user": "admin", "/app/pass": "s3cret"}
        )
        params = ParameterStoreValues()

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            assert params.parameter("/app/user")() == "admin"
            assert params.parameter("/app/pass")() == "s3cret"

    def test_caches_per_parameter(self):
        from mstr.requests.credentials.aws import ParameterStoreValues

        mock_boto3 = self._make_mock_boto3({"/a": "1", "/b": "2"})
        mock_client = mock_boto3.client.return_value
        params = ParameterStoreValues()

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            params.parameter("/a")()
            params.parameter("/a")()
            params.parameter("/b")()

        assert mock_client.get_parameter.call_count == 2

    def test_not_fetched_until_called(self):
        from mstr.requests.credentials.aws import ParameterStoreValues

        mock_boto3 = self._make_mock_boto3({"/x": "y"})
        mock_client = mock_boto3.client.return_value
        params = ParameterStoreValues()
        _ = params.parameter("/x")

        mock_client.get_parameter.assert_not_called()


# ---------------------------------------------------------------------------
# Azure Key Vault
# ---------------------------------------------------------------------------


class TestKeyVaultHelper:
    def test_returns_callable(self):
        from mstr.requests.credentials.azure import key_vault

        provider = key_vault("https://v.vault.azure.net/", "secret-name")
        assert callable(provider)

    def test_fetches_plain_value(self):
        from mstr.requests.credentials.azure import key_vault

        mock_secret = MagicMock()
        mock_secret.value = "raw_value"
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.get_secret.return_value = mock_secret
        mock_cred_cls = MagicMock()
        mock_identity = MagicMock(**{"DefaultAzureCredential": mock_cred_cls})
        mock_kv = MagicMock(**{"SecretClient": mock_client_cls})

        provider = key_vault("https://v.vault.azure.net/", "my-secret")
        with patch.dict(
            sys.modules,
            {"azure": MagicMock(), "azure.identity": mock_identity, "azure.keyvault": MagicMock(), "azure.keyvault.secrets": mock_kv},
        ):
            result = provider()

        assert result == "raw_value"

    def test_fetches_json_key(self):
        from mstr.requests.credentials.azure import key_vault

        mock_secret = MagicMock()
        mock_secret.value = json.dumps({"user": "admin", "pass": "s3cret"})
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.get_secret.return_value = mock_secret
        mock_cred_cls = MagicMock()
        mock_identity = MagicMock(**{"DefaultAzureCredential": mock_cred_cls})
        mock_kv = MagicMock(**{"SecretClient": mock_client_cls})

        provider = key_vault("https://v.vault.azure.net/", "my-secret", key="pass")
        with patch.dict(
            sys.modules,
            {"azure": MagicMock(), "azure.identity": mock_identity, "azure.keyvault": MagicMock(), "azure.keyvault.secrets": mock_kv},
        ):
            result = provider()

        assert result == "s3cret"

    def test_secret_value_none_raises_value_error(self):
        from mstr.requests.credentials.azure import key_vault

        mock_secret = MagicMock()
        mock_secret.value = None
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.get_secret.return_value = mock_secret
        mock_cred_cls = MagicMock()
        mock_identity = MagicMock(**{"DefaultAzureCredential": mock_cred_cls})
        mock_kv = MagicMock(**{"SecretClient": mock_client_cls})

        provider = key_vault("https://v.vault.azure.net/", "my-secret")
        with patch.dict(
            sys.modules,
            {"azure": MagicMock(), "azure.identity": mock_identity, "azure.keyvault": MagicMock(), "azure.keyvault.secrets": mock_kv},
        ):
            with pytest.raises(ValueError, match="Secret my-secret has no value"):
                provider()


class TestKeyVaultSecret:
    def _patch_azure(self, secret_data):
        mock_secret = MagicMock()
        mock_secret.value = json.dumps(secret_data)
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.get_secret.return_value = mock_secret
        mock_cred_cls = MagicMock()
        mock_identity = MagicMock(**{"DefaultAzureCredential": mock_cred_cls})
        mock_kv = MagicMock(**{"SecretClient": mock_client_cls})
        modules = {
            "azure": MagicMock(),
            "azure.identity": mock_identity,
            "azure.keyvault": MagicMock(),
            "azure.keyvault.secrets": mock_kv,
        }
        return modules, mock_client_cls

    def test_field_returns_callable(self):
        from mstr.requests.credentials.azure import KeyVaultSecret

        secret = KeyVaultSecret("https://v.vault.azure.net/", "s")
        assert callable(secret.field("k"))

    def test_field_resolves_value(self):
        from mstr.requests.credentials.azure import KeyVaultSecret

        modules, _ = self._patch_azure({"user": "admin", "pass": "pw"})
        secret = KeyVaultSecret("https://v.vault.azure.net/", "s")

        with patch.dict(sys.modules, modules):
            assert secret.field("user")() == "admin"
            assert secret.field("pass")() == "pw"

    def test_fetches_only_once(self):
        from mstr.requests.credentials.azure import KeyVaultSecret

        modules, mock_client_cls = self._patch_azure({"a": "1", "b": "2"})
        secret = KeyVaultSecret("https://v.vault.azure.net/", "s")

        with patch.dict(sys.modules, modules):
            secret.field("a")()
            secret.field("b")()

        mock_client_cls.return_value.get_secret.assert_called_once()

    def test_not_fetched_until_field_called(self):
        from mstr.requests.credentials.azure import KeyVaultSecret

        modules, mock_client_cls = self._patch_azure({"x": "y"})
        secret = KeyVaultSecret("https://v.vault.azure.net/", "s")
        _ = secret.field("x")

        mock_client_cls.return_value.get_secret.assert_not_called()

    def test_secret_value_none_raises_value_error(self):
        from mstr.requests.credentials.azure import KeyVaultSecret

        mock_secret = MagicMock()
        mock_secret.value = None
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.get_secret.return_value = mock_secret
        mock_cred_cls = MagicMock()
        mock_identity = MagicMock(**{"DefaultAzureCredential": mock_cred_cls})
        mock_kv = MagicMock(**{"SecretClient": mock_client_cls})
        modules = {
            "azure": MagicMock(),
            "azure.identity": mock_identity,
            "azure.keyvault": MagicMock(),
            "azure.keyvault.secrets": mock_kv,
        }
        secret = KeyVaultSecret("https://v.vault.azure.net/", "s")
        with patch.dict(sys.modules, modules):
            with pytest.raises(ValueError, match="Secret s has no value"):
                secret.field("k")()


# ---------------------------------------------------------------------------
# GCP Secret Manager
# ---------------------------------------------------------------------------


class TestGCPSecretManagerHelper:
    def _make_mock_gcp(self, payload_str):
        mock_sm = MagicMock()
        mock_client = mock_sm.SecretManagerServiceClient.return_value
        mock_response = MagicMock()
        mock_response.payload.data = payload_str.encode("UTF-8")
        mock_client.access_secret_version.return_value = mock_response
        return mock_sm, mock_client

    def test_returns_callable(self):
        from mstr.requests.credentials.gcp import secret_manager

        provider = secret_manager("proj", "secret-id")
        assert callable(provider)

    def test_fetches_plain_value(self):
        from mstr.requests.credentials.gcp import secret_manager

        mock_sm, mock_client = self._make_mock_gcp("raw_value")

        provider = secret_manager("proj", "secret-id")
        with patch.dict(
            sys.modules,
            {"google": MagicMock(), "google.cloud": MagicMock(), "google.cloud.secretmanager": mock_sm},
        ):
            result = provider()

        mock_client.access_secret_version.assert_called_once_with(
            name="projects/proj/secrets/secret-id/versions/latest"
        )
        assert result == "raw_value"

    def test_fetches_json_key(self):
        from mstr.requests.credentials.gcp import secret_manager

        mock_sm, _ = self._make_mock_gcp(json.dumps({"user": "admin"}))

        provider = secret_manager("proj", "secret-id", key="user")
        with patch.dict(
            sys.modules,
            {"google": MagicMock(), "google.cloud": MagicMock(), "google.cloud.secretmanager": mock_sm},
        ):
            result = provider()

        assert result == "admin"

    def test_custom_version(self):
        from mstr.requests.credentials.gcp import secret_manager

        mock_sm, mock_client = self._make_mock_gcp("v")

        provider = secret_manager("proj", "secret-id", version="42")
        with patch.dict(
            sys.modules,
            {"google": MagicMock(), "google.cloud": MagicMock(), "google.cloud.secretmanager": mock_sm},
        ):
            provider()

        mock_client.access_secret_version.assert_called_once_with(
            name="projects/proj/secrets/secret-id/versions/42"
        )


class TestGCPSecretManagerSecret:
    def _make_mock_gcp(self, secret_data):
        mock_sm = MagicMock()
        mock_client = mock_sm.SecretManagerServiceClient.return_value
        mock_response = MagicMock()
        mock_response.payload.data = json.dumps(secret_data).encode("UTF-8")
        mock_client.access_secret_version.return_value = mock_response
        return mock_sm, mock_client

    def _gcp_modules(self, mock_sm):
        return {
            "google": MagicMock(),
            "google.cloud": MagicMock(),
            "google.cloud.secretmanager": mock_sm,
        }

    def test_field_returns_callable(self):
        from mstr.requests.credentials.gcp import SecretManagerSecret

        secret = SecretManagerSecret("proj", "secret-id")
        assert callable(secret.field("k"))

    def test_field_resolves_value(self):
        from mstr.requests.credentials.gcp import SecretManagerSecret

        mock_sm, _ = self._make_mock_gcp({"user": "admin", "pass": "pw"})
        secret = SecretManagerSecret("proj", "secret-id")

        with patch.dict(sys.modules, self._gcp_modules(mock_sm)):
            assert secret.field("user")() == "admin"
            assert secret.field("pass")() == "pw"

    def test_fetches_only_once(self):
        from mstr.requests.credentials.gcp import SecretManagerSecret

        mock_sm, mock_client = self._make_mock_gcp({"a": "1", "b": "2"})
        secret = SecretManagerSecret("proj", "secret-id")

        with patch.dict(sys.modules, self._gcp_modules(mock_sm)):
            secret.field("a")()
            secret.field("b")()

        mock_client.access_secret_version.assert_called_once()

    def test_not_fetched_until_field_called(self):
        from mstr.requests.credentials.gcp import SecretManagerSecret

        mock_sm, mock_client = self._make_mock_gcp({"x": "y"})
        secret = SecretManagerSecret("proj", "secret-id")
        _ = secret.field("x")

        mock_client.access_secret_version.assert_not_called()

    def test_missing_key_raises_key_error(self):
        from mstr.requests.credentials.gcp import SecretManagerSecret

        mock_sm, _ = self._make_mock_gcp({"username": "admin"})
        secret = SecretManagerSecret("proj", "secret-id")

        with patch.dict(sys.modules, self._gcp_modules(mock_sm)):
            with pytest.raises(KeyError):
                secret.field("nonexistent")()
