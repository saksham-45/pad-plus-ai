# HEALER — где и как применять

HEALER — модуль самодиагностики и самовосстановления для Python-проектов. Работает на чистом stdlib, zero external dependencies.

---

## 1. Пет-проекты и стартапы

**Когда:** вы пишете Telegram-бота, веб-сервер на FastAPI, парсер. Проект один, всё в одной папке.

**Как:**
1. Скопировать папку `aethon/` (X-RAY ядро) в свой проект
2. Вставить 2 строки: `start_trace("request")` при старте, `trace.end()` в конце
3. Запустить `python -m healer.diagnostics.runner --path ./data/trace_store`

**Что найдёт:** незакрытые файлы, медленные импорты, мёртвый код, ошибки без обработки

**Почему:** zero dep — не нужно `pip install`, просто скопировал и пошло

---

## 2. Продакшн-системы (наблюдение в реальном времени)

**Когда:** сервер обрабатывает тысячи запросов в день. Нужно знать, что внутри, и реагировать автоматически.

**Как:**
1. Встроить X-RAY во входные точки: HTTPS-запрос → trace, внешний API → span, работа с БД → span
2. Запустить watch-режим: `python -m healer.diagnostics.runner --watch --interval 60`
3. Или HTTP API: `python -m healer.api --port 8090`, дёргать `/api/v1/run` из cron

**Что найдёт:** аномалии задержек, утечки (spans без end), нарушения причинности

**Почему:** X-RAY не async, не блокирует поток, пишет на диск. При падении HEALER приложение продолжает работать.

---

## 3. CI/CD пайплайн (проверка перед деплоем)

**Когда:** перед выкаткой в продакшн нужно проверить, не появились ли проблемы.

**Как:**
```bash
# В CI скрипте (GitHub Actions, GitLab CI, Jenkins):
python -m healer.diagnostics.runner --quiet --fail-on error --output healer-report.json

# exit code 1 — пайплайн падает
```

**Что найдёт:** регрессии, мёртвый код, ошибки без fallback

**Почему:** не требует установки зависимостей в CI, `--quiet` даёт чистый JSON для парсинга

---

## 4. Self-healing (HEALER чинит сам себя)

**Когда:** HEALER продиагностировал проект, нашёл проблемы. Теперь может продиагностировать свой же код (или viewer).

**Как:**
1. `python -m healer.diagnostics.runner --path ../my-app/data/trace_store`
2. Запустить viewer: `cd ../healer-viewer && start.bat`
3. Viewer запускает диагностику на себе — HEALER чинит viewer.py

**Что найдёт:** проблемы в собственном коде (незавершённые spans → try/finally, мёртвый код → удаление)

**Почему:** TraceStoreRegistry изолирует трейсы проектов. HEALER не путает `my-app` и `healer-viewer`.

---

## 5. Монолит с модулями

**Когда:** большой проект с модулями `auth`, `payment`, `notifications`. Каждый пишет свои трейсы.

**Как:**
```bash
python -m healer.diagnostics.runner --path ./data/auth/trace_store --output auth-report.html
python -m healer.diagnostics.runner --path ./data/payment/trace_store --output payment-report.html
```

**Что найдёт:** для каждого модуля свои проблемы

**Почему:** store изолирован по папке, можно параллельно запускать диагностику на разных модулях

---

## Когда HEALER НЕ нужен

| Ситуация | Почему |
|----------|--------|
| Нет X-RAY в проекте | HEALER нечего анализировать, нужны трейсы на диске |
| Проект на чистом JS/TS без Python | X-RAY (ядро сбора трейсов) только для Python |
| Одноразовый скрипт | HEALER нужен там, где код живёт долго |
| Embedded / микроконтроллеры | HEALER требует Python 3.12+ и файловую систему |

---

## Таблица: проект → что HEALER даёт

| Тип проекта | Что найдёт | Режим | Формат |
|-------------|-----------|-------|--------|
| Веб-сервер (FastAPI/Flask) | Зависшие запросы, утечки, аномалии | `--watch` | HTML |
| Telegram-бот | Незакрытые соединения, медленные импорты | `monitor` | Таблица |
| CI/CD пайплайн | Регрессии, мёртвый код, ошибки без fallback | `--quiet` | JSON |
| Self-healing viewer | Проблемы в собственном коде | `auto` | Лайв-лента |
| Монолит (N модулей) | Модуль-specific проблемы | Раздельные запуски | N HTML |
| Исследовательский проект | Аномалии, нарушения причинности | `suggest` | HTML + рекомендации |

---

## Быстрый старт

```bash
# Демо — увидеть HEALER в действии
cd HEALER && python main.py

# Проверить свой проект
python -m healer.diagnostics.runner --path /путь/к/трейсам

# Непрерывный мониторинг
python -m healer.diagnostics.runner --watch --interval 30

# HTML-отчёт
python -m healer.diagnostics.runner --format html --output report.html
```

Установка: `git clone <url> && cd HEALER` — никаких `pip install`.
