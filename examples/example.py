"""Example showing usage of this library.

Mirrors the hass-tnse coordinator flow:
1. Login
2. Get all accounts
3. For each account: get account info, balance, counters
4. For each counter: get readings history
5. Get last payment from history
6. Logout
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pprint import pprint

import aiohttp

from aiotnse import SimpleTNSEAuth, TNSEApi, async_get_regions


async def main() -> None:
    """Create the aiohttp session and run the example."""
    async with aiohttp.ClientSession() as session:
        # ---- Step 1: Fetch available regions ----
        print("=" * 60)
        print("Fetching available regions...")
        regions = await async_get_regions(session)
        for i, r in enumerate(regions, 1):
            print(f"  {i}. {r['name']} ({r['code']})")

        # User selects a region by number
        while True:
            try:
                choice = int(input("\nRegion number: "))
                if 1 <= choice <= len(regions):
                    break
                print(f"Enter a number from 1 to {len(regions)}")
            except ValueError:
                print("Enter a valid number")

        region = regions[choice - 1]["code"]

        # User enters credentials
        email = input("Email: ")
        password = input("Password: ")

        # ---- Step 2: Login ----
        print("=" * 60)
        auth = SimpleTNSEAuth(
            session, region=region, email=email, password=password
        )
        print(f"Logging in as {email} (region: {region})...")
        await auth.async_login()
        print("Login successful.")
        print(f"  Access token expires:  {auth.access_token_expires}")
        print(f"  Refresh token expires: {auth.refresh_token_expires}")

        api = TNSEApi(auth)

        # ---- Step 3: Get all accounts ----
        print("=" * 60)
        print("Fetching accounts...")
        raw_accounts = await api.async_get_accounts()
        print(f"Found {len(raw_accounts)} account(s)")

        for raw in raw_accounts:
            account_id = raw["id"]
            account_number = raw["number"]
            account_name = raw.get("name", "")

            print()
            print("-" * 60)
            print(f"Account: {account_number} (id={account_id}, name={account_name})")
            print("-" * 60)

            # ---- Step 4: Account info ----
            print("\n[Account Info]")
            try:
                info = await api.async_get_account_info(account_id)
                print(f"  Address:       {info.get('address')}")
                print(f"  Persons:       {info.get('numberPersons')}")
                print(f"  Total area:    {info.get('totalArea')}")
                print(f"  Living area:   {info.get('livingArea')}")
                print(f"  Document:      {info.get('document')}")
                print(f"  Category:      {info.get('tenantCategory')}")
                print(f"  Season ratio:  {info.get('seasonRatio')}")
            except Exception as exc:
                print(f"  ERROR: {exc}")

            # ---- Step 5: Balance ----
            print("\n[Balance]")
            try:
                balance = await api.async_get_balance(account_number)
                print(f"  Sum to pay:    {balance.get('sumToPay')}")
                print(f"  Debt:          {balance.get('debt')}")
                print(f"  Peni debt:     {balance.get('peniDebt')}")
                print(f"  Closed month:  {balance.get('closedMonth')}")
                print(f"  Recalc:        {balance.get('recalc')}")
                print(f"  Losses:        {balance.get('losses')}")
                print(f"  ODN:           {balance.get('odn')}")
                print(f"  Peni forecast: {balance.get('peniForecast')}")
                print(f"  Avans total:   {balance.get('avansTotal')}")
            except Exception as exc:
                print(f"  ERROR: {exc}")

            # ---- Step 6: Counters ----
            print("\n[Counters]")
            try:
                counters = await api.async_get_counters(account_number)
                print(f"  Found {len(counters)} counter(s)")
            except Exception as exc:
                print(f"  ERROR: {exc}")
                counters = []

            for j, counter in enumerate(counters):
                counter_id = counter.get("counterId")
                row_id = counter.get("rowId")
                tariff = counter.get("tariff")
                checking_date = counter.get("checkingDate")
                last_readings = counter.get("lastReadings", [])

                print(f"\n  Counter #{j + 1}: {counter_id}")
                print(f"    Row ID:        {row_id}")
                print(f"    Tariff zones:  {tariff}")
                print(f"    Checking date: {checking_date}")
                print(f"    Last readings ({len(last_readings)}):")
                for k, reading in enumerate(last_readings):
                    print(
                        f"      T{k + 1}: {reading.get('value')} kWh"
                        f"  ({reading.get('name')}, {reading.get('date')})"
                    )

                # ---- Step 7: Readings history ----
                print(f"    Readings history:")
                try:
                    history = await api.async_get_counter_readings(
                        counter_id, account_number
                    )
                    for entry in history[:5]:  # last 5 entries
                        values = ", ".join(
                            f"T{i + 1}={r.get('value')}"
                            for i, r in enumerate(entry.get("readings", []))
                        )
                        print(f"      {entry.get('date')}: {values}")
                    if len(history) > 5:
                        print(f"      ... and {len(history) - 5} more")
                except Exception as exc:
                    print(f"      ERROR: {exc}")

            # ---- Step 8: Last payment from history ----
            print("\n[Last Payment]")
            try:
                now = datetime.now()
                for offset in (0, -1):
                    dt = now.replace(day=1)
                    if offset == -1:
                        dt = (dt - timedelta(days=1)).replace(day=1)
                    history_data = await api.async_get_history(
                        account_number, dt.year, dt.month
                    )
                    items = history_data.get("items", [])
                    for item in items:
                        if item.get("type") == 1:
                            print(f"  Date:   {item.get('date')}")
                            print(f"  Amount: {item.get('amount')}")
                            break
                    else:
                        continue
                    break
                else:
                    print("  No payments found")
            except Exception as exc:
                print(f"  ERROR: {exc}")

            # ---- Full raw data (for debugging) ----
            print("\n[Raw account data]")
            pprint(raw)

        # ---- Step 9: Logout ----
        print()
        print("=" * 60)
        await auth.async_logout()
        print("Logged out.")


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
