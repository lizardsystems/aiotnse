"""Constants for TNS-Energo API."""
from __future__ import annotations

import logging
from typing import Final

LOGGER = logging.getLogger(__package__)

LOG_LEVELS = {
    None: logging.WARNING,  # 0
    0: logging.ERROR,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG,
}

DEFAULT_BASE_URL: Final = "https://rest.tns-e.ru"
DEFAULT_API_VERSION: Final = "1.69"
DEFAULT_HASH: Final = "958fdc9525875bb8ef89e5c0bda3ebc60b95040e"
DEFAULT_USER_AGENT: Final = "okhttp/3.7.0"
DEFAULT_ACCOUNT_NUMBERS: Final = 12

REGIONS: Final[dict[str, str]] = {
    "58": "penza",
    "76": "yar",
    "36": "voronezh",
    "53": "novgorod",
    "10": "karelia",
    "23": "kuban",
    "93": "kuban",
    "12": "mari-el",
    "52": "nn",
    "71": "tula",
    "61": "rostov",
}
