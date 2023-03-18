""" Example showing usage of this library """

import asyncio
from pprint import pprint

import aiohttp

from aiotnse import SimpleTNSEAuth, TNSEApi


async def main(account: str) -> None:
    """Create the aiohttp session and run the example."""
    async with aiohttp.ClientSession() as session:
        auth = SimpleTNSEAuth(session)
        api = TNSEApi(auth)

        data = await api.async_get_latest_readings(account)

        pprint(data)


if __name__ == "__main__":
    _account = string = str(input("Account: "))
    asyncio.run(main(_account))
