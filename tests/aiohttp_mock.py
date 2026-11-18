"""Mock aiohttp client requests, in the style of Home Assistant tests.

The API follows Home Assistant's ``AiohttpClientMocker``
(``tests/test_util/aiohttp.py`` in home-assistant/core): register responses
with ``get()`` / ``post()``, run the code under test with a session from
``create_session()``, then inspect ``mock_calls`` and ``call_count``.

Unlike the Home Assistant version, the mock response mirrors real aiohttp in
two places the library code relies on:

- ``session.request(..., raise_for_status=True)`` raises
  ``ClientResponseError`` for a status of 400 or higher;
- ``json()`` returns ``None`` for an empty body and raises
  ``ContentTypeError`` when the Content-Type is not JSON.

The mock replaces ``ClientSession._request`` and never builds an aiohttp
``ClientResponse``, so it keeps working across aiohttp releases.
"""
from __future__ import annotations

import json as jsonlib
import re
from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Any
from unittest import mock
from urllib.parse import parse_qs

from aiohttp import ClientSession
from aiohttp.client_exceptions import (
    ClientConnectionError,
    ClientResponseError,
    ContentTypeError,
)
from multidict import CIMultiDict
from yarl import URL

SideEffect = Callable[[str, URL, Any], Awaitable["AiohttpClientMockResponse"]]


