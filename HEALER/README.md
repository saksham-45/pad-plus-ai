# HEALER — модуль самодиагностики и самовосстановления

**Статус:** ✅ Все 7 фаз завершены · 121 тест · 0 зависимостей (Python stdlib)

---

**English version:** `README.en.md`

**Полный отчёт о проекте:** `docs/HEALER_PROJECT.md`

---

## Что умеет

1. **Наблюдать** — X-RAY ядро отслеживает каждый запрос, каждый вызов, каждый span
2. **Диагностировать** — 7 детекторов находят проблемы: медленные импорты, ошибки без fallback, мёртвый код, утечки, нарушения причинности, аномалии задержек
3. **Исправлять** — AST-трансформер генерирует патчи (lazy import, try/finally, timeout, remove dead code, close resource)
4. **Проверять** — PatchResult с apply + rollback (Фаза 3 Verification — следующий шаг)
5. **Обучаться** — MetaLearner запоминает результаты, адаптирует пороги и веса

## Новое (v1.1)

- **Streaming диагностика** — `run_diagnostics(event_callback=...)` передаёт события в реальном времени: `detector_start`, `detector_found`, `detector_done`
- **Store изоляция** — `TraceStoreRegistry` с per-project изоляцией, исключены гонки данных между проектами
- **Typed DiagnosticReport** — детекторы возвращают `DiagnosticReport`, не `dict`. `compat_mode=True` для обратной совместимости
- **API версионирование** — `/api/v1/*` endpoints + `X-API-Version` header
- **Graceful shutdown** — atexit, SIGTERM, `orchestrator.stop()`, флаг `_stop_event` в run_cycle
- **Restart notification** — `.restart_required` файл-флаг, `GET /api/v1/restart-required`
- **Detector ABC** — `BaseDetector` с `@abstractmethod detect()`, все 7 детекторов наследуют
- **Thread-safe store** — `threading.RLock()` на всех публичных методах TraceStore
- **Schema versioning** — `_schema_version` в JSON на диске, skip при несовпадении
- **Meta retention** — `_prune()` с `max_age_days`/`max_records`, защита старых записей

## Быстрый старт

```bash
cd HEALER

# Демо: генерация трейсов + диагностика
python main.py

# CLI диагностика (с streaming событиями в реальном времени)
python -m healer.diagnostics.runner

# JSON output
python -m healer.diagnostics.runner --quiet --fail-on error

# Мониторинг в реальном времени
python -m healer.diagnostics.runner --watch --interval 30

# Тесты (121)
python -m pytest tests/

# Smoke test (полная проверка всех слоёв)
python scripts/smoke_test.py

# Оркестратор API (версия v1)
python -m healer.api --port 8090
# → http://127.0.0.1:8090/api/v1/status

# Viewer (веб-дашборд)
python -m healer.viewer
# → http://127.0.0.1:8085
```

## HEALER Viewer — веб-дашборд

Встроенный дашборд для наблюдения. Сам инструментирован X-RAY — HEALER может диагностировать его.

```bash
python -m healer.viewer
# → http://127.0.0.1:8085
```

Или из оригинальной папки:
```bash
cd ../healer-viewer
python viewer.py
```

## Архитектура

```
┌──────────────────────────────────────────────────────┐
│ Layer 5: Meta-Learning ✅                            │
│ MetaLearner · AdaptiveStrategies · retention(_prune) │
├──────────────────────────────────────────────────────┤
│ Layer 4: Orchestrator ✅                             │
│ monitor / suggest / auto + API v1 + SSE + graceful   │
│ shutdown + restart notification                      │
├──────────────────────────────────────────────────────┤
│ Layer 3: Verification ✅                             │
│ TestRunner · LintChecker · MetricComparator · Rollback│
├──────────────────────────────────────────────────────┤
│ Layer 2: Patch Engine ✅                             │
│ PythonPatcher (AST) · JSPatcher                      │
│ 5 patterns + PatchResult (diff, apply, rollback)     │
├──────────────────────────────────────────────────────┤
│ Layer 1: Diagnostics ✅                             │
│ 7 detectors (BaseDetector ABC) · streaming events    │
│ CLI runner · integration tests                       │
├──────────────────────────────────────────────────────┤
│ Layer 0: X-RAY Kernel ✅                             │
│ 17 modules · Trace/Span · persistence · schema v1    │
│ TraceStoreRegistry · thread-safe (RLock)             │
└──────────────────────────────────────────────────────┘
```

