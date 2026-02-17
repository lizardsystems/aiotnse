# Справочник мобильного API ТНС-Энерго

Базовый URL: `https://mobile-api-{region}.tns-e.ru/api/v1`

> **Примечание:** Библиотека aiotnse (начиная с версии 2.0.3) возвращает payload (`data`) напрямую.
> Например, `async_get_accounts()` возвращает массив аккаунтов, а не `{"result": true, "statusCode": 200, "data": [...]}`.

## Общие заголовки

Все запросы включают:

| Заголовок | Значение |
|-----------|----------|
| `User-Agent` | `Dart/3.9 (dart:io)` |
| `Content-Type` | `application/json` |
| `x-api-hash` | `b4c9554247f14b9a281f5f60df923f5e` |
| `Authorization` | `Basic {base64(mobile-api-{region}:mobile-api-{region})}` |
| `x-device-id` | Номер сборки Android (например, `AP3A.240905.015`) |

Аутентифицированные запросы добавляют:

| Заголовок | Значение |
|-----------|----------|
| `authorizationtest` | `Bearer {JWT access token}` |

## Формат ответа

Все ответы API имеют одинаковую структуру:

```json
{
    "result": true,
    "statusCode": 200,
    "data": { ... }
}
```

Ответ с ошибкой:

```json
{
    "result": false,
    "statusCode": 400,
    "error": {
        "type": "PROVIDER_ERROR",
        "description": "Неверный логин или пароль."
    }
}
```

---

## Публичные эндпоинты (без авторизации)

### GET /app/version

Проверка совместимости версии приложения.

**Query-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `version` | string | Версия приложения (например, `3.0.12`) |

**Ответ `data`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `status` | int | 1 = совместимо |

```json
{ "status": 1 }
```

**Библиотека:** `async_check_version(session, region="rostov")` — standalone-функция, авторизация не требуется

---

### GET /contacts/regions

Получить список доступных регионов.

**Query-параметры:** нет

**Ответ `data`:** массив регионов

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | string | Название региона |
| `code` | string | Код региона для URL |
| `coordinates` | string | Координаты на карте (`"x, y"`) |

```json
[
    { "name": "Ростовская область", "code": "rostov", "coordinates": "458, 683" },
    { "name": "Воронежская область", "code": "voronezh", "coordinates": "506, 729" }
]
```

**Библиотека:** `async_get_regions(session)` — standalone-функция, авторизация не требуется

---

## Эндпоинты авторизации

### POST /user/auth

Аутентификация по email и паролю.

**Тело запроса:**

| Поле | Тип | Описание |
|------|-----|----------|
| `login` | string | Email |
| `authType` | string | Всегда `"email"` |
| `password` | string | Пароль |
| `region` | string | Код региона |
| `platform` | string | Всегда `"android"` |

**Ответ `data`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `accessToken` | string | JWT access token |
| `refreshToken` | string | JWT refresh token |
| `accessTokenExpires` | string | Дата/время истечения (`"YYYY-MM-DD HH:MM:SS"`) |
| `refreshTokenExpires` | string | Дата/время истечения |

```json
{
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "accessTokenExpires": "2026-06-09 19:42:16",
    "refreshTokenExpires": "2026-10-09 19:42:16"
}
```

**Примечание:** Неверный регион при верных учётных данных возвращает 400 «Неверный логин или пароль.»

**Библиотека:** `SimpleTNSEAuth.async_login()`

---

### POST /user/refresh-token

Обновление access token.

**Тело запроса:**

| Поле | Тип | Описание |
|------|-----|----------|
| `refreshToken` | string | Текущий refresh token |

**Ответ `data`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `accessToken` | string | Новый JWT access token |
| `accessTokenExpires` | string | Новая дата/время истечения |

```json
{
    "accessToken": "eyJ...",
    "accessTokenExpires": "2026-06-09 21:06:40"
}
```

**Библиотека:** `SimpleTNSEAuth.async_refresh_token()`

---

### POST /user/logout

