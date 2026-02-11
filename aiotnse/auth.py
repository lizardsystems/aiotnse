"""TNS-Energo API Auth wrapper."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from aiohttp import ClientSession

from .const import (
    BEARER_HEADER,
    DEFAULT_API_PATH,
    DEFAULT_PLATFORM,
    DEVICE_ID,
    LOGGER,
)
from .exceptions import TNSEApiError, TNSEAuthError, TNSETokenRefreshError
from .helpers import build_request_headers, get_base_url


class AbstractTNSEAuth(ABC):
    """Abstract class to make authenticated requests."""

    def __init__(self, session: ClientSession, *, region: str) -> None:
        self._session = session
        self._region = region

    @property
    def region(self) -> str:
        """Return current region."""
        return self._region

    @region.setter
    def region(self, value: str) -> None:
        """Set current region."""
        self._region = value

    @property
    def base_url(self) -> str:
        """Return base URL for the current region."""
        return get_base_url(self._region)

    def _build_url(self, path: str) -> str:
        """Build full API URL for the given path."""
        return f"{self.base_url}/{DEFAULT_API_PATH}/{path}"

    def _build_headers(self) -> dict[str, str]:
        """Build common request headers."""
        return build_request_headers(self._region, DEVICE_ID)

    @abstractmethod
    async def async_get_access_token(self) -> str | None:
        """Return a valid access token."""

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make a request with proper authorization headers."""
        headers = {**kwargs.pop("headers", {}), **self._build_headers()}

        access_token = await self.async_get_access_token()
        if access_token:
            headers[BEARER_HEADER] = f"Bearer {access_token}"

        url = self._build_url(path)

        LOGGER.debug("Request %s %s", method, url)
        async with self._session.request(
            method, url, **kwargs, headers=headers, raise_for_status=True
        ) as resp:
            data = await resp.json()
            LOGGER.debug("Response status=%s", resp.status)

        if isinstance(data, dict) and not data.get("result"):
            error = data.get("error", {})
            raise TNSEApiError(error.get("description", "API request failed"))

        return data


class SimpleTNSEAuth(AbstractTNSEAuth):
    """Auth implementation with email/password login and JWT tokens."""

    def __init__(
        self,
        session: ClientSession,
        *,
        region: str,
        email: str | None = None,
        password: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        """Initialize the auth.

        Two modes:
        1. Login: provide email + password, then call async_login().
        2. Session restore: provide access_token + refresh_token.
        """
        super().__init__(session, region=region)
        self._email = email
        self._password = password
        self._access_token = access_token
        self._refresh_token = refresh_token

    @property
    def access_token(self) -> str | None:
        """Return current access token."""
        return self._access_token

    @property
    def refresh_token(self) -> str | None:
        """Return current refresh token."""
        return self._refresh_token

    async def async_get_access_token(self) -> str | None:
        """Return a valid access token."""
        return self._access_token

    async def _async_auth_request(
        self,
        path: str,
        json_data: dict[str, Any],
        error_class: type[TNSEAuthError],
        default_error: str,
    ) -> dict[str, Any]:
        """Make an auth POST request without Bearer token."""
        url = self._build_url(path)
        LOGGER.debug("Auth request to %s", url)
        async with self._session.request(
            "POST",
            url,
            json=json_data,
            headers=self._build_headers(),
            raise_for_status=True,
        ) as resp:
            data = await resp.json()

        if not data.get("result"):
            error = data.get("error", {})
            raise error_class(error.get("description", default_error))

        return data

    async def async_login(self) -> dict[str, Any]:
        """Authenticate with email and password."""
        if not self._email or not self._password:
            raise TNSEAuthError("Email and password are required for login")

        data = await self._async_auth_request(
            "user/auth",
            {
                "login": self._email,
                "authType": "email",
                "password": self._password,
                "region": self._region,
                "platform": DEFAULT_PLATFORM,
            },
            TNSEAuthError,
            "Authentication failed",
        )

        token_data = data["data"]
        self._access_token = token_data["accessToken"]
        self._refresh_token = token_data["refreshToken"]

        LOGGER.debug("Login successful")
        return data

    async def async_refresh_token(self) -> dict[str, Any]:
        """Refresh the access token."""
        if not self._refresh_token:
            raise TNSETokenRefreshError("No refresh token available")

        data = await self._async_auth_request(
            "user/refresh-token",
            {"refreshToken": self._refresh_token},
            TNSETokenRefreshError,
            "Token refresh failed",
        )

        self._access_token = data["data"]["accessToken"]

        LOGGER.debug("Token refresh successful")
        return data

    async def async_logout(self) -> dict[str, Any]:
        """Logout and invalidate tokens."""
        data = await self.request("POST", "user/logout")

        self._access_token = None
        self._refresh_token = None

        LOGGER.debug("Logout successful")
        return data
