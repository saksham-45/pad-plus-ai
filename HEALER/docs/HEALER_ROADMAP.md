# HEALER — Дорожная карта

**Статус:** Фаза 0 ✅ · Фаза 1 ✅ · Фаза 2 ✅ · дальше → Фаза 3

**Полная стратегия:** `HEALER_STRATEGY.md`

---

## Фаза 0: X-RAY Kernel ✅ (готова)

X-RAY ядро работает. Трейсы пишутся на диск, causal integrity, consistency audit.

| # | Задача | Статус |
|---|--------|--------|
| 0.0 | `aethon/xray/` — ядро (17 модулей) | ✅ |
| 0.1 | Trace/Span модель с logical_ts | ✅ |
| 0.2 | TraceStore in-memory + disk JSON | ✅ |
| 0.3 | HTTP propagation (5 заголовков) | ✅ |
| 0.4 | Causal Validator (4 проверки) | ✅ |
| 0.5 | Consistency Audit (5 проверок) | ✅ |
| 0.6 | Retention Policy (4 pass) | ✅ |
| 0.7 | Data Sanitizer (scan + repair) | ✅ |
| 0.8 | Diagnostics (5 checks) | ✅ |
| 0.9 | DTO + Normalizer control plane | ✅ |
| 0.10 | Manual Scenarios (A/B/C) | ✅ |

**→ Критерий:** Данные на диске, recovery после рестарта, 53 теста проходят

---

## Фаза 1: Diagnostic Rules Engine ✅ (готова)

7 детекторов + CLI runner + интеграционные тесты на синтетических данных.

| # | Задача | Статус |
|---|--------|--------|
| 1.1 | `DiagnosticReport` — структурированный отчёт | ✅ |
| 1.2 | `SpanAnalyzer` — дубликаты, orphan, глубина | ✅ |
| 1.3 | `SlowImportDetector` — импорты/init > 100ms | ✅ |
| 1.4 | `ErrorPathDetector` — error без fallback | ✅ |
| 1.5 | `DeadCodeDetector` — неиспользуемые компоненты | ✅ |
| 1.6 | `ResourceLeakDetector` — незавершённые spans | ✅ |
| 1.7 | `CausalViolationDetector` — обёртка causal_validator | ✅ |
| 1.8 | `LatencyAnomalyDetector` — выбросы > 3 sigma | ✅ |
| 1.9 | CLI runner (--watch, --quiet, --fail-on, --output) | ✅ |
| 1.10 | Интеграционный тест (9 синтетических сценариев) | ✅ |
| 1.11 | Unit-тесты (20 тестов) | ✅ |

**→ Критерий:** Детекторы работают на реальных X-RAY данных, пример: 27 отчётов на 12 трейсах

---

## Фаза 2: Patch Engine ✅ (готова)

AST-трансформер для Python + JS-патчер. 5 паттернов, apply + rollback.

| # | Задача | Статус |
|---|--------|--------|
| 2.1 | `PythonPatcher` — AST-трансформации на Python | ✅ |
| 2.2 | `JSPatcher` — regex-трансформации для JS | ✅ |
| 2.3 | Паттерн lazy_import — import → внутрь функции | ✅ |
| 2.4 | Паттерн try_finally — try/finally с cleanup | ✅ |
| 2.5 | Паттерн add_timeout — timeout=30 к HTTP вызовам | ✅ |
| 2.6 | Паттерн remove_dead — удаление мёртвого кода | ✅ |
| 2.7 | Паттерн close_resource — open → with-блок | ✅ |
| 2.8 | `PatchResult` — diff, apply, rollback, backup | ✅ |
| 2.9 | `PATTERN_DETECTOR_MAP` — маппинг детектор→паттерн | ✅ |
| 2.10 | Unit-тесты (33 теста) | ✅ |

**→ Критерий:** Каждый паттерн = корректный AST diff, apply + rollback, 33/33 тестов

---

## Фаза 3: Verification Layer ✅ (готова)

Создан верификатор, подтверждающий корректность исправлений.

| # | Задача | Статус |
|---|--------|--------|
| 3.1 | `verifier/` пакет + `VerificationResult` | ✅ |
| 3.2 | `TestRunner` — pytest/npm test (автоопределение) | ✅ |
| 3.3 | `LintChecker` — ruff, mypy, eslint | ✅ |
| 3.4 | `MetricComparator` — метрики до/after (1.2x порог) | ✅ |
| 3.5 | `RollbackEngine` — backup restore + cleanup | ✅ |
| 3.6 | Тесты (21 шт.) | ✅ |

**→ Критерий:** Verifier запускает тесты проекта, линтеры, сравнивает метрики, откатывает. 74/74 общих тестов.

---

## Фаза 4: Orchestrator ✅ (готова)

Соединяет все слои: monitor/suggest/auto + SSE events + API.

| # | Задача | Статус |
|---|--------|--------|
| 4.1 | `orchestrator.py` — SelfHealingLoop | ✅ |
| 4.2 | Режимы: monitor / suggest / auto | ✅ |
| 4.3 | SSE endpoint для real-time событий | ✅ |
| 4.4 | API endpoints (status, history, diagnostics, patchers) | ✅ |
| 4.5 | Интеграция с X-RAY trace (каждый цикл = trace) | ✅ |
| 4.6 | Тесты (17 шт.) | ✅ |

**→ Критерий:** Полный цикл: diagnose → patch → verify → apply/rollback. 91/91 общих тестов.

---

## Фаза 5: Meta-обучение

Система учится на своих исправлениях.

