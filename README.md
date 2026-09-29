# mstr-rest-requests

A straightforward sync and async client for the [MicroStrategy REST API](https://demo.microstrategy.com/MicroStrategyLibrary/api-docs/), built on [httpx](https://www.python-httpx.org/).

![Python package](https://github.com/paulbailey/mstr-rest-requests/workflows/Python%20package/badge.svg)

Full documentation: <https://mstr-rest-requests.readthedocs.io/>

## Installation

Requires Python 3.10 or later.

```bash
pip install mstr-rest-requests
```

### Extras

To use the built-in credential providers, install the corresponding extra:

```bash
pip install mstr-rest-requests[aws]    # AWS Secrets Manager & SSM Parameter Store
pip install mstr-rest-requests[azure]  # Azure Key Vault
pip install mstr-rest-requests[gcp]    # Google Cloud Secret Manager
pip install mstr-rest-requests[requests]  # Deprecated requests-based sessions (mstr.requests.compat)
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

Context manager:

```python
with AuthenticatedMSTRRESTSession(
    base_url="https://.../api/",
    identity_token="supersecretidentitytoken",
) as session:
    ...
```

Manual:

```python
session.delegate(identity_token="supersecretidentitytoken")
```

### API key (trusted authentication)

Context manager (use the `api_key` parameter; supports callables for vaults):

```python
with AuthenticatedMSTRRESTSession(
    base_url="https://.../api/",
    api_key="your-api-key",
) as session:
    ...
```

Manual:

```python
session.login(api_key="your-api-key")
```

### Anonymous

Context manager:

```python
with AuthenticatedMSTRRESTSession(base_url="https://.../api/") as session:
    ...
```

Manual:

```python
session.login()
```

## Credential providers

Every credential parameter on `AuthenticatedMSTRRESTSession` -- including
`base_url` -- accepts either a plain string **or** a zero-argument callable
that returns a string (the `Credential` type).  Callables are resolved
lazily when the context manager is entered, not when the session is constructed.
You can import the type alias from `mstr.requests` for type hints.

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

### Environment variables

No extra needed. `env()` reads the variable each time it is resolved and
raises `MissingCredentialException` if it is unset or empty (unless you pass
`default=`):

```python
from mstr.requests.credentials.env import env

with AuthenticatedMSTRRESTSession(
    base_url=env("MSTR_BASE_URL"),
    username=env("MSTR_USERNAME"),
    password=env("MSTR_PASSWORD"),
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

The saved data holds the live auth token and session cookies, so treat it as
a secret. Restored cookies are sent only to the `base_url` host.

### Projects

Pass a project name as `project=` and the session looks up its ID, fetching
the project list the first time (and again for a name it doesn't know):

```python
response = session.get("reports/abc123", project="My Project")
project_id = session.resolve_project_id("My Project")
```

### Long-running jobs

`AuthenticatedMSTRRESTSession` (and its async counterpart) can keep a session
alive for long jobs:

- `relogin=True` -- when a request fails because the session expired
  (`ERR009`), log in again with freshly resolved credentials and send the
  request once more.
- `keepalive_interval=240` -- call `extend_session()` every 240 seconds in the
  background while the `with` block runs.

```python
with AuthenticatedMSTRRESTSession(
    base_url="https://your-server/MicroStrategyLibrary/api/",
    username="dave",
    password=env("MSTR_PASSWORD"),
    relogin=True,
    keepalive_interval=240,
) as session:
    ...
```

### Identity tokens

`create_identity_token()` returns a token another process can use to get its
own session as the same user, without the user's credentials:

```python
token = session.create_identity_token()

# In the other process:
with AuthenticatedMSTRRESTSession(base_url=..., identity_token=token) as s:
    ...
```

## Making requests

`MSTRRESTSession` wraps an `httpx.Client` (available as `session.client`).
Its request methods take the usual httpx arguments (`params`, `json`,
`headers`, `timeout`, ...) plus two extra keyword arguments:

- `include_auth` (default `True`) -- attach the `X-MSTR-AuthToken` header.
  The token is only sent to the scheme, host and port of `base_url`; absolute
  URLs on other hosts, and redirects to them, go without it.
- `project_id` -- attach the `X-MSTR-ProjectID` header for project-scoped
  endpoints.
- `project` -- the same, from a project name.

```python
response = session.get("reports/abc123", project_id="B7CA92...")
```

### Retries

Pass `retries=` to retry requests that fail to connect, and (for `GET`,
`HEAD`, `OPTIONS`, `PUT` and `DELETE`) ones that time out, hit a network
error or get a 502, 503 or 504. The wait starts at `backoff_factor` seconds
(default 0.5) and doubles each time, up to 60 seconds; a longer `Retry-After`
from the server is honoured.

```python
session = MSTRRESTSession(base_url=..., retries=3, backoff_factor=1)
```

### Logging

The library logs to the `mstr.requests` logger. At `DEBUG` it logs each
request's method, URL, status and time taken; retries, re-logins and failed
keep-alives are logged at `WARNING` or `INFO`. Headers, bodies, tokens and
passwords are never logged, and any `user:password@` in a URL is removed.

```python
logging.getLogger("mstr.requests").setLevel(logging.DEBUG)
```

### Testing your code

Pass an `httpx.MockTransport` as `transport=` to run your code against a fake
server; see the [testing guide](https://mstr-rest-requests.readthedocs.io/en/latest/usage/testing.html).

Extra constructor arguments (`verify`, `proxy`, `limits`, `http2`,
`transport`, ...) are passed to the `httpx.Client`. Unlike httpx's own
defaults, there is no timeout unless you pass `timeout=`, and redirects are
followed.

## Async usage

`AsyncMSTRRESTSession` and `AsyncAuthenticatedMSTRRESTSession` mirror the
synchronous classes method for method and work with asyncio and trio:

```python
import asyncio

from mstr.requests import AsyncAuthenticatedMSTRRESTSession


async def main():
    async with AsyncAuthenticatedMSTRRESTSession(
        base_url="https://demo.microstrategy.com/MicroStrategyLibrary/api/",
        username="dave",
        password="hellodave",
    ) as session:
        await session.load_projects()
        project_id = session.get_project_id("My Project")
        responses = await asyncio.gather(
            session.get("reports/abc123", project_id=project_id),
            session.get("reports/def456", project_id=project_id),
        )


asyncio.run(main())
```

Differences from the synchronous classes:

- Methods are coroutines and return `httpx.Response` objects.
- Credentials can also be `async def` callables. Plain callables, including
  the built-in credential providers, run in a worker thread so they don't
  block the event loop.
- The session wraps an `httpx.AsyncClient`, available as `session.client`,
  with the same constructor arguments and defaults as the synchronous session.
- Use `async with` (or `await session.aclose()`) to release connections.
- `to_dict()` / `from_dict()` use the same format as the synchronous session,
  so a session can be handed between the two.

## Upgrading from 1.x

Since 2.0 the sessions are built on [httpx](https://www.python-httpx.org/)
instead of requests. The class names, arguments and methods are the same, so
most code keeps working. The differences:

- Methods return `httpx.Response`. Use `response.is_success` instead of
  `response.ok`. `raise_for_status()` raises `httpx.HTTPStatusError`, and
  also raises for 3xx responses.
- Request arguments follow httpx: `follow_redirects` instead of
  `allow_redirects`, and `content=` for raw bodies.
- The session wraps an `httpx.Client` (`session.client`) rather than being a
  `requests.Session`. Configure TLS, proxies, retries and connection limits
  with constructor arguments (`verify`, `proxy`, `transport`, `limits`)
  instead of `session.mount()` and adapters.
- Relative URLs are always appended to `base_url`, so a leading `/` or a
  missing trailing slash no longer drops the `/api` segment.
- Use `with` or `session.close()` to release connections.
- Saved sessions (`to_dict()` / `json()`) from 1.x load unchanged.

If you need the 1.x behaviour while you migrate, the requests-based classes
are still available, with a `DeprecationWarning`, until 3.0:

```bash
pip install mstr-rest-requests[requests]
```

```python
from mstr.requests.compat import AuthenticatedMSTRRESTSession
```

## Exceptions

All API error responses are translated into typed exceptions:

| Exception                          | Error codes            | Trigger                              |
|------------------------------------|------------------------|--------------------------------------|
| `LoginFailureException`            | ERR003                 | Authentication error                 |
| `IServerException`                 | ERR002, ERR0013        | IServer error or unreachable         |
| `ResourceNotFoundException`        | ERR004                 | Resource not found                   |
| `InvalidRequestException`          | ERR005, ERR006, ERR007 | Missing or invalid input             |
| `SessionException`                 | ERR009                 | Session invalid or timed out         |
| `InsufficientPrivilegesException`  | ERR0014, ERR0017       | Insufficient privileges / permission |
| `ObjectAlreadyExistsException`     | ERR0015                | Object already exists                |
| `ExecutionCancelledException`      | --                     | Not raised by the library; for your own code |
| `MSTRUnknownException`             | --                     | Response missing error code          |
| `MSTRException`                    | Everything else        | Base class / catch-all               |

```python
from mstr.requests.rest.exceptions import LoginFailureException
```

Error responses without a JSON body (for example a proxy's HTML error page)
are returned as normal. Pass `raise_on_http_error=True` when creating the
session to raise `MSTRHTTPError` for those too. Exceptions raised for a
response carry its `status_code` and the `response`.

## License

Apache 2.0 -- see [LICENSE](LICENSE) for details.