Инвалидация текущих токенов. Требует заголовок `authorizationtest` с Bearer-токеном.

**Тело запроса:** нет

**Ответ `data`:** `[]`

**Библиотека:** `SimpleTNSEAuth.async_logout()`

---

## Эндпоинты пользователя

### GET /user

Получить информацию о текущем пользователе.

**Query-параметры:** нет

**Ответ `data`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | ID пользователя |
| `email` | string | Email пользователя |
| `region` | string | Код региона |

```json
{ "id": 50001, "email": "user@example.com", "region": "rostov" }
```

**Библиотека:** `TNSEApi.async_get_user_info()`

---

## Эндпоинты лицевых счетов

### GET /accounts

Получить список лицевых счетов пользователя.

**Query-параметры:** нет

**Ответ `data`:** массив лицевых счетов

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | ID лицевого счёта (внутренний) |
| `number` | string | 12-значный номер лицевого счёта |
| `name` | string | Название (может быть пустым) |
| `address` | string | Адрес |
| `isueAvaliable` | bool | Доступность сервиса ИСУЭ |
| `initial_year` | int | Начальный год |

```json
[
    {
        "id": 100001,
        "number": "610000000001",
        "name": "",
        "address": "г Ростов-на-Дону,ул Примерная,д.1",
        "isueAvaliable": false,
        "initial_year": 2020
    }
]
```

**Библиотека:** `TNSEApi.async_get_accounts()`

---

### GET /accounts/{account_id}

Получить детальную информацию о лицевом счёте по внутреннему ID.

**Path-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `account_id` | int | Внутренний ID (из ответа `/accounts`) |

**Ответ `data`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | ID лицевого счёта |
| `number` | string | 12-значный номер |
| `name` | string | Название |
| `address` | string | Адрес |
| `phone` | string | Телефон |
| `numberPersons` | int | Количество зарегистрированных жильцов |
| `totalArea` | float | Общая площадь (м²) |
| `livingArea` | float | Жилая площадь (м²) |
| `document` | string | Документ |
| `tenantCategory` | string | Категория жильца |
| `seasonRatio` | float | Сезонный коэффициент |
| `countersInfo` | array | Информация о счётчиках (см. ниже) |

Элемент `countersInfo`:

| Поле | Тип | Описание |
|------|-----|----------|
| `number` | string | Номер счётчика |
| `place` | string | Место установки |
| `checkingDate` | string | Дата следующей поверки (`"DD.MM.YYYY"`) |

```json
{
    "id": 100001,
    "number": "610000000001",
    "address": "г Ростов-на-Дону,ул Примерная,д.1",
    "totalArea": 65,
    "seasonRatio": 0.9,
    "countersInfo": [
        { "number": "10000001", "place": "", "checkingDate": "01.01.2040" }
    ]
}
```

**Библиотека:** `TNSEApi.async_get_account_info(account_id)`

---

### GET /main-page/debt/info

Получить информацию о задолженности для главной страницы.

**Query-параметры:** нет

**Ответ `data`:** `[]` (или массив элементов задолженности)

**Библиотека:** `TNSEApi.async_get_main_page_debt_info()`

---

### GET /information

Получить общую информацию по лицевому счёту.

**Query-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `account` | string | 12-значный номер лицевого счёта |

**Ответ `data`:** `[]` (или массив информационных элементов)

**Библиотека:** `TNSEApi.async_get_information(account)`

---

## Эндпоинты счётчиков

### GET /counters

Получить счётчики (приборы учёта) для лицевого счёта.

**Query-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `account` | string | 12-значный номер лицевого счёта |

**Ответ `data`:** массив счётчиков

| Поле | Тип | Описание |
|------|-----|----------|
| `counterId` | string | ID счётчика |
| `rowId` | string | ID строки (для передачи показаний) |
| `installationType` | string | Тип установки |
| `tariff` | int | Количество тарифных зон (1 = однотарифный, 2 = день/ночь, 3 = день/ночь/пик) |
| `checkingDate` | string | Дата следующей поверки (`"DD.MM.YYYY"`) |
| `lastReadings` | array | Последние показания по тарифным зонам |

