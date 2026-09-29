# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.1.0]: https://github.com/paulbailey/mstr-rest-requests/releases/tag/v1.1.0
[1.0.0]: https://github.com/paulbailey/mstr-rest-requests/releases/tag/v1.0.0
