"""Helpers for TNS-Energo API."""
from __future__ import annotations

from aiotnse.const import REGIONS, DEFAULT_ACCOUNT_NUMBERS
from aiotnse.exceptions import RegionNotFound, InvalidAccountNumber


def get_region(account: str):
    """Get region for account"""
    if len(account) != DEFAULT_ACCOUNT_NUMBERS:
        raise InvalidAccountNumber(f"Invalid account number {account}")
    region_code = account[:2]
    region = REGIONS.get(region_code)
    if region is None:
        raise RegionNotFound(f"Unknown region for account {account}")
    return region
