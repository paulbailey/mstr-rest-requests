# mstr-rest-requests

An extension to the excellent [requests](https://docs.python-requests.org/) `Session` object, providing a more straightforward interface for the [MicroStrategy REST API](https://demo.microstrategy.com/MicroStrategyLibrary/api-docs/).

![Python package](https://github.com/paulbailey/mstr-rest-requests/workflows/Python%20package/badge.svg)

## Installation

```bash
pip install mstr-rest-requests
```

### Extras

To use the built-in credential providers, install the corresponding extra:

```bash
pip install mstr-rest-requests[aws]    # AWS Secrets Manager & SSM Parameter Store
pip install mstr-rest-requests[azure]  # Azure Key Vault
pip install mstr-rest-requests[gcp]    # Google Cloud Secret Manager
```

## Quick start

```python
from mstr.requests import AuthenticatedMSTRRESTSession

with AuthenticatedMSTRRESTSession(
    base_url="https://demo.microstrategy.com/MicroStrategyLibrary/api/",
    username="dave",
    password="hellodave",
) as session:
    projects = session.get("projects").json()
```

The session automatically logs in when the context manager is entered and logs
out when it exits.

## Authentication

Four authentication modes are supported. In every case you can use either the
context-manager style shown above or the manual approach shown below.

### Standard (username and password)

```python
from mstr.requests import MSTRRESTSession

session = MSTRRESTSession(
    base_url="https://demo.microstrategy.com/MicroStrategyLibrary/api/"
)
session.login(username="dave", password="hellodave")
```

### Identity token (delegation)

```python
session.delegate(identity_token="supersecretidentitytoken")
```

### API key (trusted authentication)

```python
session.login(api_key="supersecretapikey")
```

### Anonymous

```python
session.login()
```

## Credential providers

Every credential parameter on `AuthenticatedMSTRRESTSession` -- including
`base_url` -- accepts either a plain string **or** a zero-argument callable
that returns a string.  Callables are resolved lazily when the context manager
is entered, not when the session is constructed.

This makes it easy to pull credentials from vaults, environment helpers, or any
other source at connect time:

```python
from mstr.requests import AuthenticatedMSTRRESTSession

with AuthenticatedMSTRRESTSession(
    base_url="https://demo.microstrategy.com/MicroStrategyLibrary/api/",
    username=lambda: get_username_from_somewhere(),
    password=lambda: get_password_from_somewhere(),
) as session:
    ...
```

### AWS Secrets Manager

Install with `pip install mstr-rest-requests[aws]`.

#### Single-value secrets

Use `secrets_manager` to create a callable for a single secret value:

```python
from mstr.requests import AuthenticatedMSTRRESTSession
from mstr.requests.credentials.aws import secrets_manager

with AuthenticatedMSTRRESTSession(
    base_url="https://demo.microstrategy.com/MicroStrategyLibrary/api/",
    username=secrets_manager("my-secret-id", key="username"),
    password=secrets_manager("my-secret-id", key="password"),
) as session:
    ...
```

#### Multi-field secrets

When a single secret contains all connection details as a JSON object, use
`SecretsManagerSecret` to fetch the secret once and share it across fields:

```python
from mstr.requests import AuthenticatedMSTRRESTSession
from mstr.requests.credentials.aws import SecretsManagerSecret

secret = SecretsManagerSecret("my-secret-id")

with AuthenticatedMSTRRESTSession(
    base_url=secret.field("base_url"),
    username=secret.field("username"),
    password=secret.field("password"),
) as session:
    ...
```

The secret is only fetched on the first field resolution, and the result is
cached for all subsequent fields.

### AWS SSM Parameter Store

Also covered by the `aws` extra (`pip install mstr-rest-requests[aws]`).

#### Individual parameters

```python
from mstr.requests.credentials.aws import parameter_store

with AuthenticatedMSTRRESTSession(
    base_url=parameter_store("/myapp/mstr/base_url"),
    username=parameter_store("/myapp/mstr/username"),
    password=parameter_store("/myapp/mstr/password"),
) as session:
    ...
```

#### Grouped parameters with caching

`ParameterStoreValues` caches each parameter after the first fetch so
repeated resolutions of the same name do not make extra API calls:

```python
from mstr.requests.credentials.aws import ParameterStoreValues

params = ParameterStoreValues()

with AuthenticatedMSTRRESTSession(
    base_url=params.parameter("/myapp/mstr/base_url"),
    username=params.parameter("/myapp/mstr/username"),
    password=params.parameter("/myapp/mstr/password"),
) as session:
    ...
```

### Azure Key Vault

Install with `pip install mstr-rest-requests[azure]`.  Authentication uses
[`DefaultAzureCredential`](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential)
which supports managed identity, environment variables, Azure CLI, and more.

#### Single-value secrets

```python
from mstr.requests.credentials.azure import key_vault

with AuthenticatedMSTRRESTSession(
    base_url="https://demo.microstrategy.com/MicroStrategyLibrary/api/",
    username=key_vault("https://my-vault.vault.azure.net/", "mstr-username"),
    password=key_vault("https://my-vault.vault.azure.net/", "mstr-password"),
) as session:
    ...
```

#### Multi-field secrets

```python
from mstr.requests.credentials.azure import KeyVaultSecret

secret = KeyVaultSecret("https://my-vault.vault.azure.net/", "mstr-connection")

with AuthenticatedMSTRRESTSession(
    base_url=secret.field("base_url"),
    username=secret.field("username"),
    password=secret.field("password"),
) as session:
    ...
```

### Google Cloud Secret Manager

Install with `pip install mstr-rest-requests[gcp]`.  Authentication uses
[Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials).

#### Single-value secrets

```python
from mstr.requests.credentials.gcp import secret_manager

with AuthenticatedMSTRRESTSession(
    base_url="https://demo.microstrategy.com/MicroStrategyLibrary/api/",
    username=secret_manager("my-project", "mstr-username"),
    password=secret_manager("my-project", "mstr-password"),
) as session:
    ...
```

#### Multi-field secrets

```python
from mstr.requests.credentials.gcp import SecretManagerSecret

secret = SecretManagerSecret("my-project", "mstr-connection")

with AuthenticatedMSTRRESTSession(
    base_url=secret.field("base_url"),
    username=secret.field("username"),
    password=secret.field("password"),
) as session:
    ...
```

## Session handling

### Checking session state

```python
session.has_session()      # True if an auth token is present
session.get_session_info() # GET /sessions
session.extend_session()   # PUT /sessions (prolongs the session)
session.get_userinfo()     # GET /sessions/userInfo
```

### Serialisation and restoration

A session can be serialised to JSON and later restored, which is useful for
passing sessions between processes:

```python
data = session.json()

# Later, in another process:
restored = MSTRRESTSession.from_dict(json.loads(data))
```

### Projects

```python
session.load_projects()
project_id = session.get_project_id("My Project")
response = session.get("reports/abc123", project_id=project_id)
```

## Making requests

`MSTRRESTSession` extends `requests.Session`, so the full requests API is
available. Two extra keyword arguments are added to every request method:

- `include_auth` (default `True`) -- attach the `X-MSTR-AuthToken` header.
- `project_id` -- attach the `X-MSTR-ProjectID` header for project-scoped
  endpoints.

```python
response = session.get("reports/abc123", project_id="B7CA92...")
```

## Exceptions

All API error responses are translated into typed exceptions:

| Exception                     | Trigger                        |
|-------------------------------|--------------------------------|
| `LoginFailureException`       | ERR001, ERR003                 |
| `SessionException`            | ERR009                         |
| `ResourceNotFoundException`   | ERR004                         |
| `MSTRUnknownException`        | Unrecognised error response    |
| `MSTRException`               | Any other MicroStrategy error  |

```python
from mstr.requests.rest.exceptions import LoginFailureException
```

## License

Apache 2.0 -- see [LICENSE](LICENSE) for details.
