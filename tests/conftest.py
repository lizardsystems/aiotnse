"""Fixtures for aiotnse tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiohttp
import pytest
import pytest_asyncio

from aiotnse import SimpleTNSEAuth, TNSEApi
from tests.aiohttp_mock import AiohttpClientMocker
from tests.common import ACCESS_TOKEN, REFRESH_TOKEN, REGION

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    """Load a JSON fixture file by name."""
    with (FIXTURES_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def aioclient_mock() -> AiohttpClientMocker:
    """Create an aiohttp client mocker."""
    return AiohttpClientMocker()


@pytest_asyncio.fixture
async def auth(aioclient_mock: AiohttpClientMocker) -> SimpleTNSEAuth:
    """Create a SimpleTNSEAuth instance with test tokens."""
    session = aioclient_mock.create_session()
    try:
        yield SimpleTNSEAuth(
            session=session,
            region=REGION,
            access_token=ACCESS_TOKEN,
            refresh_token=REFRESH_TOKEN,
        )
    finally:
        await session.close()


@pytest_asyncio.fixture
async def api(auth: SimpleTNSEAuth) -> TNSEApi:
    """Create a TNSEApi instance."""
    yield TNSEApi(auth)
