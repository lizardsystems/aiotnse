"""Tests for aiotnse auth module."""
from __future__ import annotations

from base64 import b64encode
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import aiohttp
import pytest
import pytest_asyncio

from aiotnse import SimpleTNSEAuth
from aiotnse.const import DEVICE_ID, _DEVICE_IDS
from aiotnse.exceptions import TNSEApiError, TNSEAuthError, TNSETokenRefreshError
from tests.aiohttp_mock import AiohttpClientMocker
from tests.common import (
    ACCESS_TOKEN,
    ACCESS_TOKEN_EXPIRES,
    API_URL,
    EMAIL,
    HEADERS,
    PASSWORD,
    REFRESH_TOKEN,
    REFRESH_TOKEN_EXPIRES,
    REGION,
)
from tests.conftest import load_fixture


@pytest_asyncio.fixture
async def login_auth(aioclient_mock: AiohttpClientMocker) -> SimpleTNSEAuth:
    """Create a SimpleTNSEAuth instance with login credentials."""
    session = aioclient_mock.create_session()
    try:
        yield SimpleTNSEAuth(
            session=session,
            region=REGION,
            email=EMAIL,
            password=PASSWORD,
        )
    finally:
        await session.close()


@pytest_asyncio.fixture
async def no_creds_auth(aioclient_mock: AiohttpClientMocker) -> SimpleTNSEAuth:
    """Create a SimpleTNSEAuth instance without credentials."""
    session = aioclient_mock.create_session()
    try:
        yield SimpleTNSEAuth(session=session, region=REGION)
    finally:
        await session.close()


