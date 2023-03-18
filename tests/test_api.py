"""Tests for aiotnse package."""
import json
from datetime import datetime

import pytest
from aioresponses import aioresponses

from aiotnse import TNSEApi
from aiotnse.const import DEFAULT_BASE_URL, DEFAULT_API_VERSION, DEFAULT_HASH
from aiotnse.helpers import get_region
from tests.common import HEADERS, ACCOUNT


@pytest.mark.asyncio
class TestTNSEApi:
    async def test_get_account_status(self, api: TNSEApi, session_mock: aioresponses):
        account = ACCOUNT
        headers = HEADERS
        with open("fixtures/account_status_response.json", encoding="utf-8") as file:
            payload = json.load(file)

        session_mock.get(
            f"{DEFAULT_BASE_URL}/version/{DEFAULT_API_VERSION}/Android/mobile/"
            f"delegation/getLsStatus/{account}/?hash={DEFAULT_HASH}",
            payload=payload,
            headers=headers,
        )
        data = await api.async_get_account_status(account)

        assert data is not None
        assert data["result"]
        assert data["emailAndKvitStatus"]["ls"] == account
        assert data["registered_email"] == "test@test.ru"

    async def test_get_latest_readings(self, api: TNSEApi, session_mock: aioresponses):
        account = ACCOUNT
        headers = HEADERS
        region = get_region(account)
        with open("fixtures/latest_readings_response_t1_t2.json", encoding="utf-8") as file:
            payload = json.load(file)

        session_mock.get(
            f"{DEFAULT_BASE_URL}/version/{DEFAULT_API_VERSION}/Android/mobile/"
            f"region/{region}/action/getSendReadingsPage/ls/{account}/json/"
            f"?hash={DEFAULT_HASH}",
            payload=payload,
            headers=headers,
        )
        data = await api.async_get_latest_readings(account)

        assert data is not None
        assert data["result"]
        assert data["counters"]
        for row_id in data["counters"]:
            for meter in data["counters"][row_id]:
                assert meter["ZavodNomer"]
                assert meter["ZavodNomer"] == "22222222"

    async def test_get_readings_history(self, api: TNSEApi, session_mock: aioresponses):
        account = ACCOUNT
        headers = HEADERS
        region = get_region(account)
        with open("fixtures/readings_history_response.json", encoding="utf-8") as file:
            payload = json.load(file)
        session_mock.get(
            f"{DEFAULT_BASE_URL}/version/{DEFAULT_API_VERSION}/Android/mobile/"
            f"region/{region}/action/getReadingsHistPage/ls/{account}/json/"
            f"?hash={DEFAULT_HASH}",
            payload=payload,
            headers=headers,
        )
        data = await api.async_get_readings_history(account)

        assert data is not None
        assert data["result"]
        assert data["history"]
        for year in data["history"]:
            for record_date in data["history"][year]:
                for row_id in data["history"][year][record_date]:
                    assert data["history"][year][record_date][row_id]
                    assert "number" in data["history"][year][record_date][row_id]
                    assert "readings" in data["history"][year][record_date][row_id]
                    for reading in data["history"][year][record_date][row_id]["readings"]:
                        assert "label" in data["history"][year][record_date][row_id]["readings"][reading]
                        assert "value" in data["history"][year][record_date][row_id]["readings"][reading]

    async def test_get_current_payment(self, api: TNSEApi, session_mock: aioresponses):
        account = ACCOUNT
        headers = HEADERS
        region = get_region(account)
        with open("fixtures/current_payment_response.json", encoding="utf-8") as file:
            payload = json.load(file)

        session_mock.get(
            f"{DEFAULT_BASE_URL}/version/{DEFAULT_API_VERSION}/Android/mobile/"
            f"region/{region}/action/getPaymentPage/ls/{account}/json/"
            f"?hash={DEFAULT_HASH}",
            payload=payload,
            headers=headers,
        )
        data = await api.async_get_current_payment(account)

        assert data is not None
        assert data["result"]
        assert data["data"]

    async def test_get_payments_history(self, api: TNSEApi, session_mock: aioresponses):
        account = ACCOUNT
        headers = HEADERS
        region = get_region(account)
        with open("fixtures/payments_history_response.json", encoding="utf-8") as file:
            payload = json.load(file)

        session_mock.get(
            f"{DEFAULT_BASE_URL}/version/{DEFAULT_API_VERSION}/Android/mobile/"
            f"region/{region}/action/getPaymentsHistPage/ls/{account}/json/"
            f"?hash={DEFAULT_HASH}",
            payload=payload,
            headers=headers,
        )
        data = await api.async_get_payments_history(account)

        assert data is not None
        assert data["result"]
        assert data["history"]
        for year in data["history"]:
            for record in data["history"][year]:
                assert record["SUMMA"]
                assert record["DATE"]

    async def test_get_accounts(self, api: TNSEApi, session_mock: aioresponses):
        account = ACCOUNT
        headers = HEADERS
        with open("fixtures/accounts_response.json", encoding="utf-8") as file:
            payload = json.load(file)

        session_mock.post(
            f"{DEFAULT_BASE_URL}/version/{DEFAULT_API_VERSION}/Android/mobile/"
            f"delegation/getLSListByLs/{account}/"
            f"?hash={DEFAULT_HASH}",
            payload=payload,
            headers=headers,
        )
        data = await api.async_get_accounts(account)

        assert data is not None
        assert data["result"]

    async def test_get_main_page_info(self, api: TNSEApi, session_mock: aioresponses):
        account = ACCOUNT
        headers = HEADERS
        region = get_region(account)
        with open("fixtures/main_page_response.json", encoding="utf-8") as file:
            payload = json.load(file)

        session_mock.get(
            f"{DEFAULT_BASE_URL}/version/{DEFAULT_API_VERSION}/Android/mobile/"
            f"region/{region}/action/getMainPage/ls/{account}/json/"
            f"?hash={DEFAULT_HASH}",
            payload=payload,
            headers=headers,
        )
        data = await api.async_get_main_page_info(account)

        assert data is not None
        assert data["result"]
        assert data["emailAndKvitStatus"]["ls"] == account

    async def test_get_general_info(self, api: TNSEApi, session_mock: aioresponses):
        account = ACCOUNT
        headers = HEADERS
        region = get_region(account)
        with open("fixtures/general_info_response.json", encoding="utf-8") as file:
            payload = json.load(file)

        session_mock.get(
            f"{DEFAULT_BASE_URL}/version/{DEFAULT_API_VERSION}/Android/mobile/"
            f"region/{region}/action/getInfo/ls/{account}/json/"
            f"?hash={DEFAULT_HASH}",
            payload=payload,
            headers=headers,
        )
        data = await api.async_get_general_info(account)

        assert data is not None
        assert data["result"]
        assert data["counters"]
        for meter in data["counters"]:
            assert meter["ZavodNomer"]

    async def test_get_bill(self, api: TNSEApi, session_mock: aioresponses):
        account = ACCOUNT
        headers = HEADERS
        date = datetime(day=1, month=1, year=2023)
        region = get_region(account)
        with open("fixtures/bill_response.json", encoding="utf-8") as file:
            payload = json.load(file)
        session_mock.get(
            f"{DEFAULT_BASE_URL}/version/{DEFAULT_API_VERSION}/Android/mobile/"
            f"region/{region}/action/getBill/ls/{account}/date/{date:%d.%m.%Y}/json/"
            f"?hash={DEFAULT_HASH}",
            payload=payload,
            headers=headers,
        )
        data = await api.async_get_bill(account, date)

        assert data is not None
        assert data["result"]
        assert data["link"]

    async def test_is_registered(self, api: TNSEApi, session_mock: aioresponses):
        account = ACCOUNT
        headers = HEADERS
        region = get_region(account)
        with open("fixtures/registered_response.json", encoding="utf-8") as file:
            payload = json.load(file)
        session_mock.get(
            f"{DEFAULT_BASE_URL}/version/{DEFAULT_API_VERSION}/Android/mobile/"
            f"region/{region}/action/isLsRegisteredAndHasPayments/{account}/"
            f"?hash={DEFAULT_HASH}",
            payload=payload,
            headers=headers,
        )
        data = await api.async_is_registered(account)

        assert data is not None
        assert data["result"]
        assert data["ADDRESS"]

    async def test_send_readings(self, api: TNSEApi, session_mock: aioresponses):
        account = ACCOUNT
        headers = HEADERS
        region = get_region(account)
        with open("fixtures/send_readings_request.json", encoding="utf-8") as file:
            readings = json.load(file)
        with open("fixtures/send_readings_response.json", encoding="utf-8") as file:
            payload = json.load(file)
        session_mock.post(
            f"{DEFAULT_BASE_URL}/version/{DEFAULT_API_VERSION}/Android/mobile/"
            f"region/{region}/action/sendReadings/ls/{account}/json/"
            f"?hash={DEFAULT_HASH}",
            payload=payload,
            headers=headers,
        )
        data = await api.async_send_readings(account, readings)

        assert data is not None
        assert data["result"]
        assert data["data"]