| # | Задача | Часы |
|---|--------|------|
| 5.1 | MetaLearner — статистика успешности | 2 |
| 5.2 | Адаптивные пороги + веса диагностов | 2 |
| 5.3 | Тесты | 2 |

---

## Фаза 6: Документация и CI/CD ✅ (готова)

| # | Задача | Статус |
|---|--------|--------|
| 6.1 | Документация архитектуры (HEALER_STRATEGY.md) | ✅ |
| 6.2 | Документация API (docs/API.md) | ✅ |
| 6.3 | Документация добавления диагностов (docs/ADDING_DETECTOR.md) | ✅ |
| 6.4 | Документация добавления патчей (docs/ADDING_PATTERN.md) | ✅ |
| 6.5 | GitHub Actions CI (.github/workflows/ci.yml) | ✅ |
| 6.6 | Smoke test (scripts/smoke_test.py + smoke.bat) | ✅ |
| 6.7 | Deploy script (scripts/deploy.bat) | ✅ |

**→ Критерий:** Smoke test проходит, CI готов, документация для разработчиков есть.

---

## Итого: 86 часов / ~17 дней

| Фаза | Статус | Часы |
|------|--------|------|
| 0. X-RAY Kernel | ✅ | 12 |
| 1. Diagnostics | ✅ | 14 |
| 2. Patch Engine | ✅ | 20 |
| 3. Verification | ✅ | 8 |
| 4. Orchestrator | ✅ | 14 |
| 5. Meta-обучение | ✅ | 10 |
| 6. Документация/CI | ✅ | 8 |
| **Всего** | **86/86ч (100%)** | **86** |

---

## Структура проекта

```
HEALER/                          # Разработка HEALER
├── aethon/xray/                 # X-RAY kernel (ядро)
│   ├── trace.py, span.py        # Модели Trace/Span
│   ├── trace_store.py           # Хранилище in-memory + disk
│   ├── causal_validator.py      # 4 проверки целостности
│   ├── consistency_audit.py     # 5 проверок консистентности
│   ├── diagnostics.py           # 5 встроенных checks
│   ├── contracts.py             # Event/Trace/Span/Metric схемы
│   ├── metrics.py               # Counter, Gauge, Histogram
│   ├── http_propagation.py      # 5 X-RAY заголовков
│   ├── event.py                 # Event система
│   ├── data_sanitizer.py        # Очистка данных
│   ├── retention.py             # Политика хранения
│   ├── manual_scenarios.py      # Тестовые сценарии A/B/C
│   ├── version.py               # Версионирование
│   └── control_plane/           # DTO + нормализация
│
├── healer/                      # Self-Healing модуль
│   ├── diagnostics/             # Layer 1 (7 детекторов)
│   │   ├── report.py            # DiagnosticReport + severity/category
│   │   ├── span_analyzer.py     # Дубликаты, orphan, глубина
│   │   ├── slow_import.py       # Медленные импорты
│   │   ├── error_path.py        # Ошибки без fallback
│   │   ├── dead_code.py         # Неиспользуемые компоненты
│   │   ├── resource_leak.py     # Утечки ресурсов
│   │   ├── causal_violation.py  # Нарушения причинности
│   │   ├── latency_anomaly.py   # Аномалии задержек
│   │   ├── runner.py            # CLI (--watch, --fail-on, --output)
│   │   └── integration_test.py  # 9 синтетических сценариев
│   │
│   ├── patcher/                 # Layer 2 (5 паттернов)
│   │   ├── base.py              # BasePatcher ABC
│   │   ├── result.py            # PatchResult (diff, apply, rollback)
│   │   ├── python_patcher.py    # AST-трансформер Python
│   │   ├── js_patcher.py        # JS-патчер (regex)
│   │   └── patterns/
│   │       ├── lazy_import_py.py   # import → внутрь функции
│   │       ├── try_finally_py.py   # try/finally с cleanup
│   │       ├── add_timeout_py.py   # timeout для HTTP
│   │       ├── remove_dead_py.py   # удаление мёртвого кода
│   │       └── close_resource_py.py # open → with-блок
│   │
│   └── __init__.py
│
├── tests/                       # Тесты (53 шт.)
│   ├── test_diagnostics.py      # 20 тестов детекторов
│   └── test_patcher.py          # 33 теста патчей
│
├── data/trace_store/            # Трейсы на диске
├── main.py                      # Демо-запуск
├── HEALER_STRATEGY.md           # Полная стратегия
├── HEALER_ROADMAP.md            # Эта дорожная карта
└── README.md                    # Быстрый старт

healer-viewer/                   # Отдельное приложение-наблюдатель
├── viewer.py                    # HTTP сервер + X-RAY инструментация
├── start.bat                    # Запуск (открывает браузер :8085)
├── static/index.html            # Веб-дашборд (4 вкладки)
├── data/trace_store/            # Свои трейсы (HEALER их диагностирует)
└── README.md
```

---

## Быстрый старт

```bash
cd HEALER

# Установка (0 зависимостей — только Python stdlib)
pip install pytest  # опционально, для тестов

# Запустить демо
python main.py

# Запустить диагностику HEALER
python -m healer.diagnostics.runner

# Запустить диагностику другого проекта
python -m healer.diagnostics.runner --path ../healer-viewer/data/trace_store

# Unit-тесты (53 шт.)
python -m pytest tests/

# Интеграционные тесты (9 сценариев)
python -m healer.diagnostics.integration_test

# Запустить HEALER Viewer (отдельное приложение)
cd ../healer-viewer
start.bat
```
