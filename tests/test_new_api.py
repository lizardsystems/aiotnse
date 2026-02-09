"""Tests for mobile API support."""

from datetime import date
import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses

from aiotnse import TNSEMobileApi, TNSEMobileAuth
from aiotnse.exceptions import RequiredApiParamNotFound

TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJ1c2VySWQiOiIxMDAwMDEiLCJyZWdpb24iOiJubiIsImV4cCI6NDA3MDkwODgwMH0."
    "fakeSignatureForTestsOnly"
)
BASE_URL = "https://mobile-api-nn.tns-e.ru/api/v1"
ACCOUNT = "520000000001"
COUNTER_ID = "90010001"
ROW_ID = "70010001"


@pytest.fixture
def session_mock() -> aioresponses:
    with aioresponses() as _session_mock:
        yield _session_mock


@pytest_asyncio.fixture
async def mobile_auth() -> TNSEMobileAuth:
    async with aiohttp.ClientSession() as session:
        yield TNSEMobileAuth(
            session,
            login="demo@example.com",
            password="secret",
            region="nn",
            device_id="test-device",
        )


def _mock_auth(session_mock: aioresponses) -> None:
    session_mock.post(
        f"{BASE_URL}/user/auth",
        payload={"result": True, "statusCode": 200, "data": {"session": {"jwt": TOKEN}}},
        headers={"Content-Type": "application/json"},
    )


@pytest.mark.asyncio
async def test_mobile_get_user(mobile_auth: TNSEMobileAuth, session_mock: aioresponses) -> None:
    _mock_auth(session_mock)
    session_mock.get(
        f"{BASE_URL}/user",
        payload={
            "result": True,
            "statusCode": 200,
            "data": {"id": 100001, "email": "demo@example.com", "region": "nn"},
        },
        headers={"Content-Type": "application/json"},
    )

    api = TNSEMobileApi(mobile_auth)
    data = await api.async_get_user()

    assert data["result"]
    assert data["statusCode"] == 200
    assert data["data"]["region"] == "nn"


@pytest.mark.asyncio
async def test_mobile_get_current_payment(mobile_auth: TNSEMobileAuth, session_mock: aioresponses) -> None:
    _mock_auth(session_mock)
    account = ACCOUNT
    session_mock.get(
        f"{BASE_URL}/payments/new-balance?account={account}",
        payload={
            "result": True,
            "statusCode": 200,
            "data": {"sumToPayRaw": 4137.25, "debt": 2373.47, "hasAvans": True},
        },
        headers={"Content-Type": "application/json"},
    )

    api = TNSEMobileApi(mobile_auth)
    data = await api.async_get_current_payment(account)

    assert data["result"]
    assert data["data"]["sumToPayRaw"] == 4137.25


@pytest.mark.asyncio
async def test_mobile_get_counter_readings(mobile_auth: TNSEMobileAuth, session_mock: aioresponses) -> None:
    _mock_auth(session_mock)
    account = ACCOUNT
    counter_id = COUNTER_ID
    session_mock.get(
        f"{BASE_URL}/counters/{counter_id}/readings?account={account}",
        payload={
            "result": True,
            "statusCode": 200,
            "data": [
                {
                    "date": "25.01.26",
                    "readings": [
                        {"title": "Day meter 90010001", "value": 10570, "consumption": 322},
                        {"title": "Night meter 90010001", "value": 2278, "consumption": 55},
                    ],
                }
            ],
        },
        headers={"Content-Type": "application/json"},
    )

    api = TNSEMobileApi(mobile_auth)
    data = await api.async_get_counter_readings(account, counter_id)

    assert data["result"]
    assert data["data"]
    assert data["data"][0]["readings"][0]["value"] == 10570


@pytest.mark.asyncio
async def test_mobile_get_counters(mobile_auth: TNSEMobileAuth, session_mock: aioresponses) -> None:
    _mock_auth(session_mock)
    account = ACCOUNT
    session_mock.get(
        f"{BASE_URL}/counters?account={account}",
        payload={"result": True, "statusCode": 200, "data": [{"id": 90010001, "rowId": 70010001}]},
        headers={"Content-Type": "application/json"},
    )

    api = TNSEMobileApi(mobile_auth)
    data = await api.async_get_counters(account)

    assert data["result"]
    assert data["data"][0]["id"] == 90010001


