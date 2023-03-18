"""Provide a CLI for TNS-Energo API."""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pprint import pprint

from aiohttp import ClientSession

from ._version import __version__
from .api import TNSEApi
from .auth import SimpleTNSEAuth
from .const import LOG_LEVELS


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Command line tool for TNS-Energo API")

    parser.add_argument("account", help="Account number")
    parser.add_argument('--check', help='show registration information', action="store_true")
    parser.add_argument('--status', help='show account status', action="store_true")
    parser.add_argument('--readings', help='show readings history', action="store_true")
    parser.add_argument('--payment', help='show current payment', action="store_true")
    parser.add_argument('--payments', help='show payments history', action="store_true")
    parser.add_argument('--accounts', help='list linked accounts', action="store_true")
    parser.add_argument('--main', help='show main info', action="store_true")
    parser.add_argument('--info', help='show general info', action="store_true")
    parser.add_argument('--bill', help='get bill', action="store_true")
    parser.add_argument('--latest', help='show the latest readings', action="store_true")

    # send the readings
    subparsers = parser.add_subparsers(title='send', description="Send the readings command.")
    send_parser = subparsers.add_parser('send')
    send_parser.add_argument('meter', type=str, help='Meter number')
    send_parser.add_argument('readings_values', type=int, nargs="+",
                             help='Values for Tariff readings (T1,T2,T3). '
                                  'From 1 to 3 values depending on your tariff')

    parser.add_argument('-v', '--verbose', action='count', default=0, help="increase verbosity level")
    parser.add_argument("-V", "--version", action="version", version=__version__)

    arguments = parser.parse_args()

    return arguments


async def cli() -> None:
    """Run main."""
    args = get_arguments()

    # Setup logging and the log level according to the "-v" option
    logging.basicConfig(level=LOG_LEVELS.get(args.verbose, logging.INFO))

    if not args.account:
        print("Please provide account number")
        return
    account = args.account

    async with ClientSession() as session:
        auth = SimpleTNSEAuth(session)
        api = TNSEApi(auth)

        if args.check:
            print(f"Info about account #{account}:")
            _info = await api.async_is_registered(account)
            pprint(_info)
            return

        if args.status:
            print(f"Status of account #{account}:")
            _info = await api.async_get_account_status(account)
            pprint(_info)
            return

        if args.accounts:
            print(f"Accounts linked with account #{account}:")
            _info = await api.async_get_accounts(account)
            pprint(_info)
            return

        if args.main:
            print(f"Main info for account #{account}:")
            _info = await api.async_get_main_page_info(account)
            pprint(_info)
            return

        if args.info:
            print(f"General info for account #{account}:")
            _info = await api.async_get_general_info(account)
            pprint(_info)
            return

        if args.payment:
            print(f"Current payment for account #{account}:")
            _info = await api.async_get_current_payment(account)
            pprint(_info)
            return

        if args.payments:
            print(f"Payments history for account #{account}:")
            _info = await api.async_get_payments_history(account)
            pprint(_info)
            return

        if args.bill:
            print(f"Bill for account #{account}:")
            _info = await api.async_get_bill(account, date=datetime.now())
            pprint(_info)
            return

        if args.readings:
            print(f"Readings history for account #{account}:")
            _info = await api.async_get_readings_history(account)
            pprint(_info)
            return

        if args.latest:
            print(f"The latest readings for account #{account}:")
            _info = await api.async_get_latest_readings(account)
            pprint(_info)
            return

        if args.readings_values and args.meter:
            print(f"Account: #{account}")
            meter_number = str(args.meter)
            print(f"Meter: #{meter_number}")

            readings = list(args.readings_values)
            if len(readings) > 3:
                print("Error: Expected 3 or less arguments")
                return

            _latest = await api.async_get_latest_readings(account)
            if not _latest["result"]:
                print("Error. The latest readings was not received.")
                return

            pprint(_latest)

            data = []

            for rowid in _latest["counters"]:
                tariffs = _latest["counters"][rowid]
                if str(meter_number).lower() != str(tariffs[0]["ZavodNomer"]).lower():
                    continue
                if not (len(readings) == len(tariffs) == int(tariffs[0]["Tarifnost"])):
                    print(f"Error. The number of tariffs does not match.")
                    print(f"Data for {len(readings)}, and total tariffs {int(tariffs[0]['Tarifnost'])}")
                    return
                for i, tariff in enumerate(tariffs):
                    _data = {
                        "counterNumber": tariff["ZavodNomer"],
                        "label": tariff["Label"],
                        "newPok": str(readings[int(tariff["NomerTarifa"])]),  # all readings as str
                        "nomerTarifa": tariff["NomerTarifa"],
                        "rowID": rowid
                    }
                    print(f"T{int(_data['nomerTarifa'])} ({_data['label']}): "
                          f"Previous: {int(tariff['zakrPok'])} Current: {int(_data['newPok'])} "
                          f"Diff: {int(_data['newPok']) - int(tariff['zakrPok'])}")
                    data.append(_data)
                break
            if input("Do you want to send the readings? (y/n): ").lower() == "y":
                _data = await api.async_send_readings(account, data)
                if _data["result"]:
                    print("Readings was successful send.")
                else:
                    print("Readings was not send.")
                    print(_data)
            else:
                print("Readings does not send.")
            return

        print(f"Info about account #{account}:")
        _info = await api.async_is_registered(account)
        pprint(_info)
        return