Элемент `lastReadings`:

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | string | Название тарифной зоны (например, «День», «Ночь») |
| `value` | string | Текущее показание |
| `date` | string | Дата показания (`"DD.MM.YY"`) |

```json
[
    {
        "counterId": "10000001",
        "rowId": "2000001",
        "tariff": 2,
        "checkingDate": "01.01.2040",
        "lastReadings": [
            { "name": "День", "value": "3500", "date": "24.01.26" },
            { "name": "Ночь", "value": "1500", "date": "24.01.26" }
        ]
    }
]
```

**Библиотека:** `TNSEApi.async_get_counters(account)`

---

### GET /counters/{counter_id}/readings

Получить историю показаний для конкретного счётчика.

**Path-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `counter_id` | string | ID счётчика (из ответа `/counters`) |

**Query-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `account` | string | 12-значный номер лицевого счёта |

**Ответ `data`:** массив записей показаний (сортировка по дате, убывание)

| Поле | Тип | Описание |
|------|-----|----------|
| `date` | string | Дата показания (`"DD.MM.YY"`) |
| `readings` | array | Показания по тарифным зонам |

Элемент `readings`:

| Поле | Тип | Описание |
|------|-----|----------|
| `title` | string | Зона + номер ПУ (например, «День ПУ 10000001») |
| `value` | int | Показание счётчика |
| `consumption` | int | Расход с предыдущего показания |

```json
[
    {
        "date": "24.01.26",
        "readings": [
            { "title": "День ПУ 10000001", "value": 2689, "consumption": 72 },
            { "title": "Ночь ПУ 10000001", "value": 1022, "consumption": 27 }
        ]
    }
]
```

**Библиотека:** `TNSEApi.async_get_counter_readings(counter_id, account)`

---

### POST /counters/send-readings

Передать показания счётчика.

**Тело запроса:**

| Поле | Тип | Описание |
|------|-----|----------|
| `account` | string | 12-значный номер лицевого счёта |
| `rowId` | string | ID строки (из ответа `/counters`) |
| `readings` | array[string] | Показания по тарифным зонам (порядок соответствует `lastReadings`) |
| `platform` | string | Всегда `"android"` |

```json
{
    "account": "610000000001",
    "rowId": "2000001",
    "readings": ["2690", "1023"],
    "platform": "android"
}
```

**Ответ `data`:** `[]`

**Библиотека:** `TNSEApi.async_send_readings(account, row_id, readings)`

---

## Эндпоинты платежей

### GET /payments/new-balance

Получить текущий баланс и информацию об оплате.

**Query-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `account` | string | 12-значный номер лицевого счёта |

**Ответ `data`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `sumToPay` | float | Итого к оплате |
| `sumToPayRaw` | float | Сумма без округления |
| `debt` | float | Текущая задолженность |
| `debtAbs` | float | Абсолютная задолженность |
| `peniDebt` | float | Задолженность по пени |
| `closedMonth` | string | Последний закрытый месяц (`"DD.MM.YY"`) |
| `sumWithoutCheckbox` | float | Сумма без дополнительных начислений |
| `sumWithCheckbox` | float | Сумма с дополнительными начислениями |
| `hasAvans` | bool | Наличие аванса |
| `avansTotal` | float | Общий аванс |
| `avansType` | string | Тип аванса (`"avg"` и др.) |
| `avansMain` | float | Основной аванс |
| `hasRecalc` | bool | Наличие перерасчёта |
| `recalc` | float | Сумма перерасчёта |
| `hasLosses` | bool | Наличие потерь |
| `losses` | float | Сумма потерь |
| `hasOdn` | bool | Наличие ОДН (общедомовые нужды) |
| `odn` | float | Сумма ОДН (общедомовые нужды) |
| `hasPeniForecast` | bool | Наличие прогноза пени |
| `peniForecast` | float | Прогноз пени |
| `hasOtherServicesDebt` | bool | Наличие задолженности по другим услугам |
| `otherServicesDebt` | float | Задолженность по другим услугам |

