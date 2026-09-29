# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0]
### Added
- `raise_on_http_error=True` (a constructor argument on the httpx and async sessions, an attribute on the requests-based ones) raises the new `MSTRHTTPError` for error responses without a MicroStrategy JSON body, such as a proxy's HTML error page or an empty 502. Off by default, so such responses are still returned as before.
- Every `MSTRException` raised for a response carries `status_code` and `response`.
- A `py.typed` marker, so type checkers use the package's type hints.

### Fixed
- Leaving an `AuthenticatedMSTRRESTSession` or `AsyncAuthenticatedMSTRRESTSession` block with an exception no longer replaces that exception with a logout error. The logout error is logged as a warning on the `mstr.requests` logger instead.
- An expired session (`SessionException`) during logout on exit is now ignored, even when the block succeeded, and the token is cleared.
- `logout()` raises `HTTPStatusError` (`requests.HTTPError` for the requests-based sessions) when the server answers with an error status and no JSON error body. Previously it did nothing and left the token in place.
- A JSON error body that is not an object (a list or a string) raises `MSTRUnknownException` instead of `TypeError`.
- Error messages that already end in a full stop no longer get a second one.
- The `//` warning only checks the URL path, so a URL in a query parameter no longer triggers it.

### Changed
- Tests that call demo.microstrategy.com are marked `live` and only run with `pytest --live`. CI still runs them.

## [2.1.0]
### Security
- The auth token (and the other `X-MSTR` headers) is now only sent to the scheme, host and port of `base_url`. Previously it was sent to any absolute URL requested through the session, and it was forwarded when the server redirected to another host, because httpx and requests only strip `Authorization` on redirects. Sessions without a `base_url` send the token to the URL requested but still drop it on a redirect to another origin. Applies to the httpx, async and deprecated requests-based sessions.
- Cookies restored with `update_from_json()` / `from_dict()` are now set for the `base_url` host. They were previously restored without a domain and sent to every host.
- `AuthenticatedMSTRRESTSession` and `AsyncAuthenticatedMSTRRESTSession` raise the new `MissingCredentialException` (a `LoginFailureException`) when a credential you passed resolves to `None`, for example a password function reading an unset environment variable. Previously a missing password silently became a trusted login as that user, and a missing API key or identity token fell back to another login mode. Leaving `password` out altogether still logs in with trusted authentication.

### Fixed
- `include_auth=False` now sends the request without the auth token. It previously had no effect, because the token is also a session-wide header.

### Changed
- Documented that `to_dict()` / `json()` contain the live auth token and should be treated as secrets.

## [2.0.1]
### Changed
- Updated locked development dependencies (cryptography 50.0.0, pyasn1 0.6.4). No changes to the package itself.
- The publish workflow now fails if the release tag does not match the version in `pyproject.toml`.

## [2.0.0]
### Changed (breaking)
- `mstr.requests.MSTRRESTSession`, `AuthenticatedMSTRRESTSession` and `MSTRSessionProtocol` are now the httpx-based classes introduced in 1.3. They keep the same names, arguments and methods but return `httpx.Response`. See "Upgrading from 1.x" in the README or docs.
- `httpx` and `anyio` are core dependencies. `requests` and `requests-toolbelt` are no longer installed by default and have moved to the `requests` extra.
- The async classes (`AsyncMSTRRESTSession`, `AsyncAuthenticatedMSTRRESTSession`, `AsyncCredential`, `AsyncMSTRSessionProtocol`) are imported eagerly and listed in `mstr.requests.__all__`.
- `Credential` now lives in `mstr.requests.rest.core`. It is still exported from `mstr.requests`, `mstr.requests.credentials` and `mstr.requests.rest.authenticated_session`.

### Deprecated
- The requests-based sessions are available from `mstr.requests.compat` (needs the `requests` extra). Creating one emits a `DeprecationWarning`, and they will be removed in 3.0.
- The `async` and `httpx` extras are kept so existing install commands work, but they add nothing.
- `mstr.requests.httpx` remains as an alias for the default classes.

## [1.3.0]
### Added
- httpx-based synchronous sessions in `mstr.requests.httpx` (`MSTRRESTSession`, `AuthenticatedMSTRRESTSession`), with the same names and arguments as the requests-based classes. Install with the new `httpx` extra. These become the default in 2.0.
- The sync and async httpx sessions share their client-state and persistence code (`mstr.requests.rest.httpx_common`).

### Deprecated
- Creating a requests-based `MSTRRESTSession` or `AuthenticatedMSTRRESTSession` emits a `PendingDeprecationWarning`. In 2.0 these names will refer to the httpx-based classes. See "Moving to httpx" in the docs.

## [1.2.0]
### Added
- Async sessions built on httpx: `AsyncMSTRRESTSession` and `AsyncAuthenticatedMSTRRESTSession`, importable from `mstr.requests` (or `mstr.requests.rest.aio`). Install with the new `async` extra: `pip install mstr-rest-requests[async]`.
- The async sessions mirror the synchronous API method for method, work under asyncio and trio, and serialise to the same `to_dict()` format.
- `AsyncCredential`: credentials for the async sessions may also be `async def` callables; synchronous callables run in a worker thread.
- `check_valid_session` now supports coroutine methods.

## [1.1.0]
### Added
- `mstr.requests.rest.core`: transport-independent helpers for MicroStrategy headers, error translation, login/delegate payloads and project look-ups. The session classes now use these, preparing for async support.

### Fixed
- JSON error responses whose `Content-Type` carries parameters (e.g. `application/json;charset=UTF-8`) are now translated into MicroStrategy exceptions.
- A failed response with no `Content-Type` header no longer raises `KeyError`; the response is returned as for any other non-JSON error.
- `headers` passed to a request are no longer modified in place.

## [1.0.0]
### Added
- First stable release (1.0.0).
- Public API: `MSTRRESTSession`, `AuthenticatedMSTRRESTSession`, `Credential`, `MSTRSessionProtocol` from `mstr.requests`.
- Authentication: username/password, identity token (delegation), API key, anonymous.
- Credential providers (optional): AWS (Secrets Manager, SSM Parameter Store), Azure Key Vault, Google Cloud Secret Manager.
- Session persistence: serialise/restore sessions via `json()` and `from_dict()`.
- Typed exceptions for MicroStrategy API errors (see `mstr.requests.rest.exceptions`).

[2.2.0]: https://github.com/paulbailey/mstr-rest-requests/releases/tag/v2.2.0
[2.1.0]: https://github.com/paulbailey/mstr-rest-requests/releases/tag/v2.1.0
[2.0.1]: https://github.com/paulbailey/mstr-rest-requests/releases/tag/v2.0.1
[2.0.0]: https://github.com/paulbailey/mstr-rest-requests/releases/tag/v2.0.0
[1.3.0]: https://github.com/paulbailey/mstr-rest-requests/releases/tag/v1.3.0
[1.2.0]: https://github.com/paulbailey/mstr-rest-requests/releases/tag/v1.2.0
[1.1.0]: https://github.com/paulbailey/mstr-rest-requests/releases/tag/v1.1.0
[1.0.0]: https://github.com/paulbailey/mstr-rest-requests/releases/tag/v1.0.0
