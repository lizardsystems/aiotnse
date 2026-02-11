"""Example showing usage of this library."""

import asyncio
from pprint import pprint

import aiohttp

from aiotnse import SimpleTNSEAuth, TNSEApi, async_get_regions


async def main() -> None:
    """Create the aiohttp session and run the example."""
    async with aiohttp.ClientSession() as session:
        # Fetch available regions
        print("Fetching available regions...")
        regions_data = await async_get_regions(session)
        regions = regions_data["data"]
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

        # Login
        auth = SimpleTNSEAuth(
            session, region=region, email=email, password=password
        )
        print(f"\nLogging in as {email} (region: {region})...")
        await auth.async_login()
        print("Login successful.")

        # Fetch and display accounts
        api = TNSEApi(auth)
        data = await api.async_get_accounts()
        print("\nAccounts:")
        pprint(data)

        # Logout
        await auth.async_logout()
        print("\nLogged out.")


if __name__ == "__main__":
    asyncio.run(main())
