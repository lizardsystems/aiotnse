"""TNS-Energo mobile API wrapper."""
from __future__ import annotations

from base64 import b64encode, urlsafe_b64decode
from datetime import date, datetime, timedelta, timezone
import json
import re
import uuid
from typing import Any

from aiohttp import ClientResponseError, ClientSession, hdrs

from .auth import AbstractTNSEAuth
from .const import (
    DEFAULT_MOBILE_API_HASH,
    DEFAULT_MOBILE_API_URL_TEMPLATE,
    DEFAULT_MOBILE_AUTH_TYPE,
    DEFAULT_MOBILE_BEARER_HEADER,
    DEFAULT_MOBILE_PLATFORM,
    DEFAULT_MOBILE_USER_AGENT,
    LOGGER,
)
from .exceptions import RequiredApiParamNotFound, TNSEAuthError
from .helpers import get_region

JWT_RE = re.compile(r"([A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)")


def _decode_jwt_expiration(token: str) -> datetime | None:
    """Return token expiration timestamp from JWT payload."""
    try:
        payload = token.split(".")[1]
    except IndexError:
        return None

    padded = payload + ("=" * (-len(payload) % 4))
    try:
        data = json.loads(urlsafe_b64decode(padded.encode("ascii")))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None

    exp = data.get("exp")
    if not isinstance(exp, (int, float)):
        return None
    return datetime.fromtimestamp(exp, tz=timezone.utc)


def _find_jwt(data: Any) -> str | None:
    """Extract JWT token from arbitrary response payload."""
    if isinstance(data, str):
        match = JWT_RE.search(data)
        return match.group(1) if match else None

    if isinstance(data, list):
        for item in data:
            token = _find_jwt(item)
            if token:
                return token
        return None

    if isinstance(data, dict):
        priority_keys = (
            "accessToken",
            "access_token",
            "token",
            "jwt",
            "idToken",
            "id_token",
            "bearerToken",
            "bearer_token",
        )
        for key in priority_keys:
            if key in data:
                token = _find_jwt(data[key])
                if token:
                    return token
        for value in data.values():
            token = _find_jwt(value)
            if token:
                return token
    return None


def _make_basic_header(region: str) -> str:
    """Build Authorization Basic value for mobile API."""
    credentials = f"mobile-api-{region}:mobile-api-{region}".encode("utf-8")
    encoded = b64encode(credentials).decode("ascii")
    return f"Basic {encoded}"


