Authentication
==============

Four authentication modes are supported. Each can be used with
:class:`~mstr.requests.AuthenticatedMSTRRESTSession`, which logs in for you,
or with :meth:`~mstr.requests.MSTRRESTSession.login` and
:meth:`~mstr.requests.MSTRRESTSession.delegate` on a plain
:class:`~mstr.requests.MSTRRESTSession`.

Standard (username and password)
--------------------------------

.. code-block:: python

   with AuthenticatedMSTRRESTSession(
       base_url="https://your-server/MicroStrategyLibrary/api/",
       username="dave",
       password="hellodave",
   ) as session:
       ...

   # or
   session.login(username="dave", password="hellodave")

Identity token (delegation)
---------------------------

.. code-block:: python

   with AuthenticatedMSTRRESTSession(
       base_url="https://your-server/MicroStrategyLibrary/api/",
       identity_token="supersecretidentitytoken",
   ) as session:
       ...

   # or
   session.delegate(identity_token="supersecretidentitytoken")

A session created from an identity token is not logged out when the ``with``
block ends, because the token's owner controls its lifetime.

To hand a session's user to another process without sharing credentials,
create an identity token from a logged-in session:

.. code-block:: python

   token = session.create_identity_token()

The other process passes it as ``identity_token=`` and gets its own session
as the same user.

API key (trusted authentication)
--------------------------------

.. code-block:: python

   with AuthenticatedMSTRRESTSession(
       base_url="https://your-server/MicroStrategyLibrary/api/",
       api_key="your-api-key",
   ) as session:
       ...

   # or
   session.login(api_key="your-api-key")

Anonymous
---------

Pass no credentials:

.. code-block:: python

   with AuthenticatedMSTRRESTSession(
       base_url="https://your-server/MicroStrategyLibrary/api/",
   ) as session:
       ...

   # or
   session.login()

If you pass more than one kind of credential to
:class:`~mstr.requests.AuthenticatedMSTRRESTSession`, an identity token wins
over an API key, which wins over a username and password.

Credentials from functions
--------------------------

Every credential argument of
:class:`~mstr.requests.AuthenticatedMSTRRESTSession`, including ``base_url``,
takes either a string or a function with no arguments that returns one (the
:data:`~mstr.requests.Credential` type). Functions are called when the
``with`` block starts, not when the session is created, so secrets are read
only when they are needed:

.. code-block:: python

   import os

   with AuthenticatedMSTRRESTSession(
       base_url=lambda: os.environ["MSTR_URL"],
       username=lambda: os.environ["MSTR_USER"],
       password=get_password_from_somewhere,
   ) as session:
       ...

If a credential you passed resolves to ``None``, for example because a
function reads an unset environment variable, the session raises
:class:`~mstr.requests.rest.exceptions.MissingCredentialException` before it
contacts the server, rather than falling back to another login mode.

The async sessions also accept ``async def`` functions; see :doc:`async`.

.. _long-running-jobs:

Long-running jobs
-----------------

Sessions time out on the server after a period without requests. Two options
on :class:`~mstr.requests.AuthenticatedMSTRRESTSession` and
:class:`~mstr.requests.AsyncAuthenticatedMSTRRESTSession` help long jobs:

* ``relogin=True``: when a request fails because the session has expired
  (``ERR009``), the session resolves its credentials again, logs in again and
  sends the request once more. If several threads or tasks hit the expired
  session at once, only one logs in. Requests to ``auth/`` endpoints and
  requests sent with ``include_auth=False`` are not retried this way, and a
  request body that can only be read once (a generator) can't be resent.
* ``keepalive_interval=<seconds>``: while the ``with`` block runs, call
  :meth:`~mstr.requests.MSTRRESTSession.extend_session` that often, in a
  background thread (or a task, for the async class). Failures are logged as
  warnings and don't stop the block. Choose an interval below the server's
  session timeout.

.. code-block:: python

   with AuthenticatedMSTRRESTSession(
       base_url="https://your-server/MicroStrategyLibrary/api/",
       username="dave",
       password=env("MSTR_PASSWORD"),
       relogin=True,
       keepalive_interval=240,
   ) as session:
       ...

Credential providers
--------------------

