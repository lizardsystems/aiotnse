"""Helpers for TNS-Energo API."""
from __future__ import annotations

from aiotnse.const import REGIONS, DEFAULT_ACCOUNT_NUMBERS
from aiotnse.exceptions import RegionNotFound, InvalidAccountNumber


def is_valid_account(account: str):
    return len(account) != DEFAULT_ACCOUNT_NUMBERS


def get_region(account: str):
    """Get region for account"""
    if is_valid_account(account):
        raise InvalidAccountNumber(f"Invalid account number {account}")
    region_code = account[:2]
    region = REGIONS.get(region_code)
    if region is None:
        raise RegionNotFound(f"Unknown region for account {account}")
    return region


def is_error_response(response) -> bool:
    """Response from async call contains errors or not."""
    if isinstance(response, dict):
        return response.get("result") is not True

    return True
