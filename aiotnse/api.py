"""TNS-Energo API wrapper."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Union

from aiohttp import hdrs, MultipartWriter

from .auth import AbstractTNSEAuth
from .const import DEFAULT_BASE_URL, DEFAULT_API_VERSION
from .exceptions import RequiredApiParamNotFound
from .helpers import get_region


class TNSEApi:
    """Class to communicate with the TNS-Energo API."""
    _version: str = DEFAULT_API_VERSION
    _api_url: str

    def __init__(self, auth: AbstractTNSEAuth):
        """Initialize the API and store the auth."""
        self._auth = auth
        self._api_url = f"{DEFAULT_BASE_URL}/version/{self._version}/Android/mobile"

    async def _async_get(self, url: str) -> Union[dict[str, Any], list[dict[str, Any]]]:
        """Make async get request to api endpoint"""
        return await self._auth.request(hdrs.METH_GET, f"{self._api_url}/{url}")

    async def _async_post(self, url: str, **kwargs) -> Union[dict[str, Any], list[dict[str, Any]]]:
        """Make async get request to api endpoint"""
        with MultipartWriter("form-data", boundary=str(uuid.uuid1())) as mpwriter:
            for name in kwargs:
                part = mpwriter.append_json(kwargs[name])
                part.set_content_disposition("form-data", name=name)
                part.headers[hdrs.CONTENT_TRANSFER_ENCODING] = "binary"
                part.headers[hdrs.CONTENT_TYPE] = "multipart/form-data; charset=utf-8"
            return await self._auth.request(hdrs.METH_POST, f"{self._api_url}/{url}", data=mpwriter)

    async def async_is_registered(self, account: str) -> dict[str, Any]:
        """Check if account is registered."""
        region = get_region(account)
        _url = f"region/{region}/action/isLsRegisteredAndHasPayments/{account}/"
        return await self._async_get(_url)

    async def async_get_account_status(self, account: str) -> dict[str, Any]:
        """Get account status."""
        _url = f"delegation/getLsStatus/{account}/"
        return await self._async_get(_url)

    async def async_get_accounts(self, account: str) -> dict[str, Any]:
        """Get accounts for master account."""
        _url = f"delegation/getLSListByLs/{account}/"
        data = {"for_ls": account, "dlogin": 0}
        return await self._async_post(_url, data=data)

    async def async_get_main_page_info(self, account: str) -> dict[str, Any]:
        """Get main page for account."""
        region = get_region(account)
        _url = f"region/{region}/action/getMainPage/ls/{account}/json/"
        return await self._async_get(_url)

    async def async_get_general_info(self, account: str) -> dict[str, Any]:
        """Get general info about account."""
        region = get_region(account)
        _url = f"region/{region}/action/getInfo/ls/{account}/json/"
        return await self._async_get(_url)

    async def async_get_readings_history(self, account: str) -> dict[str, Any]:
        """Get readings history for account."""
        region = get_region(account)
        _url = f"region/{region}/action/getReadingsHistPage/ls/{account}/json/"
        return await self._async_get(_url)

    async def async_get_current_payment(self, account: str) -> dict[str, Any]:
        """Get current balance for account."""
        region = get_region(account)
        _url = f"region/{region}/action/getPaymentPage/ls/{account}/json/"
        return await self._async_get(_url)

    async def async_get_payments_history(self, account: str) -> dict[str, Any]:
        """Get payments history for account."""
        region = get_region(account)
        _url = f"region/{region}/action/getPaymentsHistPage/ls/{account}/json/"
        return await self._async_get(_url)

    async def async_get_bill(self, account: str, date: datetime) -> dict[str, Any]:
        """Get general info about account."""
        region = get_region(account)
        _url = f"region/{region}/action/getBill/ls/{account}/date/{date:%d.%m.%Y}/json/"
        return await self._async_get(_url)

    async def async_get_latest_readings(self, account: str) -> dict[str, Any]:
        """Get last readings for account."""
        region = get_region(account)
        _url = f"region/{region}/action/getSendReadingsPage/ls/{account}/json/"
        return await self._async_get(_url)

    async def async_send_readings(self, account: str, readings: list[dict[str, Any]]) -> dict[str, Any]:
        region = get_region(account)
        _url = f"region/{region}/action/sendReadings/ls/{account}/json/"
        if not readings:
            raise RequiredApiParamNotFound("Required API 'readings' parameter not found")
        return await self._async_post(_url, readings=readings)
