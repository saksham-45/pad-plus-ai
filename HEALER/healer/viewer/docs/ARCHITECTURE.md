# Архитектура HEALER Viewer

## Общая схема

```
┌─────────────────────────────────────────────┐
│              Browser (SPA)                   │
│         static/index.html                    │
│  ┌─────────┬──────────┬──────────┐          │
│  │ Overview│ Traces   │ Self-Diag│          │
│  └────┬────┴────┬─────┴────┬─────┘          │
│       │         │          │                 │
└───────┼─────────┼──────────┼─────────────────┘
        │  HTTP   │          │
┌───────┼─────────┼──────────┼─────────────────┐
│       ▼         ▼          ▼                  │
│            viewer.py (HTTP server)            │
│  ┌──────────────────────────────────────┐     │
│  │          HTTP Handlers              │     │
│  │  /api/status  /api/traces           │     │
│  │  /api/invoke-healer  /api/patch     │     │
│  │  /api/patch/apply  /api/patch/rollback    │
│  └──────────┬───────────────────────────┘     │
│             │                                 │
│  ┌──────────▼───────────────────────────┐     │
│  │        X-RAY Instrumentation         │     │
│  │  Каждый запрос → trace + span       │     │
│  │  Пишет в data/trace_store/           │     │
│  └──────────┬───────────────────────────┘     │
│             │                                 │
│  ┌──────────▼───────────────────────────┐     │
│  │       HEALER Integration Layer       │     │
│  │  Прямой импорт Python-модулей HEALER │     │
│  │  (без subprocess, без pipe)          │     │
│  └─────────────────────────────────────────────┘
└─────────────────────────────────────────────────┘
```

## Ключевые решения

### 1. Прямой импорт HEALER (не subprocess)

Viewer не вызывает HEALER через shell/subprocess. Вместо этого:

```python
from aethon.xray.trace_store import store
store.configure_persistence(target_path)

from healer.diagnostics.runner import run_diagnostics
reports = run_diagnostics()
```

**Почему:** subprocess на Windows ломает Unicode — русский текст превращается в кракозябры. Прямой импорт гарантирует корректную кодировку.

### 2. X-RAY инструментация

Каждый HTTP-запрос к viewer создаёт X-RAY trace:

```python
trace = start_trace(f"viewer.{path}")
span = start_span(SpanKind.DIAGNOSTIC, "operation")
try:
    # обработка запроса
    span.end("ok")
except:
    span.end("error")
finally:
    trace.end()
```

Трейсы пишутся в `data/trace_store/` — HEALER может их прочитать и диагностировать.

### 3. Self-healing cycle

1. Viewer пишет трейсы → HEALER читает → находит проблемы
2. Viewer отображает отчёты → человек/CB нажимает Patch
3. PythonPatcher (HEALER) генерирует diff
4. diff применяется к viewer.py
5. Бэкап сохраняется как viewer.py.healer.bak
6. Viewer перезапускается (ручная операция)

### 4. SPA без фреймворков

Одна HTML-страница с чистым JavaScript. Используются:
- `fetch()` для API
- `innerHTML` для рендеринга таблиц
- CSS Grid/Flex для layout

## Процесс запуска

1. `python viewer.py`
2. Инициализация X-RAY: `init_xray()` → `store.configure_persistence()`
3. Boot-трейс: `start_trace("viewer.startup")`
4. Старт HTTP-сервера на `127.0.0.1:8085`
5. Каждый запрос → новый trace
6. Каждый запуск диагностики → вызов HEALER через прямой импорт
