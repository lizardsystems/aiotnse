"""TNS-Energo API Auth wrapper."""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from typing import Any

from aiohttp import ClientSession

from .const import (
    BEARER_HEADER,
    DEFAULT_API_PATH,
    DEFAULT_PLATFORM,
    DEVICE_ID,
    LOGGER,
)
from .exceptions import TNSEAuthError, TNSETokenRefreshError
from .helpers import build_request_headers, get_base_url, parse_api_response


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

        if params := kwargs.get("params"):
            LOGGER.debug("API request: %s /%s params=%s", method, path, params)
        elif json_body := kwargs.get("json"):
            LOGGER.debug("API request: %s /%s json=%s", method, path, json_body)
        else:
            LOGGER.debug("API request: %s /%s", method, path)

        async with self._session.request(
            method, url, **kwargs, headers=headers
        ) as resp:
            data = await parse_api_response(resp)
            LOGGER.debug(
                "API response: %s /%s -> %d: %s", method, path, resp.status, data
            )
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
        access_token_expires: datetime | None = None,
        refresh_token_expires: datetime | None = None,
        token_update_callback: Callable[[dict[str, Any]], None] | None = None,
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
        self._access_token_expires = access_token_expires
        self._refresh_token_expires = refresh_token_expires
        self._token_update_callback = token_update_callback
        self._token_lock = asyncio.Lock()

    @property
    def access_token(self) -> str | None:
        """Return current access token."""
        return self._access_token

    @property
    def refresh_token(self) -> str | None:
        """Return current refresh token."""
        return self._refresh_token

    @property
    def access_token_expires(self) -> datetime | None:
        """Return access token expiration time."""
        return self._access_token_expires

    @property
    def refresh_token_expires(self) -> datetime | None:
        """Return refresh token expiration time."""
        return self._refresh_token_expires

    async def async_get_access_token(self) -> str | None:
        """Return a valid access token, refreshing if needed."""
        if self._access_token and (
            not self._access_token_expires
            or datetime.now() < self._access_token_expires
        ):
            return self._access_token

        async with self._token_lock:
            # Re-check after acquiring lock — another coroutine may have refreshed
            if self._access_token and (
                not self._access_token_expires
                or datetime.now() < self._access_token_expires
            ):
                return self._access_token

            # Access token expired or missing — try refresh
            if self._refresh_token and (
                not self._refresh_token_expires
                or datetime.now() < self._refresh_token_expires
            ):
                LOGGER.debug("Access token expired, refreshing via refresh token")
                await self.async_refresh_token()
                return self._access_token

            # Refresh token also expired — try login
            if self._email and self._password:
                LOGGER.debug("Both tokens expired, re-authenticating")
                await self.async_login()
                return self._access_token

            LOGGER.debug("No valid token and no recovery path available")

        return self._access_token

    async def _async_auth_request(
        self,
        path: str,
        json_data: dict[str, Any],
        error_class: type[TNSEAuthError],
        default_error: str,
    ) -> Any:
        """Make an auth POST request without Bearer token."""
        url = self._build_url(path)
        LOGGER.debug(
            "Auth request: POST /%s keys=%s", path, list(json_data.keys())
        )
        async with self._session.request(
            "POST",
            url,
            json=json_data,
            headers=self._build_headers(),
        ) as resp:
            data = await parse_api_response(
                resp,
                error_class=error_class,
                default_error=default_error,
            )
            LOGGER.debug(
                "Auth response: POST /%s -> %d: %s", path, resp.status, data
            )
            return data

    async def async_login(self) -> Any:
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

        self._access_token = data["accessToken"]
        self._refresh_token = data["refreshToken"]
        self._access_token_expires = datetime.fromisoformat(
            data["accessTokenExpires"]
        )
        self._refresh_token_expires = datetime.fromisoformat(
            data["refreshTokenExpires"]
        )
        self._notify_token_update()

        LOGGER.debug("Login successful")
        return data

    async def async_refresh_token(self) -> Any:
        """Refresh the access token."""
        if not self._refresh_token:
            raise TNSETokenRefreshError("No refresh token available")

        data = await self._async_auth_request(
            "user/refresh-token",
            {"refreshToken": self._refresh_token},
            TNSETokenRefreshError,
            "Token refresh failed",
        )

        self._access_token = data["accessToken"]
        self._access_token_expires = datetime.fromisoformat(
            data["accessTokenExpires"]
        )
        self._notify_token_update()

        LOGGER.debug("Token refresh successful")
        return data

    async def async_logout(self) -> Any:
        """Logout and invalidate tokens."""
        data = await self.request("POST", "user/logout")

        self._access_token = None
        self._refresh_token = None
        self._access_token_expires = None
        self._refresh_token_expires = None

        LOGGER.debug("Logout successful")
        return data

    def _notify_token_update(self) -> None:
        """Notify callback about token changes."""
        if self._token_update_callback:
            self._token_update_callback({
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
                "access_token_expires": (
                    self._access_token_expires.isoformat()
                    if self._access_token_expires
                    else None
                ),
                "refresh_token_expires": (
                    self._refresh_token_expires.isoformat()
                    if self._refresh_token_expires
                    else None
                ),
            })
