"""Provide a CLI for TNS-Energo API."""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pprint import pprint

from aiohttp import ClientError, ClientSession

from . import __version__
from .api import TNSEApi, async_get_regions
from .auth import SimpleTNSEAuth
from .const import LOG_LEVELS
from .exceptions import TNSEApiError


def _die(message: str) -> None:
    """Print error message and exit."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def _parse_csv(value: str, count: int, flag: str) -> list[str]:
    """Split comma-separated value and validate part count."""
    parts = value.split(",")
    if len(parts) != count:
        _die(f"{flag} expects {count} comma-separated values")
    return parts


def get_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Command line tool for TNS-Energo API")

    parser.add_argument("--email", help="email for authentication")
    parser.add_argument("--password", help="password for authentication")
    parser.add_argument("--region", help="region code (interactive selection if omitted)")

    parser.add_argument("--accounts", action="store_true", help="list user accounts")
    parser.add_argument("--account-info", type=int, metavar="ID", help="show account details by ID")
    parser.add_argument("--counters", metavar="ACCOUNT", help="show counters for account")
    parser.add_argument("--balance", metavar="ACCOUNT", help="show balance for account")
    parser.add_argument("--readings", metavar="COUNTER_ID,ACCOUNT", help="show counter readings")
    parser.add_argument("--history", metavar="ACCOUNT,YEAR,MONTH", help="show history")
    parser.add_argument("--invoices", metavar="ACCOUNT,YEAR", help="show invoices")
    parser.add_argument("--user", action="store_true", help="show user info")
    parser.add_argument("--regions", action="store_true", help="show available regions")
    parser.add_argument("--version-check", action="store_true", help="check app version")

    sub = parser.add_subparsers(title="send", description="Send the readings command.")
    send = sub.add_parser("send")
    send.add_argument("account", help="account number")
    send.add_argument("row_id", help="row ID from counters response")
    send.add_argument("readings_values", nargs="+", help="reading values (T1, T2, ...)")
    send.set_defaults(command="send")

    parser.add_argument("-v", "--verbose", action="count", default=0, help="increase verbosity level")
    parser.add_argument("-V", "--version", action="version", version=__version__)

    return parser.parse_args()


async def _print_regions(session: ClientSession) -> list[dict]:
    """Fetch and print available regions. Return the region list."""
    data = await async_get_regions(session)
    regions = data["data"]
    print("Available regions:")
    for i, r in enumerate(regions, 1):
        print(f"  {i}. {r['name']} ({r['code']})")
    return regions


async def _select_region(session: ClientSession) -> str:
    """Show region list and let user pick one interactively."""
    regions = await _print_regions(session)
    while True:
        try:
            choice = int(input("\nRegion number: "))
            if 1 <= choice <= len(regions):
                return regions[choice - 1]["code"]
            print(f"Enter a number from 1 to {len(regions)}")
        except ValueError:
            print("Enter a valid number")


async def _send_readings(api: TNSEApi, args: argparse.Namespace) -> None:
    """Confirm and send meter readings."""
    readings = list(args.readings_values)
    print(f"Sending readings for account {args.account}, row {args.row_id}: {readings}")

    if input("Confirm? (y/n): ").lower() != "y":
        print("Cancelled.")
        return

    data = await api.async_send_readings(args.account, args.row_id, readings)
    if data.get("result"):
        print("Readings sent successfully.")
    else:
        print("Failed to send readings.")
        pprint(data)


async def _execute_command(api: TNSEApi, args: argparse.Namespace) -> None:
    """Execute the requested API command."""
    if getattr(args, "command", None) == "send":
        await _send_readings(api, args)
        return

    if args.version_check:
        result = await api.async_check_version()
    elif args.user:
        result = await api.async_get_user_info()
    elif args.accounts:
        result = await api.async_get_accounts()
    elif args.account_info:
        result = await api.async_get_account_info(args.account_info)
    elif args.counters:
        result = await api.async_get_counters(args.counters)
    elif args.balance:
        result = await api.async_get_balance(args.balance)
    elif args.readings:
        counter_id, account = _parse_csv(args.readings, 2, "--readings")
        result = await api.async_get_counter_readings(counter_id, account)
    elif args.history:
        account, year, month = _parse_csv(args.history, 3, "--history")
        result = await api.async_get_history(account, int(year), int(month))
    elif args.invoices:
        account, year = _parse_csv(args.invoices, 2, "--invoices")
        result = await api.async_get_invoices(account, int(year))
    else:
        result = await api.async_get_accounts()

    pprint(result)


async def cli() -> None:
    """Run main."""
    args = get_arguments()
    logging.basicConfig(level=LOG_LEVELS.get(args.verbose, logging.INFO))

    try:
        async with ClientSession() as session:
            if args.regions:
                await _print_regions(session)
                return

            if not args.email or not args.password:
                _die("--email and --password are required.")

            region = args.region or await _select_region(session)

            auth = SimpleTNSEAuth(
                session, region=region, email=args.email, password=args.password
            )
            print(f"Logging in as {args.email} (region: {region})...")
            await auth.async_login()
            print("Login successful.")

            await _execute_command(TNSEApi(auth), args)
    except ClientError as err:
        _die(f"Connection failed: {err}")
    except TNSEApiError as err:
        _die(f"API error: {err}")


if __name__ == "__main__":
    asyncio.run(cli())
