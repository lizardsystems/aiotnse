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
```

The `SimpleTNSEAuth` client also accept custom access token (this can be found by sniffing the client).

## New Mobile API (login + password)

If your region is moved to the new mobile API (`mobile-api-<region>.tns-e.ru`), use `TNSEMobileAuth` and `TNSEMobileApi`:

```python
import asyncio
from pprint import pprint

import aiohttp

from aiotnse import TNSEMobileApi, TNSEMobileAuth


async def main(login: str, password: str, account: str) -> None:
    async with aiohttp.ClientSession() as session:
        auth = TNSEMobileAuth(
            session,
            login=login,
            password=password,
            region="nn",
        )
        api = TNSEMobileApi(auth)

        user = await api.async_get_user()
        balance = await api.async_get_current_payment(account)

        pprint(user)
        pprint(balance)


if __name__ == "__main__":
    asyncio.run(main("demo@example.com", "password", "520000000001"))
```

You can also derive the region from account automatically:

```python
auth = TNSEMobileAuth.from_account(
    session,
    login="demo@example.com",
    password="password",
    account="520000000001",
)
```

This will return a price object that looks a little like this:

```json
{
  "STATUS": "Используется",
  "counters": {
    "1111111": [
      {
        "Can_delete": "0",
        "DatePok": "06.02.2023",
        "DatePosledPover": "31.12.2021",
        "DatePover": "31.12.2037",
        "DatePoverStatus": 0,
        "DatePoverURL": "",
        "GodVipuska": "01.01.22",
        "KoefTrans": "1",
        "Label": "Дневная зона",
        "MaxPok": "2000",
        "MestoUst": "Жилой дом",
        "ModelPU": "Нева МТ 114 AS PLRFPC",
        "NazvanieTarifa": "День",
        "NazvanieUslugi": "Электроснабжение ",
        "NomerTarifa": "0",
        "NomerUslugi": "0100",
        "PredPok": "700",
        "RaschSch": "Работает",
        "Razradnost": "6",
        "RowID": "1111111",
        "Tarifnost": "2",
        "Type": "1",
        "ZavodNomer": "22222222",
        "sort": 0,
        "zakrPok": "700"
      },
      {
        "Can_delete": "0",
        "DatePok": "06.02.2023",
        "DatePosledPover": "31.12.2021",
        "DatePover": "31.12.2037",
        "DatePoverStatus": 0,
        "DatePoverURL": "",
        "GodVipuska": "01.01.22",
        "KoefTrans": "1",
        "Label": "Ночная зона",
        "MaxPok": "2000",
        "MestoUst": "Жилой дом",
        "ModelPU": "Нева МТ 114 AS PLRFPC",
        "NazvanieTarifa": "Ночь",
        "NazvanieUslugi": "Электроснабжение ",
        "NomerTarifa": "1",
        "NomerUslugi": "0100",
        "PredPok": "337",
        "RaschSch": "Работает",
        "Razradnost": "6",
        "RowID": "1111111",
        "Tarifnost": "2",
        "Type": "1",
        "ZavodNomer": "22222222",
        "sort": 1,
        "zakrPok": "337"
      }
    ]
  },
  "result": true
}
```

## Timeouts

aiotnse does not specify any timeouts for any requests. You will need to specify them in your own code. We recommend the `timeout` from `asyncio` package:

```python
import asyncio

with asyncio.timeout(10):
    data = await api.async_get_account_status(account)
```
