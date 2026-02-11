"""Tests for aiotnse auth module."""
from __future__ import annotations

from base64 import b64encode

import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses

from aiotnse import SimpleTNSEAuth
from aiotnse.const import DEVICE_ID, _DEVICE_IDS
from aiotnse.exceptions import TNSEApiError, TNSEAuthError, TNSETokenRefreshError
from tests.common import (
    ACCESS_TOKEN,
    API_URL,
    EMAIL,
    HEADERS,
    PASSWORD,
    REFRESH_TOKEN,
    REGION,
)
from tests.conftest import load_fixture


@pytest_asyncio.fixture
async def login_auth() -> SimpleTNSEAuth:
    """Create a SimpleTNSEAuth instance with login credentials."""
    async with aiohttp.ClientSession() as session:
        yield SimpleTNSEAuth(
            session=session,
            region=REGION,
            email=EMAIL,
            password=PASSWORD,
        )


@pytest_asyncio.fixture
async def no_creds_auth() -> SimpleTNSEAuth:
    """Create a SimpleTNSEAuth instance without credentials."""
    async with aiohttp.ClientSession() as session:
        yield SimpleTNSEAuth(session=session, region=REGION)


class TestSimpleTNSEAuth:
    async def test_login_success(
        self, login_auth: SimpleTNSEAuth, session_mock: aioresponses
    ) -> None:
        session_mock.post(
            f"{API_URL}/user/auth",
            payload=load_fixture("auth_response.json"),
            headers=HEADERS,
        )
        data = await login_auth.async_login()

        assert data["result"] is True
        assert data["statusCode"] == 200
        assert login_auth.access_token == "test_access_token_new"
        assert login_auth.refresh_token == "test_refresh_token_new"

    async def test_login_wrong_credentials(
        self, login_auth: SimpleTNSEAuth, session_mock: aioresponses
    ) -> None:
        session_mock.post(
            f"{API_URL}/user/auth",
            payload=load_fixture("auth_error_response.json"),
            headers=HEADERS,
        )
        with pytest.raises(TNSEAuthError, match="Неверный логин или пароль"):
            await login_auth.async_login()

    async def test_login_no_credentials(self, no_creds_auth: SimpleTNSEAuth) -> None:
        with pytest.raises(TNSEAuthError, match="Email and password are required"):
            await no_creds_auth.async_login()

    async def test_refresh_token_success(
        self, auth: SimpleTNSEAuth, session_mock: aioresponses
    ) -> None:
        session_mock.post(
            f"{API_URL}/user/refresh-token",
            payload=load_fixture("refresh_token_response.json"),
            headers=HEADERS,
        )
        data = await auth.async_refresh_token()

        assert data["result"] is True
        assert auth.access_token == "test_access_token_refreshed"

    async def test_refresh_token_no_token(
        self, no_creds_auth: SimpleTNSEAuth
    ) -> None:
        with pytest.raises(TNSETokenRefreshError, match="No refresh token available"):
            await no_creds_auth.async_refresh_token()

    async def test_logout(
        self, auth: SimpleTNSEAuth, session_mock: aioresponses
    ) -> None:
        session_mock.post(
            f"{API_URL}/user/logout",
            payload=load_fixture("logout_response.json"),
            headers=HEADERS,
        )
        data = await auth.async_logout()

        assert data["result"] is True
        assert auth.access_token is None
        assert auth.refresh_token is None

    async def test_request_error_response(
        self, auth: SimpleTNSEAuth, session_mock: aioresponses
    ) -> None:
        """Verify request() raises TNSEApiError on error responses."""
        error_payload = {
            "result": False,
            "statusCode": 400,
            "error": {"code": 100, "description": "Some API error"},
        }
        session_mock.get(
            f"{API_URL}/some-endpoint",
            payload=error_payload,
            headers=HEADERS,
        )
        with pytest.raises(TNSEApiError, match="Some API error"):
            await auth.request("GET", "some-endpoint")

    async def test_basic_auth_rostov(self, auth: SimpleTNSEAuth) -> None:
        expected = "Basic " + b64encode(b"mobile-api-rostov:mobile-api-rostov").decode()
        headers = auth._build_headers()
        assert headers["Authorization"] == expected

    async def test_basic_auth_penza(self) -> None:
        async with aiohttp.ClientSession() as session:
            penza_auth = SimpleTNSEAuth(session=session, region="penza")
        expected = "Basic " + b64encode(b"mobile-api-penza:mobile-api-penza").decode()
        headers = penza_auth._build_headers()
        assert headers["Authorization"] == expected
        assert penza_auth.base_url == "https://mobile-api-penza.tns-e.ru"

    async def test_region_property(self, auth: SimpleTNSEAuth) -> None:
        assert auth.region == REGION

    async def test_set_region(self, auth: SimpleTNSEAuth) -> None:
        auth.region = "nn"
        assert auth.region == "nn"
        assert auth.base_url == "https://mobile-api-nn.tns-e.ru"

    async def test_device_id_in_headers(self, auth: SimpleTNSEAuth) -> None:
        headers = auth._build_headers()
        assert headers["x-device-id"] == DEVICE_ID
        assert DEVICE_ID in _DEVICE_IDS
