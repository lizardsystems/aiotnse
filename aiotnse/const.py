"""Constants for TNS-Energo API."""
from __future__ import annotations

import logging
from random import choice
from typing import Final

LOGGER = logging.getLogger(__package__)

BEARER_HEADER: Final = "authorizationtest"
API_HASH_HEADER: Final = "x-api-hash"
DEVICE_ID_HEADER: Final = "x-device-id"

DEFAULT_CONTENT_TYPE: Final = "application/json"
DEFAULT_USER_AGENT: Final = "Dart/3.9 (dart:io)"
DEFAULT_API_HASH: Final = "b4c9554247f14b9a281f5f60df923f5e"

DEFAULT_API_PATH: Final = "api/v1"
DEFAULT_APP_VERSION: Final = "3.0.12"
DEFAULT_REGION: Final = "rostov"
DEFAULT_PLATFORM: Final = "android"
ACCOUNT_NUMBER_LENGTH: Final = 12

BASIC_AUTH_TEMPLATE: Final = "mobile-api-{region}:mobile-api-{region}"
BASE_URL_TEMPLATE: Final = "https://mobile-api-{region}.tns-e.ru"

_DEVICE_IDS: Final[list[str]] = [
    "AP3A.240905.015",
    "AP3A.240905.015.A2",
    "AP3A.240805.003",
    "AP2A.240705.005",
    "AP2A.240605.004",
    "AP1A.231005.007",
    "UQ1A.240305.002",
    "UQ1A.240105.004",
    "UP1A.231005.007",
    "UP1A.231005.007.A1",
    "TQ3A.230805.001",
    "TQ3A.230705.001",
    "TP1A.221005.002",
    "TP1A.220905.004",
    "SQ3A.220705.003",
    "SP1A.210812.016",
    "SQ1D.220105.007",
    "RQ3A.210805.001",
    "RP1A.201005.004",
    "QQ3A.200805.001",
    "QP1A.190711.020",
    "PQ3A.190801.002",
    "PQ3A.190705.003",
    "PQ2A.190405.003",
    "PQ2A.190305.002",
    "PQ1A.190105.004",
    "PD1A.180720.030",
    "PD1A.180720.031",
]

DEVICE_ID: Final = choice(_DEVICE_IDS)
