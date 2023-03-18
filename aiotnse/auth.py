"""TNS-Energo API Auth wrapper."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from aiohttp import ClientSession, hdrs

from .const import LOGGER, DEFAULT_HASH, DEFAULT_USER_AGENT


class AbstractTNSEAuth(ABC):
    """Abstract class to make authenticated requests."""
    _session: ClientSession

    def __init__(self, session: ClientSession):
        """Initialize the auth."""
        self._session = session

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""

    async def request(self, method: str, url: str, **kwargs) -> Any:
        """Make a request with token authorization."""
        params = kwargs.pop("params", {})
        params["hash"] = await self.async_get_access_token()
        headers = kwargs.pop("headers", {})
        headers[hdrs.USER_AGENT] = DEFAULT_USER_AGENT
        headers[hdrs.CONNECTION] = hdrs.KEEP_ALIVE

        LOGGER.debug("Request to %s with data %s", url, kwargs)
        async with self._session.request(method, url, **kwargs, params=params, headers=headers,
                                         raise_for_status=True) as resp:
            data = await resp.json()
            LOGGER.debug("Request finished with status=%s, headers=%s, data=%s", resp.status, resp.headers, data)
        return data


class SimpleTNSEAuth(AbstractTNSEAuth):
    """Simple implementation of AbstractTNSEAuth"""
    _token: str

    def __init__(self,
                 session: ClientSession,
                 *,
                 access_token: str = DEFAULT_HASH):
        """Initialize the auth."""
        super().__init__(session)
        self._token = access_token

    async def async_get_access_token(self) -> str:
        """Return a valid access token."""
        return self._token
