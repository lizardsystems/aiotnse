"""CLI entrypoint for TNS-Energo API."""
from __future__ import annotations

import asyncio

from .cli import cli


def main() -> None:
    """Run the CLI entrypoint."""
    asyncio.run(cli())


if __name__ == "__main__":
    main()