class TestSimpleTNSEAuth:
    async def test_login_success(
        self, login_auth: SimpleTNSEAuth, aioclient_mock: AiohttpClientMocker
    ) -> None:
        aioclient_mock.post(
            f"{API_URL}/user/auth",
            json=load_fixture("auth_response.json"),
            headers=HEADERS,
        )
        data = await login_auth.async_login()

        assert data["accessToken"] == "test_access_token_new"
        assert login_auth.access_token == "test_access_token_new"
        assert login_auth.refresh_token == "test_refresh_token_new"
        assert login_auth.access_token_expires == datetime.fromisoformat(
            ACCESS_TOKEN_EXPIRES
        )
        assert login_auth.refresh_token_expires == datetime.fromisoformat(
            REFRESH_TOKEN_EXPIRES
        )

    async def test_login_wrong_credentials(
        self, login_auth: SimpleTNSEAuth, aioclient_mock: AiohttpClientMocker
    ) -> None:
        aioclient_mock.post(
            f"{API_URL}/user/auth",
            json=load_fixture("auth_error_response.json"),
            headers=HEADERS,
        )
        with pytest.raises(TNSEAuthError, match="Неверный логин или пароль"):
            await login_auth.async_login()

    async def test_login_no_credentials(self, no_creds_auth: SimpleTNSEAuth) -> None:
        with pytest.raises(TNSEAuthError, match="Email and password are required"):
            await no_creds_auth.async_login()

    async def test_refresh_token_success(
        self, auth: SimpleTNSEAuth, aioclient_mock: AiohttpClientMocker
    ) -> None:
        aioclient_mock.post(
            f"{API_URL}/user/refresh-token",
            json=load_fixture("refresh_token_response.json"),
            headers=HEADERS,
        )
        data = await auth.async_refresh_token()

        assert data["accessToken"] == "test_access_token_refreshed"
        assert auth.access_token == "test_access_token_refreshed"
        assert auth.access_token_expires == datetime.fromisoformat(
            "2026-06-09 21:06:40"
        )

    async def test_refresh_token_no_token(
        self, no_creds_auth: SimpleTNSEAuth
    ) -> None:
        with pytest.raises(TNSETokenRefreshError, match="No refresh token available"):
            await no_creds_auth.async_refresh_token()

    async def test_logout(
        self, auth: SimpleTNSEAuth, aioclient_mock: AiohttpClientMocker
    ) -> None:
        aioclient_mock.post(
            f"{API_URL}/user/logout",
            json=load_fixture("logout_response.json"),
            headers=HEADERS,
        )
        data = await auth.async_logout()

        assert data == []
        assert auth.access_token is None
        assert auth.refresh_token is None
        assert auth.access_token_expires is None
        assert auth.refresh_token_expires is None

    async def test_request_error_response(
        self, auth: SimpleTNSEAuth, aioclient_mock: AiohttpClientMocker
    ) -> None:
        """Verify request() raises TNSEApiError on error responses."""
        error_payload = {
            "result": False,
            "statusCode": 400,
            "error": {"code": 100, "description": "Some API error"},
        }
        aioclient_mock.get(
            f"{API_URL}/some-endpoint",
            json=error_payload,
            headers=HEADERS,
        )
        with pytest.raises(TNSEApiError, match="Some API error"):
            await auth.request("GET", "some-endpoint")

    async def test_request_http_error(
        self, auth: SimpleTNSEAuth, aioclient_mock: AiohttpClientMocker
    ) -> None:
        """Verify request() wraps HTTP errors in TNSEApiError."""
        aioclient_mock.get(
            f"{API_URL}/some-endpoint",
            status=500,
        )
        with pytest.raises(TNSEApiError, match="500"):
            await auth.request("GET", "some-endpoint")

    async def test_request_http_error_with_body(
        self, auth: SimpleTNSEAuth, aioclient_mock: AiohttpClientMocker
    ) -> None:
        """Verify request() includes API error description from response body."""
        aioclient_mock.get(
            f"{API_URL}/some-endpoint",
            status=400,
            json={
                "result": False,
                "error": {"description": "Account not found"},
            },
        )
        with pytest.raises(TNSEApiError, match="Account not found.*400"):
            await auth.request("GET", "some-endpoint")

    async def test_login_http_error(
        self, login_auth: SimpleTNSEAuth, aioclient_mock: AiohttpClientMocker
    ) -> None:
        """A login error without a JSON body is a transient API error."""
        aioclient_mock.post(
            f"{API_URL}/user/auth",
            status=403,
        )
        with pytest.raises(TNSEApiError, match="403") as exc_info:
            await login_auth.async_login()
        assert not isinstance(exc_info.value, TNSEAuthError)

    @pytest.mark.parametrize(
        ("status", "kwargs"),
        [
            (502, {"text": "<html>502 Bad Gateway</html>", "headers": {"Content-Type": "text/html"}}),
            (500, {"json": {"result": False, "error": {"description": "Internal error"}}}),
            (200, {"text": "<html>maintenance</html>", "headers": {"Content-Type": "text/html"}}),
        ],
    )
    async def test_login_server_failure_is_not_auth_error(
        self,
        login_auth: SimpleTNSEAuth,
        aioclient_mock: AiohttpClientMocker,
        status: int,
        kwargs: dict,
    ) -> None:
        """5xx and non-JSON login responses do not mean wrong credentials."""
        aioclient_mock.post(f"{API_URL}/user/auth", status=status, **kwargs)
        with pytest.raises(TNSEApiError) as exc_info:
            await login_auth.async_login()
        assert not isinstance(exc_info.value, TNSEAuthError)

    async def test_login_http_error_with_body(
        self, login_auth: SimpleTNSEAuth, aioclient_mock: AiohttpClientMocker
    ) -> None:
        """Verify async_login includes API error description from response body."""
        aioclient_mock.post(
            f"{API_URL}/user/auth",
            status=401,
            json={
                "result": False,
                "error": {"description": "Token expired"},
            },
        )
        with pytest.raises(TNSEAuthError, match="Token expired.*401"):
            await login_auth.async_login()

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

    async def test_token_update_callback_on_login(
        self, aioclient_mock: AiohttpClientMocker
    ) -> None:
        """Test that token_update_callback is called after login."""
        callback = MagicMock()
        async with aioclient_mock.create_session() as session:
            auth = SimpleTNSEAuth(
                session=session,
                region=REGION,
                email=EMAIL,
                password=PASSWORD,
                token_update_callback=callback,
            )
            aioclient_mock.post(
                f"{API_URL}/user/auth",
                json=load_fixture("auth_response.json"),
                headers=HEADERS,
            )
            await auth.async_login()

        callback.assert_called_once()
        token_data = callback.call_args[0][0]
        assert token_data["access_token"] == "test_access_token_new"
        assert token_data["refresh_token"] == "test_refresh_token_new"
        assert token_data["access_token_expires"] is not None
        assert token_data["refresh_token_expires"] is not None

    async def test_token_update_callback_on_refresh(
        self, auth: SimpleTNSEAuth, aioclient_mock: AiohttpClientMocker
    ) -> None:
        """Test that token_update_callback is called after refresh."""
        callback = MagicMock()
        auth._token_update_callback = callback
        aioclient_mock.post(
            f"{API_URL}/user/refresh-token",
            json=load_fixture("refresh_token_response.json"),
            headers=HEADERS,
        )
        await auth.async_refresh_token()

        callback.assert_called_once()
        token_data = callback.call_args[0][0]
        assert token_data["access_token"] == "test_access_token_refreshed"
        assert token_data["access_token_expires"] is not None

    async def test_get_access_token_valid(self) -> None:
        """Test async_get_access_token returns token when not expired."""
        async with aiohttp.ClientSession() as session:
            auth = SimpleTNSEAuth(
                session=session,
                region=REGION,
                access_token=ACCESS_TOKEN,
                refresh_token=REFRESH_TOKEN,
                access_token_expires=datetime.now() + timedelta(hours=1),
            )
            token = await auth.async_get_access_token()
        assert token == ACCESS_TOKEN

    async def test_get_access_token_expired_triggers_refresh(
        self, aioclient_mock: AiohttpClientMocker
    ) -> None:
        """Test async_get_access_token refreshes when access token is expired."""
        async with aioclient_mock.create_session() as session:
            auth = SimpleTNSEAuth(
                session=session,
                region=REGION,
                access_token=ACCESS_TOKEN,
                refresh_token=REFRESH_TOKEN,
                access_token_expires=datetime.now() - timedelta(hours=1),
                refresh_token_expires=datetime.now() + timedelta(days=30),
            )
            aioclient_mock.post(
                f"{API_URL}/user/refresh-token",
                json=load_fixture("refresh_token_response.json"),
                headers=HEADERS,
            )
            token = await auth.async_get_access_token()
        assert token == "test_access_token_refreshed"

    async def test_get_access_token_both_expired_triggers_login(
        self, aioclient_mock: AiohttpClientMocker
    ) -> None:
        """Test async_get_access_token re-logs in when both tokens are expired."""
        async with aioclient_mock.create_session() as session:
            auth = SimpleTNSEAuth(
                session=session,
                region=REGION,
                email=EMAIL,
                password=PASSWORD,
                access_token=ACCESS_TOKEN,
                refresh_token=REFRESH_TOKEN,
                access_token_expires=datetime.now() - timedelta(hours=1),
                refresh_token_expires=datetime.now() - timedelta(hours=1),
            )
            aioclient_mock.post(
                f"{API_URL}/user/auth",
                json=load_fixture("auth_response.json"),
                headers=HEADERS,
            )
            token = await auth.async_get_access_token()
        assert token == "test_access_token_new"

    async def test_get_access_token_refresh_rejected_falls_back_to_login(
        self, aioclient_mock: AiohttpClientMocker
    ) -> None:
        """Refresh rejected by server (403/HTML) falls back to login.

        Regression test for hass-tnse issue #14: the refresh token is still
        valid by local timestamp, but the server answers the refresh request
        with HTTP 403 and an HTML body. With stored credentials the client
        must re-login instead of surfacing a token refresh error.
        """
        async with aioclient_mock.create_session() as session:
            auth = SimpleTNSEAuth(
                session=session,
                region=REGION,
                email=EMAIL,
                password=PASSWORD,
                access_token=ACCESS_TOKEN,
                refresh_token=REFRESH_TOKEN,
                access_token_expires=datetime.now() - timedelta(hours=1),
                refresh_token_expires=datetime.now() + timedelta(days=30),
            )
            aioclient_mock.post(
                f"{API_URL}/user/refresh-token",
                status=403,
                text="<html><body>403 Forbidden</body></html>",
                headers={"Content-Type": "text/html"},
            )
            aioclient_mock.post(
                f"{API_URL}/user/auth",
                json=load_fixture("auth_response.json"),
                headers=HEADERS,
            )
            token = await auth.async_get_access_token()
        assert token == "test_access_token_new"

    async def test_get_access_token_refresh_rejected_login_server_down(
        self, aioclient_mock: AiohttpClientMocker
    ) -> None:
        """Refresh rejected and login hits a 5xx: transient error, not auth."""
        async with aioclient_mock.create_session() as session:
            auth = SimpleTNSEAuth(
                session=session,
                region=REGION,
                email=EMAIL,
                password=PASSWORD,
                access_token=ACCESS_TOKEN,
                refresh_token=REFRESH_TOKEN,
                access_token_expires=datetime.now() - timedelta(hours=1),
                refresh_token_expires=datetime.now() + timedelta(days=30),
            )
            aioclient_mock.post(
                f"{API_URL}/user/refresh-token",
                status=403,
                text="<html><body>403 Forbidden</body></html>",
                headers={"Content-Type": "text/html"},
            )
            aioclient_mock.post(
                f"{API_URL}/user/auth",
                status=503,
                text="<html>503 Service Unavailable</html>",
                headers={"Content-Type": "text/html"},
            )
            with pytest.raises(TNSEApiError) as exc_info:
                await auth.async_get_access_token()
        assert not isinstance(exc_info.value, TNSEAuthError)

    async def test_get_access_token_refresh_rejected_no_creds_raises(
        self, aioclient_mock: AiohttpClientMocker
    ) -> None:
        """Refresh rejected with no credentials has no recovery path."""
        async with aioclient_mock.create_session() as session:
            auth = SimpleTNSEAuth(
                session=session,
                region=REGION,
                access_token=ACCESS_TOKEN,
                refresh_token=REFRESH_TOKEN,
                access_token_expires=datetime.now() - timedelta(hours=1),
                refresh_token_expires=datetime.now() + timedelta(days=30),
            )
            aioclient_mock.post(
                f"{API_URL}/user/refresh-token",
                status=403,
                text="<html><body>403 Forbidden</body></html>",
                headers={"Content-Type": "text/html"},
            )
            with pytest.raises(TNSETokenRefreshError, match="403"):
                await auth.async_get_access_token()

    async def test_get_access_token_no_expiration(self) -> None:
        """Test async_get_access_token returns token when no expiration set."""
        async with aiohttp.ClientSession() as session:
            auth = SimpleTNSEAuth(
                session=session,
                region=REGION,
                access_token=ACCESS_TOKEN,
                refresh_token=REFRESH_TOKEN,
            )
            token = await auth.async_get_access_token()
        assert token == ACCESS_TOKEN
