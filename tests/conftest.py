"""Fixtures for aiotnse tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses

from aiotnse import SimpleTNSEAuth, TNSEApi
from tests.common import ACCESS_TOKEN, REFRESH_TOKEN, REGION

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    """Load a JSON fixture file by name."""
    with (FIXTURES_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


@pytest_asyncio.fixture
async def auth() -> SimpleTNSEAuth:
    """Create a SimpleTNSEAuth instance with test tokens."""
    async with aiohttp.ClientSession() as session:
        yield SimpleTNSEAuth(
            session=session,
            region=REGION,
            access_token=ACCESS_TOKEN,
            refresh_token=REFRESH_TOKEN,
        )


@pytest_asyncio.fixture
async def api(auth: SimpleTNSEAuth) -> TNSEApi:
    """Create a TNSEApi instance."""
    yield TNSEApi(auth)


@pytest.fixture
def session_mock() -> aioresponses:
    """Create an aioresponses mock context."""
    with aioresponses() as mock:
        yield mock
