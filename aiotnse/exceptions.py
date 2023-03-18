"""Exceptions for TNS-Energo API."""
from __future__ import annotations


class TNSEApiError(Exception):
    """Base class for aiotaipit errors"""


class TNSEAuthError(TNSEApiError):
    """Base class for aiotaipit auth errors"""


class RegionNotFound(TNSEApiError):
    """Region for account number are not found"""


class RequiredApiParamNotFound(TNSEApiError):
    """Required API parameter not found"""


class InvalidAccountNumber(TNSEApiError):
    """Invalid account number"""
