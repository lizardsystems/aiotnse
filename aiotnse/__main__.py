"""Provide a CLI for TNS-Energo API."""
from __future__ import annotations

import asyncio

from .cli import cli

if __name__ == "__main__":
    asyncio.run(cli())
