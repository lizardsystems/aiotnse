"""Tests for aiotnse helpers module."""
from __future__ import annotations

from base64 import b64encode

from aiohttp import hdrs

from aiotnse.const import (
    DEFAULT_API_HASH,
    DEFAULT_CONTENT_TYPE,
    DEFAULT_USER_AGENT,
    DEVICE_ID_HEADER,
)
from aiotnse.helpers import (
    build_request_headers,
    get_base_url,
    is_valid_account,
)


class TestIsValidAccount:
    def test_valid_12_digits(self) -> None:
        assert is_valid_account("610000000001") is True

    def test_too_short(self) -> None:
        assert is_valid_account("000000000") is False

    def test_too_long(self) -> None:
        assert is_valid_account("6100000000011") is False

    def test_empty(self) -> None:
        assert is_valid_account("") is False

    def test_non_digit_chars(self) -> None:
        assert is_valid_account("61000000000a") is False

    def test_with_spaces(self) -> None:
        assert is_valid_account("61000000000 ") is False


class TestBuildRequestHeaders:
    def test_all_headers(self) -> None:
        headers = build_request_headers("rostov", "AP3A.240905.015")
        expected_basic = "Basic " + b64encode(
            b"mobile-api-rostov:mobile-api-rostov"
        ).decode()

        assert headers[hdrs.USER_AGENT] == DEFAULT_USER_AGENT
        assert headers[hdrs.CONTENT_TYPE] == DEFAULT_CONTENT_TYPE
        assert headers["x-api-hash"] == DEFAULT_API_HASH
        assert headers[hdrs.AUTHORIZATION] == expected_basic
        assert headers[DEVICE_ID_HEADER] == "AP3A.240905.015"


class TestGetBaseUrl:
    def test_various_regions(self) -> None:
        assert get_base_url("rostov") == "https://mobile-api-rostov.tns-e.ru"
        assert get_base_url("penza") == "https://mobile-api-penza.tns-e.ru"
        assert get_base_url("nn") == "https://mobile-api-nn.tns-e.ru"
