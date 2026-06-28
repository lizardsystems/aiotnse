"""Live health-check / smoke test for the aiotnse library.

Walks through the main public and authenticated API calls against the real
TNS-Energo backend and prints PASS / FAIL / SKIP for each, so you can quickly
spot when the upstream API has changed (new error codes, moved endpoints,
changed response shapes, 403/HTML responses, etc.).

It is read-only: it never sends meter readings or mutates anything. In
addition to the read calls it explicitly exercises the refresh-token endpoint
(the spot behind hass-tnse issue #14) and a final logout.

Region, email and password are requested interactively at startup. The
password input is hidden.

Run from the repo root:

    python -m examples.healthcheck

or:

    python examples/healthcheck.py

Add -v / --verbose for full aiotnse debug logging.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from getpass import getpass
from pathlib import Path
from pprint import pformat
from typing import Any, Awaitable, Callable

import aiohttp

import aiotnse
from aiotnse import SimpleTNSEAuth, TNSEApi, async_check_version, async_get_regions

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

# ANSI colors (disabled automatically when not writing to a TTY).
_COLORS = {PASS: "\033[32m", FAIL: "\033[31m", SKIP: "\033[33m"}
_RESET = "\033[0m"

# Result lines are routed here; the handler is attached in _setup_logging so
# they land in the log file only (never duplicated on the console).
log = logging.getLogger("healthcheck")


def _mask(token: str | None) -> str:
    """Mask a secret token for logging, keeping only the last 6 characters."""
    if not token:
        return "<none>"
    return f"...{token[-6:]}" if len(token) > 6 else "<short>"


def _color(status: str) -> str:
    """Colorize a status label when stdout is a terminal."""
    if not sys.stdout.isatty():
        return status
    return f"{_COLORS.get(status, '')}{status}{_RESET}"


@dataclass
class Result:
    """Outcome of a single health check."""

    name: str
    status: str
    detail: str = ""
    elapsed_ms: float = 0.0


@dataclass
class HealthCheck:
    """Accumulates and runs individual checks."""

    results: list[Result] = field(default_factory=list)

    async def run(
        self,
        name: str,
        factory: Callable[[], Awaitable[Any]],
        summarize: Callable[[Any], str] | None = None,
        inputs: Any | None = None,
    ) -> Any | None:
        """Run one check, record the result, and return the data (or None).

        The full input (``inputs``) and full output (the parsed response) are
        written to the log file so the whole request/response picture is
        available afterwards.
        """
        log.info("CHECK %s", name)
        log.debug("INPUT  %s: %s", name, pformat(inputs) if inputs else "<none>")
        start = time.monotonic()
        try:
            data = await factory()
        except Exception as exc:  # noqa: BLE001 - we want to catch everything here
            elapsed = (time.monotonic() - start) * 1000
            detail = f"{type(exc).__name__}: {exc}"
            self.results.append(Result(name, FAIL, detail, elapsed))
            print(f"  [{_color(FAIL)}] {name}  ({elapsed:.0f} ms)")
            print(f"          {detail}")
            log.error("FAIL  %s  (%.0f ms): %s", name, elapsed, detail)
            log.debug("TRACEBACK %s:", name, exc_info=True)
            return None
        else:
            elapsed = (time.monotonic() - start) * 1000
            detail = ""
            if summarize is not None:
                try:
                    detail = summarize(data)
                except Exception as exc:  # noqa: BLE001
                    detail = f"(summary failed: {exc})"
            self.results.append(Result(name, PASS, detail, elapsed))
            suffix = f"  {detail}" if detail else ""
            print(f"  [{_color(PASS)}] {name}  ({elapsed:.0f} ms){suffix}")
            log.info("PASS  %s  (%.0f ms)  %s", name, elapsed, detail)
            log.debug("OUTPUT %s:\n%s", name, pformat(data))
            return data

    def skip(self, name: str, reason: str) -> None:
        """Record a skipped check."""
        self.results.append(Result(name, SKIP, reason))
        print(f"  [{_color(SKIP)}] {name}  ({reason})")
        log.info("SKIP  %s  (%s)", name, reason)

    def summary(self) -> int:
        """Print the summary table and return a process exit code."""
        passed = sum(r.status == PASS for r in self.results)
        failed = sum(r.status == FAIL for r in self.results)
        skipped = sum(r.status == SKIP for r in self.results)

        print()
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        for r in self.results:
            line = f"  {_color(r.status):<6}  {r.name}"
            if r.elapsed_ms:
                line += f"  ({r.elapsed_ms:.0f} ms)"
            print(line)
            if r.status == FAIL and r.detail:
                print(f"            -> {r.detail}")
        print("-" * 70)
        print(f"  {passed} passed, {failed} failed, {skipped} skipped")
        print("=" * 70)
        log.info(
            "Summary: %d passed, %d failed, %d skipped", passed, failed, skipped
        )
        if failed:
            print(
                "\nOne or more calls failed. If login itself worked but data "
                "calls failed,\nthe upstream API has most likely changed."
            )
        return 1 if failed else 0


# ---- response summarizers (short, shape-focused) ------------------------------


def _shape(data: Any) -> str:
    """Generic short description of a response shape."""
    if isinstance(data, list):
        return f"list[{len(data)}]"
    if isinstance(data, dict):
        keys = list(data.keys())
        shown = ", ".join(keys[:6])
        more = f", +{len(keys) - 6} more" if len(keys) > 6 else ""
        return f"dict keys: {shown}{more}"
    return f"{type(data).__name__}: {data!r}"


def _sum_regions(data: Any) -> str:
    return f"{len(data)} regions"


def _sum_accounts(data: Any) -> str:
    nums = [a.get("number") for a in data] if isinstance(data, list) else []
    return f"{len(nums)} account(s): {', '.join(str(n) for n in nums)}"


def _sum_balance(data: Any) -> str:
    if isinstance(data, dict):
        return f"sumToPay={data.get('sumToPay')}, debt={data.get('debt')}"
    return _shape(data)


def _sum_counters(data: Any) -> str:
    if isinstance(data, list):
        ids = [c.get("counterId") for c in data]
        return f"{len(ids)} counter(s): {', '.join(str(i) for i in ids)}"
    return _shape(data)


# ---- version + logging setup --------------------------------------------------


def _read_version() -> str:
    """Read the project version from pyproject.toml.

    Falls back to the installed package metadata version if the file cannot be
    read or parsed.
    """
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        with pyproject.open("rb") as f:
            data = tomllib.load(f)
        return str(data["project"]["version"])
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return aiotnse.__version__


def _setup_logging(verbose: bool, log_path: str) -> None:
    """Configure logging.

    - The log file always captures full DEBUG output (every API request and
      response from aiotnse, plus the PASS/FAIL/SKIP result lines), so problems
      can be analysed afterwards.
    - The console stays clean: WARNING and above by default, or full DEBUG with
      --verbose.

    Note: at DEBUG the log file contains the login/refresh responses, which
    include access and refresh tokens. Treat the file as sensitive.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    )
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.WARNING)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(console)

    # Result lines go to the file handler only, so they are never duplicated on
    # the console (which already shows them via print()).
    log.setLevel(logging.DEBUG)
    log.handlers.clear()
    log.addHandler(file_handler)
    log.propagate = False