```json
{
    "sumToPay": 1500.5,
    "debt": 0,
    "peniDebt": 0,
    "closedMonth": "01.02.26",
    "hasAvans": true,
    "avansTotal": 1500.5,
    "avansType": "avg"
}
```

**Библиотека:** `TNSEApi.async_get_balance(account)`

---

## Эндпоинты квитанций

### GET /invoices/settings

Получить настройки email-уведомлений о квитанциях.

**Query-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `account` | string | 12-значный номер лицевого счёта |

**Ответ `data`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `email` | string | Email для доставки квитанций |
| `status` | bool | Включена ли email-доставка |

```json
{ "email": "user@example.com", "status": true }
```

**Библиотека:** `TNSEApi.async_get_invoice_settings(account)`

---

### GET /invoices

Получить список квитанций за год.

**Query-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `account` | string | 12-значный номер лицевого счёта |
| `year` | int | Год |

**Ответ `data`:** массив квитанций

| Поле | Тип | Описание |
|------|-----|----------|
| `type` | int | Тип элемента (3 = квитанция) |
| `title` | string | Название квитанции |
| `date` | string | Дата квитанции (`"DD.MM.YYYY"`) |
| `description` | string | Описание |

```json
[
    {
        "type": 3,
        "title": "Квитанция за Январь 2026",
        "date": "01.01.2026",
        "description": "Лицевой счет 610000000001"
    }
]
```

**Библиотека:** `TNSEApi.async_get_invoices(account, year)`

---

### GET /invoices/get-file

Получить файл квитанции в формате base64-encoded PDF.

**Query-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `account` | string | 12-значный номер лицевого счёта |
| `date` | string | Дата квитанции (`"DD.MM.YYYY"`) |

**Ответ `data`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `file` | string | PDF в формате base64 |

```json
{ "file": "JVBERi0xLjUK..." }
```

**Библиотека:** `TNSEApi.async_get_invoice_file(account, date)`

---

## Эндпоинт истории

### GET /history

Получить историю операций (платежи, показания, квитанции) за конкретный месяц.

**Query-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `account` | string | 12-значный номер лицевого счёта |
| `year` | int | Год |
| `month` | int | Месяц (1-12) |

**Ответ `data`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `filters` | array | Доступные типы фильтров |
| `items` | array | Элементы истории |

Элемент `filters`:

| Поле | Тип | Описание |
|------|-----|----------|
| `type` | int | ID типа фильтра |
| `title` | string | Название фильтра |

Типы фильтров: 1 = «Платежи», 2 = «Показания», 3 = «Квитанции»

Элемент `items` (тип 2 — показания):

| Поле | Тип | Описание |
|------|-----|----------|
| `type` | int | Тип элемента |
| `title` | string | Заголовок |
| `date` | string | Дата (`"DD.MM.YY"`) |
| `indications` | array | Показания (аналогично readings) |

Элемент `items` (тип 1 — платёж):

| Поле | Тип | Описание |
|------|-----|----------|
| `type` | int | Тип элемента |
| `title` | string | Заголовок платежа |
| `date` | string | Дата |
| `description` | string | Описание |
| `amount` | float | Сумма платежа |

```json
{
    "filters": [
        { "type": 1, "title": "Платежи" },
        { "type": 2, "title": "Показания" },
        { "type": 3, "title": "Квитанции" }
    ],
    "items": [
        {
            "type": 2,
            "title": "Показания",
            "date": "09.02.26",
            "indications": [
                { "title": "День ПУ 10000001", "value": 5105, "consumption": 1 }
            ]
        },
        {
            "type": 1,
            "title": "Платеж от 08.02.26",
            "date": "08.02.26",
            "description": "Лицевой счет 610000000001",
            "amount": 2000.0
        }
    ]
}
```

**Библиотека:** `TNSEApi.async_get_history(account, year, month)`