class AiohttpClientMocker:
    """Mock aiohttp client requests."""

    def __init__(self) -> None:
        """Initialize the request mocker."""
        self._mocks: list[AiohttpClientMockResponse] = []
        self.mock_calls: list[tuple[str, URL, Any, Any]] = []

    def request(
        self,
        method: str,
        url: str | URL | re.Pattern[str],
        *,
        status: int = HTTPStatus.OK,
        text: str | None = None,
        content: bytes | None = None,
        json: Any = None,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        exc: BaseException | None = None,
        side_effect: SideEffect | None = None,
        closing: bool | None = None,
    ) -> AiohttpClientMockResponse:
        """Register a mock response for a request."""
        if not isinstance(url, re.Pattern):
            url = URL(url)
            if params:
                url = url.with_query(params)
        response = AiohttpClientMockResponse(
            method=method,
            url=url,
            status=status,
            response=content,
            json=json,
            text=text,
            exc=exc,
            headers=headers,
            side_effect=side_effect,
            closing=closing,
        )
        self._mocks.append(response)
        return response

    def get(self, *args: Any, **kwargs: Any) -> None:
        """Register a mock GET request."""
        self.request("get", *args, **kwargs)

    def post(self, *args: Any, **kwargs: Any) -> None:
        """Register a mock POST request."""
        self.request("post", *args, **kwargs)

    def put(self, *args: Any, **kwargs: Any) -> None:
        """Register a mock PUT request."""
        self.request("put", *args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> None:
        """Register a mock DELETE request."""
        self.request("delete", *args, **kwargs)

    @property
    def call_count(self) -> int:
        """Return the number of requests made."""
        return len(self.mock_calls)

    def clear_requests(self) -> None:
        """Forget registered responses and recorded calls."""
        self._mocks.clear()
        self.mock_calls.clear()

    def create_session(self) -> ClientSession:
        """Create a ClientSession whose requests go to this mocker."""
        session = ClientSession()
        # Setting the attribute directly triggers a deprecation warning
        object.__setattr__(session, "_request", self.match_request)
        return session

    async def match_request(
        self,
        method: str,
        url: str | URL,
        *,
        data: Any = None,
        json: Any = None,
        params: Any = None,
        headers: Any = None,
        raise_for_status: Any = None,
        **kwargs: Any,
    ) -> AiohttpClientMockResponse:
        """Return the first registered response that matches the request."""
        data = data or json
        url = URL(url)
        if params:
            url = url.with_query(params)

        for response in self._mocks:
            if response.match_request(method, url):
                self.mock_calls.append((method, url, data, headers))
                if response.side_effect:
                    response = await response.side_effect(method, url, data)
                if response.exc:
                    raise response.exc
                if raise_for_status is True:
                    response.raise_for_status()
                return response

        raise AssertionError(
            f"No mock registered for {method.upper()} {url} {params}"
        )


class AiohttpClientMockResponse:
    """Mock aiohttp client response."""

    def __init__(
        self,
        method: str,
        url: URL | re.Pattern[str],
        status: int = HTTPStatus.OK,
        response: bytes | None = None,
        json: Any = None,
        text: str | None = None,
        exc: BaseException | None = None,
        headers: dict[str, str] | None = None,
        side_effect: SideEffect | None = None,
        closing: bool | None = None,
    ) -> None:
        """Initialize a fake response."""
        self._headers: CIMultiDict[str] = CIMultiDict(headers or {})
        if json is not None:
            text = jsonlib.dumps(json)
            self._headers.setdefault("Content-Type", "application/json")
        if text is not None:
            response = text.encode("utf-8")
        if response is None:
            response = b""

        self.method = method.upper()
        self._url = url
        self.status = int(status)
        self._response = response
        self.exc = exc
        self.side_effect = side_effect
        self.closing = closing

    def match_request(self, method: str, url: URL) -> bool:
        """Return True if this response answers the request."""
        if method.upper() != self.method:
            return False

        if isinstance(self._url, re.Pattern):
            return self._url.search(str(url)) is not None

        if (
            self._url.scheme != url.scheme
            or self._url.raw_host != url.raw_host
            or self._url.raw_path != url.raw_path
        ):
            return False

        # Every query component of the matcher must be present in the request
        request_qs = parse_qs(url.query_string)
        matcher_qs = parse_qs(self._url.query_string)
        for key, values in matcher_qs.items():
            for value in values:
                try:
                    request_qs.get(key, []).remove(value)
                except ValueError:
                    return False
        return True

    @property
    def url(self) -> URL:
        """Return the URL of the response."""
        return self._url if isinstance(self._url, URL) else URL("http://mock")

    @property
    def ok(self) -> bool:
        """Return True if the status is below 400, like aiohttp."""
        return self.status < 400

    @property
    def headers(self) -> CIMultiDict[str]:
        """Return the response headers."""
        return self._headers

    @property
    def content_type(self) -> str:
        """Return the MIME type of the response, like aiohttp."""
        raw = self._headers.get("Content-Type", "application/octet-stream")
        return raw.split(";")[0].strip().lower()

    @property
    def charset(self) -> str | None:
        """Return the charset from the Content-Type header."""
        raw = self._headers.get("Content-Type", "").lower()
        if "charset=" in raw:
            return raw.split("charset=")[1].split(";")[0].strip()
        return None

    @property
    def response(self) -> bytes:
        """Return the raw body, or fail if the connection is closing."""
        if self.closing:
            raise ClientConnectionError("Connection closed")
        return self._response

    def _request_info(self) -> mock.Mock:
        return mock.Mock(real_url=self.url, url=self.url, method=self.method)

    async def read(self) -> bytes:
        """Return the raw body."""
        return self.response

    async def text(self, encoding: str | None = None, errors: str = "strict") -> str:
        """Return the body as text."""
        return self.response.decode(encoding or self.charset or "utf-8", errors)

    async def json(
        self,
        *,
        encoding: str | None = None,
        loads: Callable[[str], Any] = jsonlib.loads,
        content_type: str | None = "application/json",
    ) -> Any:
        """Return the body parsed as JSON, with aiohttp's checks."""
        body = self.response
        if not body.strip():
            return None
        if content_type and "json" not in self.content_type:
            raise ContentTypeError(
                self._request_info(),
                (),
                status=self.status,
                message=(
                    "Attempt to decode JSON with unexpected mimetype: "
                    f"{self.content_type}"
                ),
                headers=self._headers,
            )
        return loads(body.decode(encoding or self.charset or "utf-8"))

    def raise_for_status(self) -> None:
        """Raise ClientResponseError for a status of 400 or higher."""
        if self.status >= 400:
            raise ClientResponseError(
                request_info=self._request_info(),
                history=(),
                status=self.status,
                message=HTTPStatus(self.status).phrase
                if self.status in HTTPStatus._value2member_map_
                else "",
                headers=self._headers,
            )

    async def __aenter__(self) -> AiohttpClientMockResponse:
        """Enter the response context, as aiohttp 3.14 does."""
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        """Exit the response context."""
        self.release()

    def release(self) -> None:
        """Mock release."""

    def close(self) -> None:
        """Mock close."""

    async def wait_for_close(self) -> None:
        """Mock wait_for_close."""
