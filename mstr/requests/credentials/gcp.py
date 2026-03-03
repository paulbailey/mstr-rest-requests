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

"""Google Cloud Secret Manager credential providers.

Requires ``google-cloud-secret-manager``, which is installed automatically
with the ``gcp`` extra::

    pip install mstr-rest-requests[gcp]

Two helpers are provided:

* :func:`secret_manager` -- returns a single-value callable for one secret
  version.
* :class:`SecretManagerSecret` -- wraps a JSON-valued secret containing
  multiple fields and caches the fetch so that all fields share a single API
  call.
"""

import json
from typing import Callable, Dict, Optional


def _build_secret_version_name(
    project: str, secret_id: str, version: str = "latest"
) -> str:
    return f"projects/{project}/secrets/{secret_id}/versions/{version}"


def _fetch_secret_value(
    project: str,
    secret_id: str,
    version: str = "latest",
    key: Optional[str] = None,
) -> str:
    from google.cloud.secretmanager import SecretManagerServiceClient

    client = SecretManagerServiceClient()
    name = _build_secret_version_name(project, secret_id, version)
    response = client.access_secret_version(name=name)
    payload = response.payload.data.decode("UTF-8")
    if key is not None:
        return json.loads(payload)[key]
    return payload


def secret_manager(
    project: str,
    secret_id: str,
    version: str = "latest",
    key: Optional[str] = None,
) -> Callable[[], str]:
    """Return a callable that fetches a value from GCP Secret Manager when invoked.

    The returned callable takes no arguments and returns a string.
    ``google-cloud-secret-manager`` is imported lazily so it only needs to
    be installed when the callable is actually called.

    Authentication uses Application Default Credentials (ADC).

    Args:
        project: GCP project ID or number.
        secret_id: Name of the secret.
        version: Secret version (default ``"latest"``).
        key: If the secret payload is a JSON object, extract this key.
            When ``None`` the raw payload string is returned.
    """

    def _fetch() -> str:
        return _fetch_secret_value(project, secret_id, version, key)

    return _fetch


class SecretManagerSecret:
    """A single GCP Secret Manager secret containing multiple JSON fields.

    The secret is fetched lazily on the first ``.field()`` resolution and
    cached so that all fields share one API call.  Each ``.field(key)`` call
    returns a zero-argument callable compatible with
    :data:`~mstr.requests.rest.authenticated_session.Credential`.

    Example::

        secret = SecretManagerSecret("my-gcp-project", "my-mstr-secret")

        with AuthenticatedMSTRRESTSession(
            base_url=secret.field("base_url"),
            username=secret.field("username"),
            password=secret.field("password"),
        ) as session:
            ...

    Args:
        project: GCP project ID or number.
        secret_id: Name of the secret.
        version: Secret version (default ``"latest"``).
    """

    def __init__(
        self, project: str, secret_id: str, version: str = "latest"
    ):
        self._project = project
        self._secret_id = secret_id
        self._version = version
        self._cache: Optional[Dict[str, str]] = None

    def _fetch(self) -> Dict[str, str]:
        if self._cache is None:
            from google.cloud.secretmanager import SecretManagerServiceClient

            client = SecretManagerServiceClient()
            name = _build_secret_version_name(
                self._project, self._secret_id, self._version
            )
            response = client.access_secret_version(name=name)
            self._cache = json.loads(response.payload.data.decode("UTF-8"))
        return self._cache

    def field(self, key: str) -> Callable[[], str]:
        """Return a callable that resolves to the value of *key* in this secret."""

        def _get_field() -> str:
            return self._fetch()[key]

        return _get_field
