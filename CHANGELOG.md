# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0]
### Added
- First stable release (1.0.0).
- Public API: `MSTRRESTSession`, `AuthenticatedMSTRRESTSession`, `Credential`, `MSTRSessionProtocol` from `mstr.requests`.
- Authentication: username/password, identity token (delegation), API key, anonymous.
- Credential providers (optional): AWS (Secrets Manager, SSM Parameter Store), Azure Key Vault, Google Cloud Secret Manager.
- Session persistence: serialise/restore sessions via `json()` and `from_dict()`.
- Typed exceptions for MicroStrategy API errors (see `mstr.requests.rest.exceptions`).

[1.0.0]: https://github.com/paulbailey/mstr-rest-requests/releases/tag/v1.0.0
