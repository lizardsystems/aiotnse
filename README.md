# aioTNSE

Asynchronous Python API for [TNS-Energo](https://tns-e.ru).

## Installation

Use pip to install the library:

```commandline
pip install aiotnse
```

## Usage

```python
import asyncio
from pprint import pprint

import aiohttp

from aiotnse import SimpleTNSEAuth, TNSEApi


async def main(email: str, password: str, region: str) -> None:
    """Create the aiohttp session and run the example."""
    async with aiohttp.ClientSession() as session:
        auth = SimpleTNSEAuth(
            session,
            region=region,
            email=email,
            password=password,
        )

        # Login first
        await auth.async_login()

        api = TNSEApi(auth)

        # Get user accounts
        accounts = await api.async_get_accounts()
        pprint(accounts)

        # Get counters for an account
        account_number = accounts["data"][0]["number"]
        counters = await api.async_get_counters(account_number)
        pprint(counters)


if __name__ == "__main__":
    _email = input("Email: ")
    _password = input("Password: ")
    _region = input("Region (e.g. rostov, penza, yar): ")
    asyncio.run(main(_email, _password, _region))
```

You can also restore a session with saved tokens:

```python
auth = SimpleTNSEAuth(
    session,
    region="rostov",
    access_token="saved_access_token",
    refresh_token="saved_refresh_token",
)
```

## Contributors

- [Sergei Mikheev (@Muxee4ka)](https://github.com/Muxee4ka) — research and documentation of the new mobile API

## Timeouts

aiotnse does not specify any timeouts for any requests. You will need to specify them in your own code. We recommend the `timeout` from `asyncio` package:

```python
import asyncio

async with asyncio.timeout(10):
    data = await api.async_get_counters(account)
```
