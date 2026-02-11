"""TNS-Energo API wrapper."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("aiotnse")
except PackageNotFoundError:
    __version__ = "unknown"

from .api import TNSEApi, async_get_regions
from .auth import AbstractTNSEAuth, SimpleTNSEAuth
from .exceptions import (
    InvalidAccountNumber,
    RegionNotFound,
    RequiredApiParamNotFound,
    TNSEApiError,
    TNSEAuthError,
    TNSETokenExpiredError,
    TNSETokenRefreshError,
)
from .helpers import get_base_url, is_error_response, is_valid_account

__all__ = [
    "AbstractTNSEAuth",
    "InvalidAccountNumber",
    "RegionNotFound",
    "RequiredApiParamNotFound",
    "SimpleTNSEAuth",
    "TNSEApi",
    "TNSEApiError",
    "TNSEAuthError",
    "TNSETokenExpiredError",
    "TNSETokenRefreshError",
    "__version__",
    "async_get_regions",
    "get_base_url",
    "is_error_response",
    "is_valid_account",
]
