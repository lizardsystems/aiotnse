# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] - 2026-02-12

Re-release of 2.0.0 (PyPI filename conflict after deleted release).

## [2.0.0] - 2026-02-11

### Changed

- Complete rewrite for new TNS-Energo mobile API
- Auth: JWT-based authentication with email/password login, token refresh, and logout
- Auth: Region-based hostnames (`mobile-api-{region}.tns-e.ru`) instead of path-based routing
- Auth: Three-layer auth headers: `x-api-hash`, `authorization: Basic`, `authorizationtest: Bearer JWT`
- Auth: `region` parameter is now **required** in `SimpleTNSEAuth` (no default fallback)
- API: JSON POST requests instead of multipart form-data
- API: New response format `{"result": true, "statusCode": 200, "data": ...}`
- API: New User-Agent `Dart/3.9 (dart:io)` instead of `okhttp/3.7.0`
- API: `async_get_regions()` is now a standalone function (accepts `ClientSession`, no auth required)
- CLI: `--email` and `--password` instead of account number
- CLI: `--regions` works without credentials
- Versioning: static version in `pyproject.toml` + `importlib.metadata` (removed setuptools_scm)
- Build: requires `setuptools>=64` only
- CI: modernized GitHub Actions (actions v5/v6, Python 3.13, pip cache, trusted publishers)

### Added

- `SimpleTNSEAuth`: `access_token_expires` and `refresh_token_expires` parameters and properties — store and expose JWT expiration timestamps from API responses
- `SimpleTNSEAuth`: `token_update_callback` parameter — caller-provided callback invoked after login or token refresh with serialized token data for persistence
- `SimpleTNSEAuth.async_get_access_token()`: automatic token management — returns cached token if valid, refreshes if access token expired, re-authenticates if both tokens expired
- `SimpleTNSEAuth`: `asyncio.Lock` guard to prevent concurrent token refresh from parallel API calls
- `async_get_regions(session)` — standalone function to get available regions without auth
- `SimpleTNSEAuth.async_login()` — authenticate with email/password
- `SimpleTNSEAuth.async_refresh_token()` — refresh JWT access token
- `SimpleTNSEAuth.async_logout()` — logout and invalidate tokens
- `TNSEApi.async_check_version()` — check app version
- `TNSEApi.async_get_user_info()` — get authenticated user info
- `TNSEApi.async_get_account_info()` — get account details by ID
- `TNSEApi.async_get_main_page_debt_info()` — get main page debt info
- `TNSEApi.async_get_information()` — get information for account
- `TNSEApi.async_get_counters()` — get meters for account
- `TNSEApi.async_get_balance()` — get payment balance for account
- `TNSEApi.async_get_counter_readings()` — get readings history for a counter
- `TNSEApi.async_get_invoice_settings()` — get invoice email settings
- `TNSEApi.async_get_invoices()` — get list of invoices
- `TNSEApi.async_get_invoice_file()` — get invoice as base64 PDF
- `TNSEApi.async_get_history()` — get account history
- `TNSETokenExpiredError` and `TNSETokenRefreshError` exception classes
- `build_request_headers()` — shared helper for building request headers
- `get_base_url()` helper function
- Header name/value constants: `API_HASH_HEADER`, `DEVICE_ID_HEADER`, `DEFAULT_CONTENT_TYPE`, `BASIC_AUTH_TEMPLATE`
- `[project.optional-dependencies] test` in `pyproject.toml`
- `.github/workflows/ci.yml` — test workflow on push/PR
- `.github/workflows/publish.yml` — PyPI publish with trusted publishers (OIDC)

### Removed

- `TNSEApi.async_get_regions()` class method (replaced by standalone `async_get_regions()`)
- `setuptools_scm` dependency and `_version.py` auto-generation
- `.gitattributes` and `.git_archival.txt` (setuptools_scm artifacts)
- `.github/workflows/release_to_pypi.yml` (replaced by `publish.yml`)
- `async_is_registered()` — no equivalent in new API
- `async_get_account_status()` — no equivalent in new API
- `async_get_authorization()` — replaced by `SimpleTNSEAuth.async_login()`
- `async_get_main_page_info()` — replaced by `async_get_main_page_debt_info()`
- `async_get_general_info()` — replaced by `async_get_account_info()`
- `async_get_current_payment()` — replaced by `async_get_balance()`
- `async_get_latest_readings()` — replaced by `async_get_counters()`
- `async_get_readings_history()` — replaced by `async_get_counter_readings()`
- `async_get_bill()` — replaced by `async_get_invoice_file()`
- `async_get_payments_history()` — replaced by `async_get_history()`
- Old constants: `DEFAULT_BASE_URL`, `DEFAULT_API_VERSION`, `DEFAULT_HASH`

## [1.3.0] - 2024-02-27

### Fixed

- Small fixes


## [1.2.0] - 2023-12-25

### Fixed

- Some typos fixed in examples and cli

## [1.1.1] - 2023-04-14

### Fixed

- Fixed parameter type async_get_bill function

## [1.1.0] - 2023-04-04

### Added

- Added authorization request to API
- Added helpers module

### Fixed

- API error detection

## [1.0.0] - 2023-03-18

First public release.