## Структура

```
HEALER/
├── aethon/xray/              # X-RAY kernel (17 файлов)
│   ├── trace_store.py        # TraceStoreRegistry, RLock, schema versioning
│   └── version.py            # API_VERSION = "1.0.0"
├── healer/
│   ├── diagnostics/
│   │   ├── base.py           # BaseDetector ABC ★
│   │   ├── report.py         # DiagnosticReport, ReportSeverity
│   │   ├── runner.py         # run_diagnostics(event_callback=) ★
│   │   ├── span_analyzer.py  # 7 детекторов (BaseDetector)
│   │   ├── slow_import.py
│   │   ├── error_path.py
│   │   ├── dead_code.py
│   │   ├── resource_leak.py
│   │   ├── causal_violation.py
│   │   ├── latency_anomaly.py
│   │   └── integration_test.py
│   ├── patcher/              # Layer 2 (5 паттернов)
│   │   ├── base.py / result.py
│   │   ├── python_patcher.py
│   │   ├── js_patcher.py
│   │   └── patterns/
│   ├── verifier/             # Layer 3
│   ├── orchestrator.py       # Layer 4 (stop(), _stop_event)
│   ├── api.py                # /api/v1/*, graceful shutdown
│   ├── meta/
│   │   ├── meta_learner.py   # _prune(), retention
│   │   └── strategies.py
│   └── __init__.py
├── tests/                      # 121 тест
├── data/trace_store/           # трейсы на диске
├── docs/
│   ├── ADDING_DETECTOR.md      # BaseDetector ABC
│   ├── ADDING_PATTERN.md       # BasePattern ABC
│   ├── FOR_HUMANS.md           # человеческое описание
│   ├── USE_CASES.md            # сценарии применения
│   ├── HEALER_PROJECT.md       # полный отчёт
│   ├── HEALER_ROADMAP.md       # дорожная карта
│   └── HEALER_STRATEGY.md      # стратегия
├── dev-requirements.txt        # pytest, mypy, ruff (для CI)
├── scripts/
│   └── smoke_test.py
├── main.py
├── CHANGELOG.md                # история изменений
├── README.en.md                # English version
└── README.md

healer-viewer/                  # отдельная папка (дублирует healer/viewer/)
├── viewer.py
├── start.bat
└── static/index.html
```

## API endpoints (v1)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/status` | Статус оркестратора |
| GET | `/api/v1/history` | История healing-циклов |
| GET | `/api/v1/diagnostics` | Список детекторов |
| GET | `/api/v1/patchers` | Список патчеров |
| GET | `/api/v1/live` | Live status |
| GET | `/api/v1/events` | SSE (real-time) |
| GET | `/api/v1/restart-required` | Флаг необходимости рестарта |
| POST | `/api/v1/run` | Запустить healing cycle |
| POST | `/api/v1/mode` | Сменить режим |

Все ответы содержат заголовок `X-API-Version: 1.0.0`.

## Технологии

- **Python 3.12+** — единственное требование
- **Zero external dependencies** — весь код на stdlib
- **AST** — синтаксические деревья для патчинга Python
- **JSON on disk** — хранение трейсов, schema versioning
- **threading.RLock** — thread-safe store
- **HTTP.server** — встроенный HTTP-сервер (stdlib)

## Прогресс

| Фаза | Статус | Часы |
|------|--------|------|
| 0. X-RAY Kernel | ✅ | 12 |
| 1. Diagnostics | ✅ | 14 |
| 2. Patch Engine | ✅ | 20 |
| 3. Verification | ✅ | 8 |
| 4. Orchestrator | ✅ | 14 |
| 5. Meta-обучение | ✅ | 10 |
| 6. Документация/CI | ✅ | 8 |
| 7. Архитектурные фиксы (10 проблем) | ✅ | + |
| **Всего** | **100%** | **86+** |
