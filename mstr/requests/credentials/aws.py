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

"""AWS credential providers for Secrets Manager and SSM Parameter Store.

Requires ``boto3``, which is installed automatically with the ``aws`` extra::

    pip install mstr-rest-requests[aws]

Secrets Manager
~~~~~~~~~~~~~~~

* :func:`secrets_manager` -- returns a single-value callable, suitable when
  each secret holds one credential or you need to extract a single key from
  a JSON secret.
* :class:`SecretsManagerSecret` -- wraps a JSON secret containing multiple
  fields and caches the fetch so that all fields share a single API call.

SSM Parameter Store
~~~~~~~~~~~~~~~~~~~

* :func:`parameter_store` -- returns a single-value callable for one SSM
  parameter.
* :class:`ParameterStoreValues` -- groups several parameter paths and caches
  each fetch so that repeated resolutions of the same parameter do not make
  extra API calls.
"""

import json
from collections.abc import Callable
from functools import partial


def _fetch_secret_value(
    secret_id: str, key: str | None = None, region_name: str | None = None
) -> str:
    import boto3

    client = boto3.client("secretsmanager", region_name=region_name)
    response = client.get_secret_value(SecretId=secret_id)
    secret_string = response["SecretString"]
    if key is not None:
        return json.loads(secret_string)[key]
    return secret_string


def secrets_manager(
    secret_id: str, key: str | None = None, region_name: str | None = None
) -> Callable[[], str]:
    """Return a callable that fetches a value from AWS Secrets Manager when invoked.

    The returned callable takes no arguments and returns a string. ``boto3`` is
    imported lazily so it only needs to be installed when the callable is
    actually called.

    Args:
        secret_id: The ARN or name of the secret.
        key: If the secret value is a JSON object, extract this key.
            When ``None`` the raw ``SecretString`` is returned.
        region_name: AWS region override. When ``None`` the default
            boto3 session region is used.
    """
    return partial(_fetch_secret_value, secret_id, key, region_name)


class SecretsManagerSecret:
    """A single Secrets Manager secret containing multiple fields.

    The secret is fetched lazily on the first ``.field()`` resolution and
    cached so that all fields share one API call.  Each ``.field(key)`` call
    returns a zero-argument callable compatible with
    :data:`~mstr.requests.rest.authenticated_session.Credential`.

    Example::

        secret = SecretsManagerSecret("my-secret-id")

        with AuthenticatedMSTRRESTSession(
            base_url=secret.field("base_url"),
            username=secret.field("username"),
            password=secret.field("password"),
        ) as session:
            ...

    Args:
        secret_id: The ARN or name of the secret.
        region_name: AWS region override.  When ``None`` the default
            boto3 session region is used.
    """

    def __init__(self, secret_id: str, region_name: str | None = None):
        self._secret_id = secret_id
        self._region_name = region_name
        self._cache: dict[str, str] | None = None

    def _fetch(self) -> dict[str, str]:
        if self._cache is None:
            import boto3

            client = boto3.client("secretsmanager", region_name=self._region_name)
            response = client.get_secret_value(SecretId=self._secret_id)
            self._cache = json.loads(response["SecretString"])
        return self._cache

    def field(self, key: str) -> Callable[[], str]:
        """Return a callable that resolves to the value of *key* in this secret."""

        def _get_field() -> str:
            return self._fetch()[key]

        return _get_field


# ---------------------------------------------------------------------------
# SSM Parameter Store
# ---------------------------------------------------------------------------


def _fetch_parameter_value(
    name: str, region_name: str | None = None
) -> str:
    import boto3

    client = boto3.client("ssm", region_name=region_name)
    response = client.get_parameter(Name=name, WithDecryption=True)
    return response["Parameter"]["Value"]


def parameter_store(
    name: str, region_name: str | None = None
) -> Callable[[], str]:
    """Return a callable that fetches an SSM Parameter Store value when invoked.

    The returned callable takes no arguments and returns a string.
    ``boto3`` is imported lazily so it only needs to be installed when the
    callable is actually called.  Parameters are always fetched with
    decryption enabled so that ``SecureString`` parameters are returned in
    plain text.

    Args:
        name: The name or ARN of the parameter.
        region_name: AWS region override.  When ``None`` the default
            boto3 session region is used.
    """
    return partial(_fetch_parameter_value, name, region_name)


class ParameterStoreValues:
    """A group of SSM Parameter Store parameters that share a cache.

    Each :meth:`parameter` call returns a zero-argument callable compatible
    with :data:`~mstr.requests.rest.authenticated_session.Credential`.
    Parameters are fetched individually on first resolution and cached so
    that subsequent resolutions of the same name do not make extra API
    calls.

    Example::

        params = ParameterStoreValues()

        with AuthenticatedMSTRRESTSession(
            base_url=params.parameter("/myapp/base_url"),
            username=params.parameter("/myapp/username"),
            password=params.parameter("/myapp/password"),
        ) as session:
            ...

    Args:
        region_name: AWS region override.  When ``None`` the default
            boto3 session region is used.
    """

    def __init__(self, region_name: str | None = None):
        self._region_name = region_name
        self._cache: dict[str, str] = {}

    def _fetch(self, name: str) -> str:
        if name not in self._cache:
            import boto3

            client = boto3.client("ssm", region_name=self._region_name)
            response = client.get_parameter(Name=name, WithDecryption=True)
            self._cache[name] = response["Parameter"]["Value"]
        return self._cache[name]

    def parameter(self, name: str) -> Callable[[], str]:
        """Return a callable that resolves to the value of the parameter *name*."""

        def _get_parameter() -> str:
            return self._fetch(name)

        return _get_parameter
