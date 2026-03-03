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

"""Credential provider helpers for :class:`~mstr.requests.AuthenticatedMSTRRESTSession`.

Each submodule targets a specific secrets backend.  Install the
corresponding package extra to pull in the required dependencies:

* :mod:`~mstr.requests.credentials.aws` -- AWS Secrets Manager and SSM
  Parameter Store (``pip install mstr-rest-requests[aws]``).
* :mod:`~mstr.requests.credentials.azure` -- Azure Key Vault
  (``pip install mstr-rest-requests[azure]``).
* :mod:`~mstr.requests.credentials.gcp` -- Google Cloud Secret Manager
  (``pip install mstr-rest-requests[gcp]``).
"""

from mstr.requests.rest.authenticated_session import Credential

__all__ = ["Credential"]