# ---- interactive credential prompt --------------------------------------------


async def _prompt_region(session: aiohttp.ClientSession, hc: HealthCheck) -> str:
    """Fetch the region list, let the user pick one, return the region code.

    The regions fetch is recorded as the first health check. If it fails, the
    user can still type a region code manually so the rest of the run proceeds.
    """
    print("Fetching available regions...")
    regions = await hc.run("public: regions", lambda: async_get_regions(session), _sum_regions)

    if regions:
        for i, r in enumerate(regions, 1):
            print(f"  {i:>3}. {r.get('name')} ({r.get('code')})")
        codes = {str(r.get("code")) for r in regions}
        while True:
            raw = input("\nRegion number or code: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(regions):
                return str(regions[int(raw) - 1]["code"])
            if raw in codes:
                return raw
            print("Enter a valid number from the list or an exact region code.")
    else:
        # Regions endpoint failed - allow manual entry so we can still test auth.
        return input("Region code (e.g. rostov, nn, penza): ").strip()


# ---- main flow ----------------------------------------------------------------


async def main(verbose: bool, log_path: str) -> int:
    """Run the full health check and return a process exit code."""
    _setup_logging(verbose, log_path)

    version = _read_version()
    module_dir = os.path.dirname(aiotnse.__file__)

    print("=" * 70)
    print("aiotnse health check")
    print("=" * 70)
    print(f"  aiotnse version: {version}")
    print(f"  aiotnse module:  {module_dir}")
    print(f"  log file:        {os.path.abspath(log_path)}")
    print("=" * 70)

    log.info("aiotnse health check started")
    log.info("aiotnse version: %s", version)
    log.info("aiotnse module:  %s", module_dir)

    hc = HealthCheck()

    async with aiohttp.ClientSession() as session:
        # ---- credentials ----
        region = await _prompt_region(session, hc)
        email = input("Email: ").strip()
        password = getpass("Password: ")
        print()
        # Region and email are logged for context; the password never is.
        log.info("region=%s email=%s", region, email)

        now = datetime.now()

        # ---- public, no-auth endpoints ----
        print("Public endpoints:")
        await hc.run(
            "public: version check",
            lambda: async_check_version(session, region=region),
            _shape,
            inputs={"region": region},
        )

        # ---- authentication ----
        print("\nAuthentication:")
        auth = SimpleTNSEAuth(
            session, region=region, email=email, password=password
        )
        login = await hc.run(
            "auth: login",
            auth.async_login,
            _shape,
            inputs={"region": region, "email": email, "password": "<hidden>"},
        )
        if login is None:
            print("\nLogin failed - cannot test authenticated endpoints.")
            return hc.summary()

        print(f"          access token expires:  {auth.access_token_expires}")
        print(f"          refresh token expires: {auth.refresh_token_expires}")

        # Explicitly exercise the refresh endpoint (issue #14 lives here).
        await hc.run(
            "auth: refresh-token",
            auth.async_refresh_token,
            lambda d: f"new access expires {auth.access_token_expires}",
            inputs={"refresh_token": _mask(auth.refresh_token)},
        )

        api = TNSEApi(auth)

        # ---- authenticated, account-independent endpoints ----
        print("\nAuthenticated endpoints:")
        await hc.run("api: user info", api.async_get_user_info, _shape)
        accounts = await hc.run("api: accounts", api.async_get_accounts, _sum_accounts)
        await hc.run(
            "api: main-page debt info", api.async_get_main_page_debt_info, _shape
        )

        # ---- account-dependent endpoints ----
        if not accounts:
            for name in (
                "api: account info",
                "api: information",
                "api: balance",
                "api: counters",
                "api: counter readings",
                "api: invoice settings",
                "api: invoices",
                "api: history",
            ):
                hc.skip(name, "no accounts")
        else:
            first = accounts[0]
            account_id = first.get("id")
            account_number = first.get("number")
            print(f"\nUsing account {account_number} (id={account_id}):")

            await hc.run(
                "api: account info",
                lambda: api.async_get_account_info(account_id),
                _shape,
                inputs={"account_id": account_id},
            )
            await hc.run(
                "api: information",
                lambda: api.async_get_information(account_number),
                _shape,
                inputs={"account": account_number},
            )
            await hc.run(
                "api: balance",
                lambda: api.async_get_balance(account_number),
                _sum_balance,
                inputs={"account": account_number},
            )
            counters = await hc.run(
                "api: counters",
                lambda: api.async_get_counters(account_number),
                _sum_counters,
                inputs={"account": account_number},
            )

            if counters:
                counter_id = counters[0].get("counterId")
                await hc.run(
                    "api: counter readings",
                    lambda: api.async_get_counter_readings(
                        counter_id, account_number
                    ),
                    _shape,
                    inputs={"counter_id": counter_id, "account": account_number},
                )
            else:
                hc.skip("api: counter readings", "no counters")

            await hc.run(
                "api: invoice settings",
                lambda: api.async_get_invoice_settings(account_number),
                _shape,
                inputs={"account": account_number},
            )
            await hc.run(
                "api: invoices",
                lambda: api.async_get_invoices(account_number, now.year),
                _shape,
                inputs={"account": account_number, "year": now.year},
            )
            await hc.run(
                "api: history",
                lambda: api.async_get_history(account_number, now.year, now.month),
                _shape,
                inputs={
                    "account": account_number,
                    "year": now.year,
                    "month": now.month,
                },
            )

        # ---- logout ----
        print("\nSession teardown:")
        await hc.run("auth: logout", auth.async_logout, _shape)

    return hc.summary()


def _default_log_path() -> str:
    """Build a timestamped default log file name in the current directory."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"tns_healthcheck_{stamp}.log"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="also print full aiotnse debug logging to the console",
    )
    parser.add_argument(
        "--log-file",
        metavar="PATH",
        default=None,
        help="path to the debug log file (default: tns_healthcheck_<timestamp>.log)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    log_path = args.log_file or _default_log_path()
    try:
        code = asyncio.run(main(args.verbose, log_path))
        print(f"\nFull debug log written to: {os.path.abspath(log_path)}")
        raise SystemExit(code)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        print(f"Partial debug log written to: {os.path.abspath(log_path)}")
        raise SystemExit(130) from None