class TNSEMobileAuth(AbstractTNSEAuth):
    """Auth class for the new mobile API."""

    def __init__(
        self,
        session: ClientSession,
        *,
        login: str,
        password: str,
        region: str,
        access_token: str | None = None,
        auth_type: str = DEFAULT_MOBILE_AUTH_TYPE,
        platform: str = DEFAULT_MOBILE_PLATFORM,
        api_hash: str = DEFAULT_MOBILE_API_HASH,
        device_id: str | None = None,
        bearer_header: str = DEFAULT_MOBILE_BEARER_HEADER,
        user_agent: str = DEFAULT_MOBILE_USER_AGENT,
    ) -> None:
        """Initialize auth handler for mobile API."""
        super().__init__(session)
        self._login = login
        self._password = password
        self._region = region
        self._auth_type = auth_type
        self._platform = platform
        self._api_hash = api_hash
        self._device_id = device_id or str(uuid.uuid4())
        self._bearer_header = bearer_header
        self._user_agent = user_agent
        self._token = access_token
        self._token_expiration = _decode_jwt_expiration(access_token) if access_token else None

    @classmethod
    def from_account(
        cls,
        session: ClientSession,
        *,
        login: str,
        password: str,
        account: str,
        access_token: str | None = None,
        auth_type: str = DEFAULT_MOBILE_AUTH_TYPE,
        platform: str = DEFAULT_MOBILE_PLATFORM,
        api_hash: str = DEFAULT_MOBILE_API_HASH,
        device_id: str | None = None,
        bearer_header: str = DEFAULT_MOBILE_BEARER_HEADER,
        user_agent: str = DEFAULT_MOBILE_USER_AGENT,
    ) -> TNSEMobileAuth:
        """Initialize auth by account number (region is derived automatically)."""
        return cls(
            session,
            login=login,
            password=password,
            region=get_region(account),
            access_token=access_token,
            auth_type=auth_type,
            platform=platform,
            api_hash=api_hash,
            device_id=device_id,
            bearer_header=bearer_header,
            user_agent=user_agent,
        )

    @property
    def api_url(self) -> str:
        """Return API base URL for selected region."""
        return DEFAULT_MOBILE_API_URL_TEMPLATE.format(region=self._region)

    def _build_headers(self, token: str | None = None) -> dict[str, str]:
        """Build default headers for all requests."""
        headers = {
            hdrs.USER_AGENT: self._user_agent,
            hdrs.CONNECTION: hdrs.KEEP_ALIVE,
            "x-api-hash": self._api_hash,
            "x-device-id": self._device_id,
            hdrs.AUTHORIZATION: _make_basic_header(self._region),
        }
        if token:
            headers[self._bearer_header] = f"Bearer {token}"
        print(headers)
        return headers

    async def _async_authorize(self) -> str:
        """Authorize via login+password and return JWT."""
        url = f"{self.api_url}/user/auth"
        payload = {
            "login": self._login,
            "authType": self._auth_type,
            "password": self._password,
            "region": self._region,
            "platform": self._platform,
        }
        headers = self._build_headers()
        LOGGER.debug("Requesting mobile auth token for region=%s", self._region)
        async with self._session.post(url, json=payload, headers=headers, raise_for_status=True) as resp:
            data = await resp.json()
            LOGGER.debug(
                "Auth request finished with status=%s, headers=%s, data=%s",
                resp.status,
                resp.headers,
                data,
            )

        token = _find_jwt(data)
        if token is None:
            raise TNSEAuthError("JWT token was not found in authorization response")

        self._token = token
        self._token_expiration = _decode_jwt_expiration(token)
        return token

    async def async_get_access_token(self) -> str:
        """Return valid JWT token."""
        now = datetime.now(tz=timezone.utc)
        if self._token and self._token_expiration:
            if self._token_expiration - timedelta(seconds=30) > now:
                return self._token

        if self._token and self._token_expiration is None:
            return self._token

        return await self._async_authorize()

    async def request(self, method: str, url: str, **kwargs) -> Any:
        """Make an authenticated request for mobile API."""
        headers = kwargs.pop("headers", {})
        token = await self.async_get_access_token()
        request_headers = self._build_headers(token)
        request_headers.update(headers)

        LOGGER.debug("Request to %s with data %s", url, kwargs)
        try:
            async with self._session.request(
                method,
                url,
                headers=request_headers,
                raise_for_status=True,
                **kwargs,
            ) as resp:
                data = await resp.json()
                LOGGER.debug(
                    "Request finished with status=%s, headers=%s, data=%s",
                    resp.status,
                    resp.headers,
                    data,
                )
                return data
        except ClientResponseError as err:
            if err.status != 401:
                raise

        token = await self._async_authorize()
        retry_headers = self._build_headers(token)
        retry_headers.update(headers)
        async with self._session.request(
            method,
            url,
            headers=retry_headers,
            raise_for_status=True,
            **kwargs,
        ) as resp:
            return await resp.json()