The :mod:`mstr.requests.credentials` package has ready-made functions for
environment variables and common secrets managers. The secrets managers each
need their own extra (see :doc:`installation`).

Environment variables
~~~~~~~~~~~~~~~~~~~~~

Needs no extra. :func:`~mstr.requests.credentials.env.env` reads the variable
each time the credential is resolved, and raises
:class:`~mstr.requests.rest.exceptions.MissingCredentialException` if it is
unset or empty, unless you pass ``default=``.

.. code-block:: python

   from mstr.requests.credentials.env import env

   with AuthenticatedMSTRRESTSession(
       base_url=env("MSTR_BASE_URL"),
       username=env("MSTR_USERNAME"),
       password=env("MSTR_PASSWORD"),
   ) as session:
       ...

Secrets managers
~~~~~~~~~~~~~~~~

The secrets manager providers come in two forms. The single-value form reads one secret or
parameter per credential. The multi-field form reads one secret holding a JSON
object once, and hands out its fields.

AWS Secrets Manager
~~~~~~~~~~~~~~~~~~~

Needs the ``aws`` extra.

.. code-block:: python

   from mstr.requests.credentials.aws import SecretsManagerSecret, secrets_manager

   # One secret per credential; key= picks a field from a JSON secret
   with AuthenticatedMSTRRESTSession(
       base_url="https://your-server/MicroStrategyLibrary/api/",
       username=secrets_manager("my-secret-id", key="username"),
       password=secrets_manager("my-secret-id", key="password"),
   ) as session:
       ...

   # One JSON secret holding every field, fetched once
   secret = SecretsManagerSecret("my-secret-id")

   with AuthenticatedMSTRRESTSession(
       base_url=secret.field("base_url"),
       username=secret.field("username"),
       password=secret.field("password"),
   ) as session:
       ...

AWS Systems Manager Parameter Store
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Needs the ``aws`` extra.

.. code-block:: python

   from mstr.requests.credentials.aws import ParameterStoreValues, parameter_store

   # Fetched each time they are resolved
   with AuthenticatedMSTRRESTSession(
       base_url=parameter_store("/myapp/mstr/base_url"),
       username=parameter_store("/myapp/mstr/username"),
       password=parameter_store("/myapp/mstr/password"),
   ) as session:
       ...

   # Each parameter cached after its first fetch
   params = ParameterStoreValues()

   with AuthenticatedMSTRRESTSession(
       base_url=params.parameter("/myapp/mstr/base_url"),
       username=params.parameter("/myapp/mstr/username"),
       password=params.parameter("/myapp/mstr/password"),
   ) as session:
       ...

Azure Key Vault
~~~~~~~~~~~~~~~

Needs the ``azure`` extra. Authentication uses
`DefaultAzureCredential <https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential>`_,
which supports managed identity, environment variables, the Azure CLI and
more.

.. code-block:: python

   from mstr.requests.credentials.azure import KeyVaultSecret, key_vault

   vault = "https://my-vault.vault.azure.net/"

   with AuthenticatedMSTRRESTSession(
       base_url="https://your-server/MicroStrategyLibrary/api/",
       username=key_vault(vault, "mstr-username"),
       password=key_vault(vault, "mstr-password"),
   ) as session:
       ...

   secret = KeyVaultSecret(vault, "mstr-connection")

   with AuthenticatedMSTRRESTSession(
       base_url=secret.field("base_url"),
       username=secret.field("username"),
       password=secret.field("password"),
   ) as session:
       ...

Google Cloud Secret Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Needs the ``gcp`` extra. Authentication uses
`Application Default Credentials <https://cloud.google.com/docs/authentication/application-default-credentials>`_.

.. code-block:: python

   from mstr.requests.credentials.gcp import SecretManagerSecret, secret_manager

   with AuthenticatedMSTRRESTSession(
       base_url="https://your-server/MicroStrategyLibrary/api/",
       username=secret_manager("my-project", "mstr-username"),
       password=secret_manager("my-project", "mstr-password"),
   ) as session:
       ...

   secret = SecretManagerSecret("my-project", "mstr-connection")

   with AuthenticatedMSTRRESTSession(
       base_url=secret.field("base_url"),
       username=secret.field("username"),
       password=secret.field("password"),
   ) as session:
       ...

See :ref:`credential-providers-api` for every option.
