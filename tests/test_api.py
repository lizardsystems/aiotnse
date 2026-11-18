"""Tests for aiotnse API module."""
from __future__ import annotations

import pytest

from aiotnse import TNSEApi
from aiotnse.api import async_check_version, async_get_regions
from aiotnse.const import DEFAULT_APP_VERSION
from aiotnse.exceptions import RequiredApiParamNotFound, TNSEApiError
from tests.aiohttp_mock import AiohttpClientMocker
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
    async def test_get_regions(self, aioclient_mock: AiohttpClientMocker) -> None:
        """Test standalone async_get_regions() without auth."""
        aioclient_mock.get(
            f"{API_URL}/contacts/regions",
            json=load_fixture("regions_response.json"),
            headers=HEADERS,
        )
        session = aioclient_mock.create_session()
        try:
            data = await async_get_regions(session)
        finally:
            await session.close()

        assert len(data) > 0
        codes = [r["code"] for r in data]
        assert "rostov" in codes

    async def test_get_regions_http_error(self, aioclient_mock: AiohttpClientMocker) -> None:
        """Test async_get_regions wraps HTTP errors in TNSEApiError."""
        aioclient_mock.get(
            f"{API_URL}/contacts/regions",
            status=403,
        )
        session = aioclient_mock.create_session()
        try:
            with pytest.raises(TNSEApiError, match="403"):
                await async_get_regions(session)
        finally:
            await session.close()

    async def test_get_regions_http_error_with_body(self, aioclient_mock: AiohttpClientMocker) -> None:
        """Test async_get_regions includes API error description from body."""
        aioclient_mock.get(
            f"{API_URL}/contacts/regions",
            status=403,
            json={
                "result": False,
                "error": {"description": "Access denied"},
            },
        )
        session = aioclient_mock.create_session()
        try:
            with pytest.raises(TNSEApiError, match="Access denied.*403"):
                await async_get_regions(session)
        finally:
            await session.close()


class TestAsyncCheckVersion:
    async def test_check_version(self, aioclient_mock: AiohttpClientMocker) -> None:
        """Test standalone async_check_version() without auth."""
        aioclient_mock.get(
            f"{API_URL}/app/version?version={DEFAULT_APP_VERSION}",
            json=load_fixture("app_version_response.json"),
            headers=HEADERS,
        )
        session = aioclient_mock.create_session()
        try:
            data = await async_check_version(session)
        finally:
            await session.close()

        assert data["status"] == 1


class TestTNSEApi:
    async def test_get_user_info(self, api: TNSEApi, aioclient_mock: AiohttpClientMocker) -> None:
        aioclient_mock.get(
            f"{API_URL}/user",
            json=load_fixture("user_info_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_user_info()

        assert data["email"] == "user@example.com"
        assert data["region"] == "rostov"

    async def test_get_accounts(self, api: TNSEApi, aioclient_mock: AiohttpClientMocker) -> None:
        aioclient_mock.get(
            f"{API_URL}/accounts",
            json=load_fixture("accounts_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_accounts()

        assert len(data) == 2
        assert data[0]["id"] == ACCOUNT_ID
        assert data[0]["number"] == ACCOUNT

    async def test_get_account_info(self, api: TNSEApi, aioclient_mock: AiohttpClientMocker) -> None:
        aioclient_mock.get(
            f"{API_URL}/accounts/{ACCOUNT_ID}",
            json=load_fixture("account_info_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_account_info(ACCOUNT_ID)

        assert data["id"] == ACCOUNT_ID
        assert data["number"] == ACCOUNT
        assert data["address"]
        assert len(data["countersInfo"]) > 0

    async def test_get_main_page_debt_info(self, api: TNSEApi, aioclient_mock: AiohttpClientMocker) -> None:
        aioclient_mock.get(
            f"{API_URL}/main-page/debt/info",
            json=load_fixture("main_page_debt_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_main_page_debt_info()

        assert data == []

    async def test_get_information(self, api: TNSEApi, aioclient_mock: AiohttpClientMocker) -> None:
        aioclient_mock.get(
            f"{API_URL}/information?account={ACCOUNT}",
            json=load_fixture("information_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_information(ACCOUNT)

        assert data == []

    async def test_get_counters(self, api: TNSEApi, aioclient_mock: AiohttpClientMocker) -> None:
        aioclient_mock.get(
            f"{API_URL}/counters?account={ACCOUNT}",
            json=load_fixture("counters_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_counters(ACCOUNT)

        assert len(data) > 0
        counter = data[0]
        assert counter["counterId"] == COUNTER_ID
        assert counter["rowId"] == ROW_ID
        assert counter["tariff"] == 2
        assert len(counter["lastReadings"]) == 2

    async def test_get_balance(self, api: TNSEApi, aioclient_mock: AiohttpClientMocker) -> None:
        aioclient_mock.get(
            f"{API_URL}/payments/new-balance?account={ACCOUNT}",
            json=load_fixture("balance_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_balance(ACCOUNT)

        assert data["sumToPay"] == 1500.5

    async def test_get_counter_readings(self, api: TNSEApi, aioclient_mock: AiohttpClientMocker) -> None:
        aioclient_mock.get(
            f"{API_URL}/counters/{COUNTER_ID}/readings?account={ACCOUNT}",
            json=load_fixture("counter_readings_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_counter_readings(COUNTER_ID, ACCOUNT)

        assert len(data) > 0
        reading = data[0]
        assert reading["date"]
        assert len(reading["readings"]) == 2

    async def test_send_readings(self, api: TNSEApi, aioclient_mock: AiohttpClientMocker) -> None:
        aioclient_mock.post(
            f"{API_URL}/counters/send-readings",
            json=load_fixture("send_readings_response.json"),
            headers=HEADERS,
        )
        data = await api.async_send_readings(ACCOUNT, ROW_ID, ["2690", "1023"])

        assert data == []

    async def test_send_readings_empty(self, api: TNSEApi) -> None:
        with pytest.raises(RequiredApiParamNotFound):
            await api.async_send_readings(ACCOUNT, ROW_ID, [])

    async def test_get_invoice_settings(self, api: TNSEApi, aioclient_mock: AiohttpClientMocker) -> None:
        aioclient_mock.get(
            f"{API_URL}/invoices/settings?account={ACCOUNT}",
            json=load_fixture("invoice_settings_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_invoice_settings(ACCOUNT)

        assert data["email"] == "user@example.com"
        assert data["status"] is True

    async def test_get_invoices(self, api: TNSEApi, aioclient_mock: AiohttpClientMocker) -> None:
        aioclient_mock.get(
            f"{API_URL}/invoices?account={ACCOUNT}&year=2026",
            json=load_fixture("invoices_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_invoices(ACCOUNT, 2026)

        assert len(data) > 0
        assert data[0]["date"] == "01.01.2026"

    async def test_get_invoice_file(self, api: TNSEApi, aioclient_mock: AiohttpClientMocker) -> None:
        aioclient_mock.get(
            f"{API_URL}/invoices/get-file?account={ACCOUNT}&date=01.01.2026",
            json=load_fixture("invoice_file_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_invoice_file(ACCOUNT, "01.01.2026")

        assert data["file"]

    async def test_get_history(self, api: TNSEApi, aioclient_mock: AiohttpClientMocker) -> None:
        aioclient_mock.get(
            f"{API_URL}/history?account={ACCOUNT}&year=2026&month=2",
            json=load_fixture("history_response.json"),
            headers=HEADERS,
        )
        data = await api.async_get_history(ACCOUNT, 2026, 2)

        assert "filters" in data
        assert "items" in data
        assert len(data["items"]) > 0
