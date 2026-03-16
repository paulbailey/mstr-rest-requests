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

"""Azure Key Vault credential providers.

Requires ``azure-identity`` and ``azure-keyvault-secrets``, which are
installed automatically with the ``azure`` extra::

    pip install mstr-rest-requests[azure]

Two helpers are provided:

* :func:`key_vault` -- returns a single-value callable for one Key Vault
  secret.
* :class:`KeyVaultSecret` -- wraps a JSON-valued Key Vault secret containing
  multiple fields and caches the fetch so that all fields share a single API
  call.
"""

import json
from collections.abc import Callable
from typing import cast


def _fetch_key_vault_value(
    vault_url: str, secret_name: str, key: str | None = None
) -> str:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient

    client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
    secret_value = client.get_secret(secret_name).value
    if secret_value is None:
        raise ValueError(f"Secret {secret_name} has no value")
    if key is not None:
        return cast(str, json.loads(secret_value)[key])
    return secret_value


def key_vault(
    vault_url: str, secret_name: str, key: str | None = None
) -> Callable[[], str]:
    """Return a callable that fetches a value from Azure Key Vault when invoked.

    The returned callable takes no arguments and returns a string.
    ``azure-identity`` and ``azure-keyvault-secrets`` are imported lazily so
    they only need to be installed when the callable is actually called.

    Authentication uses :class:`~azure.identity.DefaultAzureCredential`,
    which supports managed identity, environment variables, Azure CLI, and
    other methods automatically.

    Args:
        vault_url: The vault URL, e.g. ``"https://my-vault.vault.azure.net/"``.
        secret_name: Name of the secret within the vault.
        key: If the secret value is a JSON object, extract this key.
            When ``None`` the raw secret string is returned.
    """

    def _fetch() -> str:
        return _fetch_key_vault_value(vault_url, secret_name, key)

    return _fetch


class KeyVaultSecret:
    """A single Key Vault secret containing multiple JSON fields.

    The secret is fetched lazily on the first ``.field()`` resolution and
    cached so that all fields share one API call.  Each ``.field(key)`` call
    returns a zero-argument callable compatible with
    :data:`~mstr.requests.rest.authenticated_session.Credential`.

    Example::

        secret = KeyVaultSecret(
            "https://my-vault.vault.azure.net/", "my-mstr-secret"
        )

        with AuthenticatedMSTRRESTSession(
            base_url=secret.field("base_url"),
            username=secret.field("username"),
            password=secret.field("password"),
        ) as session:
            ...

    Args:
        vault_url: The vault URL.
        secret_name: Name of the secret within the vault.
    """

    def __init__(self, vault_url: str, secret_name: str):
        self._vault_url = vault_url
        self._secret_name = secret_name
        self._cache: dict[str, str] | None = None

    def _fetch(self) -> dict[str, str]:
        if self._cache is None:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            client = SecretClient(
                vault_url=self._vault_url,
                credential=DefaultAzureCredential(),
            )
            raw = client.get_secret(self._secret_name).value
            if raw is None:
                raise ValueError(f"Secret {self._secret_name} has no value")
            self._cache = json.loads(raw)
        return self._cache

    def field(self, key: str) -> Callable[[], str]:
        """Return a callable that resolves to the value of *key* in this secret."""

        def _get_field() -> str:
            return self._fetch()[key]

        return _get_field