@pytest.mark.asyncio
async def test_mobile_get_payments(mobile_auth: TNSEMobileAuth, session_mock: aioresponses) -> None:
    _mock_auth(session_mock)
    account = ACCOUNT
    session_mock.get(
        f"{BASE_URL}/payments?account={account}&dateFrom=01.2026&dateTo=02.2026&operationType=all",
        payload={"result": True, "statusCode": 200, "data": [{"sum": 1000}]},
        headers={"Content-Type": "application/json"},
    )

    api = TNSEMobileApi(mobile_auth)
    data = await api.async_get_payments(account, "01.2026", "02.2026")

    assert data["result"]
    assert data["data"][0]["sum"] == 1000


@pytest.mark.asyncio
async def test_mobile_get_invoices(mobile_auth: TNSEMobileAuth, session_mock: aioresponses) -> None:
    _mock_auth(session_mock)
    account = ACCOUNT
    session_mock.get(
        f"{BASE_URL}/invoices?account={account}&year=2026",
        payload={"result": True, "statusCode": 200, "data": [{"date": "01.01.2026"}]},
        headers={"Content-Type": "application/json"},
    )

    api = TNSEMobileApi(mobile_auth)
    data = await api.async_get_invoices(account, 2026)

    assert data["result"]
    assert data["data"][0]["date"] == "01.01.2026"


@pytest.mark.asyncio
async def test_mobile_get_invoice_file(mobile_auth: TNSEMobileAuth, session_mock: aioresponses) -> None:
    _mock_auth(session_mock)
    account = ACCOUNT
    session_mock.get(
        f"{BASE_URL}/invoices/get-file?account={account}&date=01.01.2026",
        payload={"result": True, "statusCode": 200, "data": {"contentType": "application/pdf"}},
        headers={"Content-Type": "application/json"},
    )

    api = TNSEMobileApi(mobile_auth)
    data = await api.async_get_invoice_file(account, date(2026, 1, 1))

    assert data["result"]
    assert data["data"]["contentType"] == "application/pdf"


@pytest.mark.asyncio
async def test_mobile_send_readings(mobile_auth: TNSEMobileAuth, session_mock: aioresponses) -> None:
    _mock_auth(session_mock)
    session_mock.post(
        f"{BASE_URL}/counters/send-readings",
        payload={"result": True, "statusCode": 200},
        headers={"Content-Type": "application/json"},
    )

    api = TNSEMobileApi(mobile_auth)
    data = await api.async_send_readings(ACCOUNT, ROW_ID, [5938, 3120])

    assert data["result"]
    assert data["statusCode"] == 200


@pytest.mark.asyncio
async def test_mobile_required_params(mobile_auth: TNSEMobileAuth) -> None:
    api = TNSEMobileApi(mobile_auth)

    with pytest.raises(RequiredApiParamNotFound):
        await api.async_get_current_payment("")

    with pytest.raises(RequiredApiParamNotFound):
        await api.async_get_counter_readings(ACCOUNT, "")

    with pytest.raises(RequiredApiParamNotFound):
        await api.async_get_counters("")

    with pytest.raises(RequiredApiParamNotFound):
        await api.async_get_payments(ACCOUNT, "", "02.2026")

    with pytest.raises(RequiredApiParamNotFound):
        await api.async_get_payments(ACCOUNT, "01.2026", "")

    with pytest.raises(RequiredApiParamNotFound):
        await api.async_get_invoices(ACCOUNT, "")

    with pytest.raises(RequiredApiParamNotFound):
        await api.async_get_invoice_file("", date(2026, 1, 1))

    with pytest.raises(RequiredApiParamNotFound):
        await api.async_send_readings(ACCOUNT, "", [1, 2])

    with pytest.raises(RequiredApiParamNotFound):
        await api.async_send_readings(ACCOUNT, ROW_ID, [])
