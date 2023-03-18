import asyncio

import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses

from aiotnse import SimpleTNSEAuth, TNSEApi


@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="class")
@pytest.mark.asyncio
async def auth() -> SimpleTNSEAuth:
    async with aiohttp.ClientSession() as _session:
        _auth = SimpleTNSEAuth(session=_session)
        yield _auth
        # some finalization


@pytest_asyncio.fixture(scope="class")
@pytest.mark.asyncio
async def api(auth: SimpleTNSEAuth) -> TNSEApi:
    _api = TNSEApi(auth)
    yield _api
    # some finalization


@pytest.fixture(scope="class")
def session_mock() -> aioresponses:
    with aioresponses() as _session_mock:
        yield _session_mock
        # some finalization
