"""Helpers for TNS-Energo API."""
from __future__ import annotations

from base64 import b64encode
from typing import Any

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
)


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


def is_error_response(response: Any) -> bool:
    """Check if API response indicates an error."""
    if not isinstance(response, dict):
        return True
    return response.get("result") is not True or response.get("statusCode", 200) != 200
