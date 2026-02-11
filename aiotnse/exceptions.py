"""Exceptions for TNS-Energo API."""
from __future__ import annotations


class TNSEApiError(Exception):
    """Base class for aiotnse errors."""


class TNSEAuthError(TNSEApiError):
    """Base class for aiotnse auth errors."""


class TNSETokenExpiredError(TNSEAuthError):
    """Access token has expired and needs refresh."""


class TNSETokenRefreshError(TNSEAuthError):
    """Refresh token failed, re-authentication required."""


class RegionNotFound(TNSEApiError):
    """Region for account number is not found."""


class RequiredApiParamNotFound(TNSEApiError):
    """Required API parameter not found."""


class InvalidAccountNumber(TNSEApiError):
    """Invalid account number."""
