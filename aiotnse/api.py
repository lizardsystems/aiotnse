"""TNS-Energo API wrapper."""
from __future__ import annotations

from typing import Any

from aiohttp import ClientSession

from .auth import AbstractTNSEAuth
from .const import (
    DEFAULT_API_PATH,
    DEFAULT_APP_VERSION,
    DEFAULT_PLATFORM,
    DEFAULT_REGION,
    DEVICE_ID,
    LOGGER,
)
from .exceptions import RequiredApiParamNotFound
from .helpers import build_request_headers, get_base_url, parse_api_response


async def _async_public_get(
    session: ClientSession,
    path: str,
    region: str = DEFAULT_REGION,
    params: dict[str, Any] | None = None,
) -> Any:
    """Make a GET request to a public API endpoint (no auth required)."""
    base_url = get_base_url(region)
    url = f"{base_url}/{DEFAULT_API_PATH}/{path}"
    headers = build_request_headers(region, DEVICE_ID)
    if params:
        LOGGER.debug("API request: GET /%s params=%s", path, params)
    else:
        LOGGER.debug("API request: GET /%s", path)
    async with session.get(url, headers=headers, params=params) as resp:
        data = await parse_api_response(resp)
        LOGGER.debug("API response: GET /%s -> %d: %s", path, resp.status, data)
        return data


async def async_get_regions(session: ClientSession) -> Any:
    """Get available regions.

    Standalone function that does not require authentication.
    Uses the default region endpoint as a bootstrap host.
    """
    return await _async_public_get(session, "contacts/regions")


async def async_check_version(
    session: ClientSession, region: str = DEFAULT_REGION
) -> Any:
    """Check app version compatibility.

    Standalone function that does not require authentication.
    """
    return await _async_public_get(
        session, "app/version", region=region, params={"version": DEFAULT_APP_VERSION}
    )


class TNSEApi:
    """TNS-Energo API client."""

    def __init__(self, auth: AbstractTNSEAuth) -> None:
        self._auth = auth

    async def _async_get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> Any:
        """Make GET request to API endpoint."""
        return await self._auth.request("GET", path, params=params)

    async def _async_post(
        self, path: str, json_data: dict[str, Any] | None = None
    ) -> Any:
        """Make POST request to API endpoint."""
        return await self._auth.request("POST", path, json=json_data)

    async def async_get_user_info(self) -> Any:
        """Get current user information."""
        return await self._async_get("user")

    async def async_get_accounts(self) -> Any:
        """Get list of user accounts."""
        return await self._async_get("accounts")

    async def async_get_account_info(self, account_id: int) -> Any:
        """Get detailed account information by ID."""
        return await self._async_get(f"accounts/{account_id}")

    async def async_get_main_page_debt_info(self) -> Any:
        """Get main page debt information."""
        return await self._async_get("main-page/debt/info")

    async def async_get_information(self, account: str) -> Any:
        """Get general information for an account."""
        return await self._async_get("information", {"account": account})

    async def async_get_counters(self, account: str) -> Any:
        """Get counters (meters) for an account."""
        return await self._async_get("counters", {"account": account})

    async def async_get_balance(self, account: str) -> Any:
        """Get current balance and payment info."""
        return await self._async_get("payments/new-balance", {"account": account})

    async def async_get_counter_readings(
        self, counter_id: str, account: str
    ) -> Any:
        """Get readings history for a specific counter."""
        return await self._async_get(
            f"counters/{counter_id}/readings", {"account": account}
        )

    async def async_send_readings(
        self, account: str, row_id: str, readings: list[str]
    ) -> Any:
        """Send meter readings."""
        if not readings:
            raise RequiredApiParamNotFound("Required API 'readings' parameter not found")
        return await self._async_post(
            "counters/send-readings",
            {
                "account": account,
                "rowId": row_id,
                "readings": readings,
                "platform": DEFAULT_PLATFORM,
            },
        )

    async def async_get_invoice_settings(self, account: str) -> Any:
        """Get invoice email settings for an account."""
        return await self._async_get("invoices/settings", {"account": account})

    async def async_get_invoices(self, account: str, year: int) -> Any:
        """Get list of invoices for an account and year."""
        return await self._async_get(
            "invoices", {"account": account, "year": year}
        )

    async def async_get_invoice_file(self, account: str, date: str) -> Any:
        """Get invoice file as base64 PDF."""
        return await self._async_get(
            "invoices/get-file", {"account": account, "date": date}
        )

    async def async_get_history(
        self, account: str, year: int, month: int
    ) -> Any:
        """Get account history (payments, readings, invoices)."""
        return await self._async_get(
            "history", {"account": account, "year": year, "month": month}
        )
