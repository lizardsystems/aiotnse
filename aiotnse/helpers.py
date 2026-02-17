"""Helpers for TNS-Energo API."""
from __future__ import annotations

import json
from base64 import b64encode
from typing import Any

import aiohttp
from aiohttp import hdrs

from .const import (
    ACCOUNT_NUMBER_LENGTH,
    API_HASH_HEADER,
    BASE_URL_TEMPLATE,
    BASIC_AUTH_TEMPLATE,
    DEFAULT_API_HASH,
    DEFAULT_CONTENT_TYPE,
    DEFAULT_USER_AGENT,
    DEVICE_ID_HEADER,
    LOGGER,
)
from .exceptions import TNSEApiError


def is_valid_account(account: str) -> bool:
    """Check if the account number is exactly 12 digits."""
    return len(account) == ACCOUNT_NUMBER_LENGTH and account.isdigit()


def get_base_url(region: str) -> str:
    """Build base URL for the given region."""
    return BASE_URL_TEMPLATE.format(region=region)


def build_request_headers(region: str, device_id: str) -> dict[str, str]:
    """Build common request headers for the given region and device."""
    credentials = BASIC_AUTH_TEMPLATE.format(region=region)
    basic_auth = "Basic " + b64encode(credentials.encode()).decode()
    return {
        hdrs.USER_AGENT: DEFAULT_USER_AGENT,
        hdrs.CONTENT_TYPE: DEFAULT_CONTENT_TYPE,
        API_HASH_HEADER: DEFAULT_API_HASH,
        hdrs.AUTHORIZATION: basic_auth,
        DEVICE_ID_HEADER: device_id,
    }


async def parse_api_response(
    resp: aiohttp.ClientResponse,
    *,
    error_class: type[TNSEApiError] = TNSEApiError,
    default_error: str = "API request failed",
) -> Any:
    """Parse API response JSON, check for HTTP and API-level errors.

    Raises error_class on:
    - JSON decode failure
    - HTTP error status (resp.ok is False)
    - API-level error (result flag is not True)
    """
    request_info = f"{resp.method} {resp.url.path}"

    try:
        data = await resp.json()
    except (json.JSONDecodeError, aiohttp.ContentTypeError) as err:
        raise error_class(
            f"{default_error} ({request_info} -> {resp.status})"
        ) from err

    if not resp.ok:
        error_msg = f"{default_error} ({request_info} -> {resp.status})"
        if isinstance(data, dict):
            error_info = data.get("error", {})
            if isinstance(error_info, dict):
                if desc := error_info.get("description"):
                    error_msg = f"{desc} ({request_info} -> {resp.status})"
            LOGGER.debug(
                "HTTP error: %s -> %d body=%s",
                request_info,
                resp.status,
                data,
            )
        raise error_class(error_msg)

    if isinstance(data, dict) and not data.get("result"):
        error = data.get("error", {})
        desc = (
            error.get("description", default_error)
            if isinstance(error, dict)
            else default_error
        )
        LOGGER.debug("API error: %s body=%s", request_info, data)
        raise error_class(f"{desc} ({request_info})")

    if isinstance(data, dict):
        return data.get("data")
    return data
