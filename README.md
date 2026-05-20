# DPFuzz

**DPFuzz** — средство комбинированного фаззинг-тестирования веб-приложений с JSON RPC API.

Объединяет три метода в одном инструменте: генерацию данных, мутацию (через Radamsa) и фаззинг по словарю известных атак. По результатам сравнительного тестирования показывает F-меру **0.59** против 0.29–0.50 у аналогов (OWASP ZAP, Restler, PyFuzz, PyJFuzz).

Разработан в рамках ВКР «Разработка средства комбинированного фаззинг-тестирования веб-приложений», ИТМО, 2022.

---

## Возможности

| Функция | Описание |
|---|---|
| Генерационный фаззинг | Подстановка типизированных значений (`fuzzint`, `fuzzstr`, `fuzzbool`, `fuzzfloat`) |
| Мутационный фаззинг | Искажение структуры и значений JSON через [Radamsa](https://gitlab.com/akihe/radamsa) |
| Фаззинг по словарю | Подстановка атакующих payload из [fuzzdb](https://github.com/fuzzdb-project/fuzzdb) |
| Анализ ответов | Детектирование HTTP-ошибок, JSON-RPC кодов, чувствительных данных в ответе |
| Покрытие интерфейсов | Подсчёт проверенных API-методов за сессию |
| Мониторинг сервера | Сбор CPU/RAM через SSH во время фаззинга |
| Отчёты | Вывод в терминал, а также сохранение в `docx`, `json`, `txt` |
| Аутентификация | Токен или JSON-файл с логином/паролем, автообновление при истечении сессии |

---

## Требования

- Python 3.9+
- [Radamsa](https://gitlab.com/akihe/radamsa) — скомпилированный бинарник (необходим для мутационного фаззинга)
- [fuzzdb](https://github.com/fuzzdb-project/fuzzdb) — опционально, для словарного фаззинга

```bash
pip install requests paramiko simplejson docxtpl urllib3
```

Установка pyradamsa (Python-обёртка для Radamsa):
```bash
# Radamsa должен быть собран заранее и доступен в системе
pip install pyradamsa
```

---

## Быстрый старт

### 1. Подготовьте примеры запросов

Создайте директорию с JSON-примерами запросов к API. Каждый метод — отдельная поддиректория:

```
input_example/
├── user_get/
│   ├── 0.json       ← минимальный запрос
│   └── 1.json       ← расширенный запрос (опционально)
├── host_create/
│   └── 0.json
└── user_login/
    └── 0.json       ← используется для получения токена
```

Формат JSON-файла (JSON RPC 2.0):
```json
{
    "jsonrpc": "2.0",
    "method": "user.get",
    "params": {
        "output": "extend",
        "limit": 10
    },
    "auth": null,
    "id": 1
}
```

> **Готовые примеры для Zabbix API** — см. [zabbix-api-spec](https://github.com/denimoll/zabbix-api-spec).

### 2. Настройте конфигурацию

Отредактируйте `config.py`:

```python
CONFIG = {
    "URL": "http://your-app/",                         # URL приложения
    "PATH_TO_EXAMPLES": "/path/to/input_example",      # путь к примерам

    "TOKEN": "none",                                   # токен или "none"
    "AUTH_METHOD": "/path/to/input_example/user_login/0.json",  # или "none"

    "MAX_IFACE_REQUEST_COUNT": "default",              # запросов на метод за цикл
    "MAX_ERROR_COUNT": "none",                         # остановка при N ошибках
    "MAX_TIME": "none",                                # остановка через N секунд
    "ERRORS": [],                                      # доп. HTTP-коды ошибок
    "SENSITIVE_DATA": [],                              # ключевые слова в ответе

    "REPORT_FORMAT": "default",                        # default | txt | json | docx

    "SSH_IP": "",                                      # IP для мониторинга сервера
    "SSH_USER": "root",
    "SSH_PASSWORD": "",
}
```

### 3. Запустите фаззер

```bash
python3 main.py
```

---

## Словарный фаззинг (fuzzdb)

Словарь атак [fuzzdb](https://github.com/fuzzdb-project/fuzzdb) включён в репозиторий. DPFuzz автоматически использует его из пути:

```
fuzzdb/attack/all-attacks/all-attacks-unix.txt
```

Если файл присутствует, ~25% генерируемых значений будут взяты из словаря атак.

---

## Генерационный фаззинг — плейсхолдеры

Чтобы указать, какие типы значений генерировать, используйте плейсхолдеры в примерах:

```json
{
    "method": "item.get",
    "params": {
        "itemids": "fuzzint",
        "output": "fuzzstr",
        "active": "fuzzbool",
        "ratio": "fuzzfloat"
    }
}
```

DPFuzz автоматически создаёт такие файлы (`for_generation.json`) из ваших примеров перед запуском.

---

## Обнаруживаемые аномалии

| Тип | Условие |
|---|---|
| HTTP-ошибка | Код ответа 500 (и другие из `ERRORS`) |
| JSON-RPC ошибка вне диапазона | Код вне `[-32768, -32000]` |
| Чувствительные данные | Слово `select` (SQL) и значения из `SENSITIVE_DATA`) в теле ответа |
| Проблема аутентификации | Ответ `Not authorised` / `re-login` / 403 |
| Нарушение прав доступа | `no permissions`, `forbidden`, `no access` и т.д. |

---

## Форматы отчёта

```python
"REPORT_FORMAT": "docx"   # Word-документ в report/report.docx
"REPORT_FORMAT": "json"   # report/report.json
"REPORT_FORMAT": "txt"    # report/report.txt
"REPORT_FORMAT": "default" # только вывод в терминал
```

Для `docx` необходим файл `template.docx` в корне проекта.

---

## Поддерживаемые продукты

Любое веб-приложение с JSON RPC 2.0 API, в том числе:

- **[Zabbix](https://github.com/denimoll/zabbix-api-spec)** — система мониторинга сети (готовые примеры запросов)
- **Odoo** — ERP-система
- **Ethereum / Solana** — блокчейн-ноды
- Любые другие JSON RPC API

---

## Структура проекта

```
DPFuzz/
├── main.py                       ← точка входа, основной цикл фаззинга
├── config.py                     ← конфигурация и валидация параметров
├── change_values.py              ← генерация и мутация значений
├── check_response.py             ← анализ HTTP-ответов
├── create_common_jsons.py        ← подготовка объединённых примеров
├── create_jsons_for_generation.py ← создание файлов с плейсхолдерами
├── create_report.py              ← генерация отчётов
├── validate_json.py              ← валидация входных JSON-файлов
├── tests/                        ← автотесты (71 тест)
│   ├── conftest.py
│   ├── test_change_values.py
│   ├── test_check_response.py
│   ├── test_config.py
│   ├── test_create_common_jsons.py
│   ├── test_create_jsons_for_generation.py
│   └── test_validate_json.py
└── fuzzdb/                       ← словарь атак (fuzzdb, включён в репо)
```

---

## Запуск тестов

```bash
python3 -m pytest tests/ -v
```

---

## Метрики эффективности

Тестирование проводилось на уязвимом веб-приложении с использованием метрик классификации:

| Метрика | Значение |
|---|---|
| Достоверность (A) | 0.77 |
| Точность (P) | 0.42 |
| Полнота (R) | **1.0** |
| F-мера (F) | **0.59** |

DPFuzz обнаруживает все уязвимые места (Recall = 1.0) и на 9–30% эффективнее аналогов по F-мере.

---

## Roadmap

| Feature | Status |
|---|---|
| JSON-RPC 2.0 fuzzing | ✅ v1.0 |
| Parallel requests (ThreadPoolExecutor) | ✅ v1.0 |
| State save/resume | ✅ v1.0 |
| Environment variable configuration | ✅ v1.0 |
| REST API support | 🔜 planned |
| GraphQL support | 🔜 planned |
