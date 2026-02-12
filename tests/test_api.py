"""Tests for aiotnse API module."""
from __future__ import annotations

import aiohttp
import pytest
from aioresponses import aioresponses

from aiotnse import TNSEApi
from aiotnse.api import async_get_regions
from aiotnse.const import DEFAULT_APP_VERSION
from aiotnse.exceptions import RequiredApiParamNotFound, TNSEApiError
from tests.common import (
    ACCOUNT,
    ACCOUNT_ID,
    API_URL,
    COUNTER_ID,
    HEADERS,
    ROW_ID,
)
from tests.conftest import load_fixture


class TestAsyncGetRegions:
    async def test_get_regions(self) -> None:
        """Test standalone async_get_regions() without auth."""
        with aioresponses() as mock:
            mock.get(
                f"{API_URL}/contacts/regions",
                payload=load_fixture("regions_response.json"),
                headers=HEADERS,
            )
            async with aiohttp.ClientSession() as session:
                data = await async_get_regions(session)

        assert data["result"] is True
        assert len(data["data"]) > 0
        codes = [r["code"] for r in data["data"]]
        assert "rostov" in codes


    async def test_get_regions_http_error(self) -> None:
        """Test async_get_regions wraps HTTP errors in TNSEApiError."""
        with aioresponses() as mock:
            mock.get(
                f"{API_URL}/contacts/regions",
                status=403,
            )
            async with aiohttp.ClientSession() as session:
                with pytest.raises(TNSEApiError, match="403"):
                    await async_get_regions(session)


class TestTNSEApi:
    async def test_check_version(self, api: TNSEApi, session_mock: aioresponses) -> None:
        session_mock.get(
            f"{API_URL}/app/version?version={DEFAULT_APP_VERSION}",
            payload=load_fixture("app_version_response.json"),
            headers=HEADERS,
        )
        data = await api.async_check_version()

        assert data["result"] is True
        assert data["data"]["status"] == 1

    async def test_get_user_info(self, api: TNSEApi, session_mock: aioresponses) -> None:
        session_mock.get(
            f"{API_URL}/user",
            payload=load_fixture("user_info_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_user_info()

        assert data["result"] is True
        assert data["data"]["email"] == "user@example.com"
        assert data["data"]["region"] == "rostov"

    async def test_get_accounts(self, api: TNSEApi, session_mock: aioresponses) -> None:
        session_mock.get(
            f"{API_URL}/accounts",
            payload=load_fixture("accounts_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_accounts()

        assert data["result"] is True
        assert len(data["data"]) == 2
        assert data["data"][0]["id"] == ACCOUNT_ID
        assert data["data"][0]["number"] == ACCOUNT

    async def test_get_account_info(self, api: TNSEApi, session_mock: aioresponses) -> None:
        session_mock.get(
            f"{API_URL}/accounts/{ACCOUNT_ID}",
            payload=load_fixture("account_info_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_account_info(ACCOUNT_ID)

        assert data["result"] is True
        assert data["data"]["id"] == ACCOUNT_ID
        assert data["data"]["number"] == ACCOUNT
        assert data["data"]["address"]
        assert len(data["data"]["countersInfo"]) > 0

    async def test_get_main_page_debt_info(self, api: TNSEApi, session_mock: aioresponses) -> None:
        session_mock.get(
            f"{API_URL}/main-page/debt/info",
            payload=load_fixture("main_page_debt_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_main_page_debt_info()

        assert data["result"] is True

    async def test_get_information(self, api: TNSEApi, session_mock: aioresponses) -> None:
        session_mock.get(
            f"{API_URL}/information?account={ACCOUNT}",
            payload=load_fixture("information_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_information(ACCOUNT)

        assert data["result"] is True

    async def test_get_counters(self, api: TNSEApi, session_mock: aioresponses) -> None:
        session_mock.get(
            f"{API_URL}/counters?account={ACCOUNT}",
            payload=load_fixture("counters_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_counters(ACCOUNT)

        assert data["result"] is True
        assert len(data["data"]) > 0
        counter = data["data"][0]
        assert counter["counterId"] == COUNTER_ID
        assert counter["rowId"] == ROW_ID
        assert counter["tariff"] == 2
        assert len(counter["lastReadings"]) == 2

    async def test_get_balance(self, api: TNSEApi, session_mock: aioresponses) -> None:
        session_mock.get(
            f"{API_URL}/payments/new-balance?account={ACCOUNT}",
            payload=load_fixture("balance_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_balance(ACCOUNT)

        assert data["result"] is True
        assert data["data"]["sumToPay"] == 1500.5

    async def test_get_counter_readings(self, api: TNSEApi, session_mock: aioresponses) -> None:
        session_mock.get(
            f"{API_URL}/counters/{COUNTER_ID}/readings?account={ACCOUNT}",
            payload=load_fixture("counter_readings_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_counter_readings(COUNTER_ID, ACCOUNT)

        assert data["result"] is True
        assert len(data["data"]) > 0
        reading = data["data"][0]
        assert reading["date"]
        assert len(reading["readings"]) == 2

    async def test_send_readings(self, api: TNSEApi, session_mock: aioresponses) -> None:
        session_mock.post(
            f"{API_URL}/counters/send-readings",
            payload=load_fixture("send_readings_response.json"),
            headers=HEADERS,
        )
        data = await api.async_send_readings(ACCOUNT, ROW_ID, ["2690", "1023"])

        assert data["result"] is True

    async def test_send_readings_empty(self, api: TNSEApi) -> None:
        with pytest.raises(RequiredApiParamNotFound):
            await api.async_send_readings(ACCOUNT, ROW_ID, [])

    async def test_get_invoice_settings(self, api: TNSEApi, session_mock: aioresponses) -> None:
        session_mock.get(
            f"{API_URL}/invoices/settings?account={ACCOUNT}",
            payload=load_fixture("invoice_settings_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_invoice_settings(ACCOUNT)

        assert data["result"] is True
        assert data["data"]["email"] == "user@example.com"
        assert data["data"]["status"] is True

    async def test_get_invoices(self, api: TNSEApi, session_mock: aioresponses) -> None:
        session_mock.get(
            f"{API_URL}/invoices?account={ACCOUNT}&year=2026",
            payload=load_fixture("invoices_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_invoices(ACCOUNT, 2026)

        assert data["result"] is True
        assert len(data["data"]) > 0
        assert data["data"][0]["date"] == "01.01.2026"

    async def test_get_invoice_file(self, api: TNSEApi, session_mock: aioresponses) -> None:
        session_mock.get(
            f"{API_URL}/invoices/get-file?account={ACCOUNT}&date=01.01.2026",
            payload=load_fixture("invoice_file_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_invoice_file(ACCOUNT, "01.01.2026")

        assert data["result"] is True
        assert data["data"]["file"]

    async def test_get_history(self, api: TNSEApi, session_mock: aioresponses) -> None:
        session_mock.get(
            f"{API_URL}/history?account={ACCOUNT}&year=2026&month=2",
            payload=load_fixture("history_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_history(ACCOUNT, 2026, 2)

        assert data["result"] is True
        assert "filters" in data["data"]
        assert "items" in data["data"]
        assert len(data["data"]["items"]) > 0