class TNSEMobileApi:
    """Class to communicate with the new mobile TNS-E API."""

    def __init__(self, auth: TNSEMobileAuth):
        """Initialize API class."""
        self._auth = auth
        self._api_url = auth.api_url

    async def _async_get(self, path: str, **params: str) -> dict[str, Any]:
        """Make GET request to mobile API endpoint."""
        url = f"{self._api_url}/{path}"
        _params = params or None
        return await self._auth.request(hdrs.METH_GET, url, params=_params)

    async def _async_post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Make POST request to mobile API endpoint."""
        url = f"{self._api_url}/{path}"
        return await self._auth.request(hdrs.METH_POST, url, json=payload)

    async def async_get_user(self) -> dict[str, Any]:
        """Get current authorized user.

        Example response:
        {"result": true, "statusCode": 200, "data": {"id": 100001, "email": "demo@example.com", "region": "nn"}}
        """
        return await self._async_get("user")

    async def async_get_current_payment(self, account: str) -> dict[str, Any]:
        """Get current payment balance.

        Example response:
        {"result": true, "statusCode": 200, "data": {"sumToPayRaw": 1250.5, "debt": 1200.0, "hasAvans": false}}
        """
        if not account:
            raise RequiredApiParamNotFound("Required API 'account' parameter not found")
        return await self._async_get("payments/new-balance", account=account)

    async def async_get_counters(self, account: str) -> dict[str, Any]:
        """Get counters list for account.

        Example response:
        {"result": true, "statusCode": 200, "data": [{"id": 90010001, "rowId": 70010001}]}
        """
        if not account:
            raise RequiredApiParamNotFound("Required API 'account' parameter not found")
        return await self._async_get("counters", account=account)

    async def async_get_counter_readings(self, account: str, counter_id: str | int) -> dict[str, Any]:
        """Get meter readings history for specific counter.

        Example response:
        {"result": true, "statusCode": 200, "data": [{"date": "25.01.26", "readings": [{"title": "Day", "value": 10570}]}]}
        """
        if not account:
            raise RequiredApiParamNotFound("Required API 'account' parameter not found")
        if counter_id in ("", None):
            raise RequiredApiParamNotFound("Required API 'counter_id' parameter not found")
        return await self._async_get(f"counters/{counter_id}/readings", account=account)

    async def async_get_payments(
        self,
        account: str,
        date_from: date | str,
        date_to: date | str,
        operation_type: str = "all",
    ) -> dict[str, Any]:
        """Get payments list by period.

        Example response:
        {"result": true, "statusCode": 200, "data": [{"date": "15.01.2026", "sum": 1000.0, "operationType": "payment"}]}
        """
        if not account:
            raise RequiredApiParamNotFound("Required API 'account' parameter not found")
        if not date_from:
            raise RequiredApiParamNotFound("Required API 'date_from' parameter not found")
        if not date_to:
            raise RequiredApiParamNotFound("Required API 'date_to' parameter not found")

        period_from = date_from.strftime("%m.%Y") if isinstance(date_from, date) else str(date_from)
        period_to = date_to.strftime("%m.%Y") if isinstance(date_to, date) else str(date_to)
        return await self._async_get(
            "payments",
            account=account,
            dateFrom=period_from,
            dateTo=period_to,
            operationType=operation_type,
        )

    async def async_get_invoices(self, account: str, year: int | str) -> dict[str, Any]:
        """Get available invoices for year.

        Example response:
        {"result": true, "statusCode": 200, "data": [{"date": "01.01.2026", "amount": 2450.0}]}
        """
        if not account:
            raise RequiredApiParamNotFound("Required API 'account' parameter not found")
        if year in ("", None):
            raise RequiredApiParamNotFound("Required API 'year' parameter not found")
        return await self._async_get("invoices", account=account, year=str(year))

    async def async_get_invoice_file(self, account: str, dt: date | str) -> dict[str, Any]:
        """Get invoice file payload by date.

        Example response:
        {"result": true, "statusCode": 200, "data": {"contentType": "application/pdf", "base64": "<pdf_data>"}}
        """
        if not account:
            raise RequiredApiParamNotFound("Required API 'account' parameter not found")
        if not dt:
            raise RequiredApiParamNotFound("Required API 'dt' parameter not found")

        bill_date = dt.strftime("%d.%m.%Y") if isinstance(dt, date) else str(dt)
        return await self._async_get("invoices/get-file", account=account, date=bill_date)

    async def async_send_readings(
        self,
        account: str,
        row_id: str | int,
        readings: list[str | int | float],
        platform: str = DEFAULT_MOBILE_PLATFORM,
    ) -> dict[str, Any]:
        """Send meter readings.

        Example response:
        {"result": true, "statusCode": 200, "data": {"accepted": true}}
        """
        if not account:
            raise RequiredApiParamNotFound("Required API 'account' parameter not found")
        if row_id in ("", None):
            raise RequiredApiParamNotFound("Required API 'row_id' parameter not found")
        if not readings:
            raise RequiredApiParamNotFound("Required API 'readings' parameter not found")

        payload = {
            "account": account,
            "rowId": str(row_id),
            "readings": [str(value) for value in readings],
            "platform": platform,
        }
        return await self._async_post("counters/send-readings", payload=payload)

    async def async_get_latest_readings(self, account: str) -> dict[str, Any]:
        """Compatibility method with old API: map to counters list.

        Example response:
        {"result": true, "statusCode": 200, "data": [{"id": 90010001, "rowId": 70010001}]}
        """
        return await self.async_get_counters(account)

    async def async_get_readings_history(self, account: str, counter_id: str | int) -> dict[str, Any]:
        """Compatibility method with old API: map to counter readings.

        Example response:
        {"result": true, "statusCode": 200, "data": [{"date": "25.01.26", "readings": [{"title": "Day", "value": 10570}]}]}
        """
        return await self.async_get_counter_readings(account, counter_id)

    async def async_get_payments_history(
        self,
        account: str,
        date_from: date | str,
        date_to: date | str,
        operation_type: str = "all",
    ) -> dict[str, Any]:
        """Compatibility method with old API: map to payments by period.

        Example response:
        {"result": true, "statusCode": 200, "data": [{"date": "15.01.2026", "sum": 1000.0, "operationType": "payment"}]}
        """
        return await self.async_get_payments(account, date_from, date_to, operation_type)

    async def async_get_bill(self, account: str, dt: date | str) -> dict[str, Any]:
        """Compatibility method with old API: map to invoice file.

        Example response:
        {"result": true, "statusCode": 200, "data": {"contentType": "application/pdf", "base64": "<pdf_data>"}}
        """
        return await self.async_get_invoice_file(account, dt)
