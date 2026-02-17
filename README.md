# aioTNSE

[![PyPI](https://img.shields.io/pypi/v/aiotnse.svg)](https://pypi.org/project/aiotnse/)
[![Python](https://img.shields.io/pypi/pyversions/aiotnse.svg)](https://pypi.org/project/aiotnse/)
[![License: MIT](https://img.shields.io/pypi/l/aiotnse.svg)](https://github.com/lizardsystems/aiotnse/blob/main/LICENSE)
[![CI](https://github.com/lizardsystems/aiotnse/actions/workflows/ci.yml/badge.svg)](https://github.com/lizardsystems/aiotnse/actions/workflows/ci.yml)

Асинхронная Python-библиотека для работы с мобильным API [ТНС-Энерго](https://tns-e.ru) (российская энергосбытовая компания).

Используется как бэкенд для интеграции [hass-tnse](https://github.com/lizardsystems/hass-tnse) в Home Assistant.

## Возможности

- Аутентификация по email/паролю с JWT-токенами
- Автоматическое обновление токенов (access token → refresh token → re-login)
- Получение списка лицевых счетов, баланса, показаний счётчиков
- Передача показаний счётчиков
- Получение квитанций (PDF) и истории операций
- Полная поддержка всех регионов ТНС-Энерго
- CLI для работы с API из командной строки

## Установка

```
pip install aiotnse
```

## Быстрый старт

```python
import asyncio

import aiohttp

from aiotnse import SimpleTNSEAuth, TNSEApi, async_get_regions


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        # Получить список регионов (авторизация не требуется)
        regions = await async_get_regions(session)
        for r in regions:
            print(f"{r['name']} ({r['code']})")

        # Авторизация
        auth = SimpleTNSEAuth(
            session, region="rostov", email="user@example.com", password="password"
        )
        await auth.async_login()

        api = TNSEApi(auth)

        # Лицевые счета
        accounts = await api.async_get_accounts()
        account_number = accounts[0]["number"]

        # Баланс
        balance = await api.async_get_balance(account_number)
        print(f"К оплате: {balance['sumToPay']} руб.")

        # Счётчики
        counters = await api.async_get_counters(account_number)
        for counter in counters:
            print(f"Счётчик {counter['counterId']}: {counter['lastReadings']}")


asyncio.run(main())
```

## Авторизация

### Логин по email/паролю

```python
auth = SimpleTNSEAuth(
    session, region="rostov", email="user@example.com", password="password"
)
await auth.async_login()
```

### Восстановление сессии из сохранённых токенов

`async_get_access_token()` автоматически обновляет токены или выполняет повторную
аутентификацию при необходимости:

```python
from datetime import datetime


def on_token_update(token_data: dict) -> None:
    """Вызывается после логина или обновления токена — сохраните токены."""
    save_to_storage(token_data)


auth = SimpleTNSEAuth(
    session,
    region="rostov",
    email="user@example.com",
    password="password",
    access_token="saved_access_token",
    refresh_token="saved_refresh_token",
    access_token_expires=datetime.fromisoformat("2026-06-09T19:42:16"),
    refresh_token_expires=datetime.fromisoformat("2026-10-09T19:42:16"),
    token_update_callback=on_token_update,
)
# Вызов async_login() не нужен — токены обновятся автоматически при первом API-запросе
```

### Автоматическое управление токенами

`async_get_access_token()` реализует трёхуровневую логику:

1. Возвращает кэшированный токен, если он ещё действителен
2. Обновляет через `async_refresh_token()`, если access token истёк
3. Выполняет повторный логин через `async_login()`, если оба токена истекли

`asyncio.Lock` предотвращает параллельное обновление токенов.

## API-методы

### Публичные (без авторизации)

| Функция | Описание |
|---------|----------|
| `async_get_regions(session)` | Список доступных регионов |
| `async_check_version(session, region)` | Проверка совместимости версии приложения |

### Лицевые счета

| Метод | Описание |
|-------|----------|
| `async_get_accounts()` | Список лицевых счетов пользователя |
| `async_get_account_info(account_id)` | Детальная информация по ID |
| `async_get_information(account)` | Общая информация по номеру ЛС |
| `async_get_main_page_debt_info()` | Информация о задолженности |

### Счётчики и показания

| Метод | Описание |
|-------|----------|
| `async_get_counters(account)` | Счётчики для лицевого счёта |
| `async_get_counter_readings(counter_id, account)` | История показаний счётчика |
| `async_send_readings(account, row_id, readings)` | Передача показаний |

### Платежи и баланс

| Метод | Описание |
|-------|----------|
| `async_get_balance(account)` | Баланс и начисления |
| `async_get_history(account, year, month)` | История операций за месяц |

### Квитанции

| Метод | Описание |
|-------|----------|
| `async_get_invoices(account, year)` | Список квитанций за год |
| `async_get_invoice_file(account, date)` | Квитанция в формате PDF (base64) |
| `async_get_invoice_settings(account)` | Настройки email-доставки квитанций |

### Пользователь

| Метод | Описание |
|-------|----------|
| `async_get_user_info()` | Информация о текущем пользователе |

Подробная документация API: [docs/API.md](docs/API.md)

## Исключения

```
TNSEApiError                    — базовая ошибка API
├── TNSEAuthError               — ошибка авторизации
│   ├── TNSETokenExpiredError   — токен истёк
│   └── TNSETokenRefreshError   — ошибка обновления токена
├── RegionNotFound              — регион не найден
├── InvalidAccountNumber        — неверный номер ЛС
└── RequiredApiParamNotFound    — отсутствует обязательный параметр
```

## CLI

Библиотека включает CLI для работы с API из командной строки:

```bash
# Список регионов (авторизация не требуется)
aiotnse-cli --regions

# Лицевые счета
aiotnse-cli --email user@example.com --password pass --region rostov --accounts

# Баланс
aiotnse-cli --email user@example.com --password pass --region rostov --balance 610000000001

# Счётчики
aiotnse-cli --email user@example.com --password pass --region rostov --counters 610000000001

# Передача показаний
aiotnse-cli --email user@example.com --password pass --region rostov send 610000000001 2000001 2690 1023

# Подробный вывод (отладка)
aiotnse-cli -vvv --email user@example.com --password pass --region rostov --accounts
```

Если `--region` не указан, CLI предложит выбрать регион интерактивно.

## Таймауты

aiotnse не задаёт таймауты для запросов. Управление таймаутами — ответственность вызывающего кода:

```python
import asyncio

async with asyncio.timeout(10):
    data = await api.async_get_counters(account)
```

## Разработка

```bash
# Клонирование
git clone https://github.com/lizardsystems/aiotnse.git
cd aiotnse

# Установка зависимостей для тестирования
pip install -e ".[test]"

# Запуск тестов
pytest tests/ -v
```

## Ссылки

- [Документация API](docs/API.md)
- [Changelog](CHANGELOG.md)
- [hass-tnse](https://github.com/lizardsystems/hass-tnse) — интеграция для Home Assistant
- [Проблемы и предложения](https://github.com/lizardsystems/aiotnse/issues)
