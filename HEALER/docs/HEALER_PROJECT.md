# HEALER — Отчёт о проекте

**Дата завершения:** 2026-06-09  
**Статус:** 7/7 фаз ✅ (100%, 86 часов)  
**Тестов:** 121, все пройдены  
**Зависимостей:** 0 (только Python stdlib)  

---

## 1. Что это

HEALER — универсальный self-healing модуль. Он умеет:

1. **Наблюдать** — X-RAY ядро отслеживает каждый запрос и вызов
2. **Диагностировать** — 7 детекторов находят проблемы (медленные импорты, ошибки без fallback, мёртвый код, утечки, нарушения причинности, аномалии задержек)
3. **Исправлять** — AST-трансформер генерирует патчи (lazy import, try/finally, timeout, remove dead code, close resource)
4. **Проверять** — TestRunner запускает тесты, LintChecker проверяет стиль, MetricComparator сравнивает метрики
5. **Обучаться** — MetaLearner запоминает результаты, адаптирует пороги и веса
6. **Работать в 3 режимах** — monitor (только смотрю), suggest (предлагаю патчи), auto (чиню сам)

---

## 2. История разработки (7 фаз, 86 часов)

### Фаза 0: X-RAY Kernel (12 часов) — с чего всё началось

Проект начался с X-RAY-INTEGRATION-KIT — zero-dependency ядра observability. 

**Что было сделано:**
- Модели Trace и Span с logical_ts для причинности
- TraceStore in-memory + disk persistence (JSON)
- HTTP propagation (5 заголовков)
- Causal Validator (4 проверки: child_before_parent, child_outlives_parent, late_span, clock regression)
- Consistency Audit (5 проверок)
- Retention Policy (4 pass: to_dict, metadata_check, freeze_check, logical_ts_check)
- Data Sanitizer (scan + repair)
- In-app Diagnostics (5 checks)
- DTO + Normalizer в control_plane
- 3 ручных сценария (A/B/C) для демонстрации

**Итог:** 17 модулей ядра. Трейсы пишутся на диск, восстанавливаются после рестарта.

---

### Фаза 1: Diagnostic Rules Engine (14 часов)

Созданы 7 детекторов, CLI runner и интеграционные тесты.

| Детектор | Что находит | Тип |
|----------|------------|-----|
| SpanAnalyzer | Дубликаты span_id, missing parent, un-ended spans, глубина > 10 | integrity |
| SlowImportDetector | Импорты/init/setup > 100ms | performance |
| ErrorPathDetector | Error-спаны без sibling fallback | correctness |
| DeadCodeDetector | Компоненты, которые ни разу не вызывались | maintainability |
| ResourceLeakDetector | Незавершённые spans > 30s | resource |
| CausalViolationDetector | Обёртка над causal_validator (6 типов) | integrity |
| LatencyAnomalyDetector | Выбросы > 3 sigma от среднего по kind | performance |

**CLI runner:** `python -m healer.diagnostics.runner` с флагами `--watch`, `--quiet`, `--fail-on`, `--min-severity`, `--output`.

**Интеграционные тесты:** 9 синтетических сценариев (с проблемами + чистый) — каждый детектор проверен на живых данных.

**Пример на реальных данных (первые 12 трейсов):** 27 отчётов, из них 4 ошибки, 12 warning, 11 info.

---

### Фаза 2: Patch Engine (20 часов)

AST-трансформер для Python + JS-патчер.

| Паттерн | Язык | Что делает | Связанный детектор |
|---------|------|-----------|-------------------|
| lazy_import | Python | Переносит import из module-level в тело функции | SlowImportDetector |
| try_finally | Python | Оборачивает тело функции в try/finally с cleanup | ErrorPathDetector, SpanAnalyzer |
| add_timeout | Python | Добавляет timeout=30 к HTTP-вызовам | LatencyAnomalyDetector |
| remove_dead | Python | Удаляет неиспользуемые импорты/пустые функции | DeadCodeDetector |
| close_resource | Python | open() → with-блок | ResourceLeakDetector |
| add_timeout (JS) | JS | AbortSignal.timeout к fetch() | LatencyAnomalyDetector |
| try_finally (JS) | JS | try/finally с cleanup | ErrorPathDetector |

**PatchResult:** содержит `diff`, `.apply(backup=True)`, `.rollback()`. Backup-файлы `*.healer.bak`.

---

### Фаза 3: Verification Layer (8 часов)

| Компонент | Что делает |
|-----------|-----------|
| VerificationResult + PhaseVerdict | Единый формат результатов проверки |
| TestRunner | Автоопределяет pytest/npm → запускает → парсит вывод |
| LintChecker | Запускает ruff / mypy / eslint (автоопределение) |
| MetricComparator | Сравнивает метрики до/after с порогом 1.2x |
| RollbackEngine | Ищет `*.healer.bak` → восстанавливает → чистит |

---

### Фаза 4: Orchestrator (14 часов)

Главный управляющий модуль, соединяющий всё вместе.

**Архитектура SelfHealingLoop:**
```
Diagnostics → reports → [severity >= warning] → Patcher → diff
→ [mode == auto] → apply → Verifier (tests + lint + metrics)
→ [tests failed] → rollback
→ [tests passed] → keep + record in MetaLearner
```

**3 режима:**
- `monitor` — только диагностика, без изменений
- `suggest` — диагностика + генерация патчей, но без apply  
- `auto` — полный цикл: diagnose → patch → verify → apply/rollback

**API (HTTP, порт 8090):**
- `GET /api/status` — статус оркестратора
- `GET /api/history` — история healing-циклов
- `GET /api/diagnostics` — список детекторов
- `GET /api/patchers` — список патчеров
- `GET /api/live` — live status
- `GET /api/events` — SSE (real-time события)
- `POST /api/run` — запустить healing cycle
- `POST /api/mode` — сменить режим

Каждый healing cycle пишет свой X-RAY trace.

---

### Фаза 5: Meta-обучение (10 часов)

Система, которая учится на своих ошибках.

| Компонент | Что делает |
|-----------|-----------|
| MetaLearner | Запоминает каждый healing cycle в JSON на диске |
| PatternStats | Статистика по паттерну: success_rate, priority, consecutive_failures |
| DetectorStats | Статистика по детектору: accuracy, weight |
| AdaptiveStrategies | Выбор лучшего паттерна по confidence |

**Логика адаптации:**
- 3+ consecutive_failures → priority паттерна падает на 70%
- accuracy < 30% → weight детектора = 0.1 (почти не учитывается)
- confidence = weight × priority — система выбирает паттерн с max confidence

---

### Фаза 6: Документация и CI/CD (8 часов)

| Ресурс | Что содержит |
|--------|------------|
| `.github/workflows/ci.yml` | GitHub Actions: 3 Python-версии (3.12, 3.13, 3.14) |
| `scripts/smoke_test.py` | Быстрая проверка всех 6 слоёв за 1 запуск |
| `scripts/smoke.bat` | Запуск smoke test двойным кликом |
| `scripts/deploy.bat` | Проверка Python → установка pytest → smoke test |
| `docs/ADDING_DETECTOR.md` | Инструкция: как добавить новый детектор (5 шагов) |
| `docs/ADDING_PATTERN.md` | Инструкция: как добавить новый паттерн (5 шагов) |

---

## 3. Архитектура

### Слои

```
┌─────────────────────────────────────────────────────┐
│                 LAYER 4: Orchestrator ✅              │
│  SelfHealingLoop · monitor/suggest/auto · API · SSE  │
├─────────────────────────────────────────────────────┤
│                 LAYER 3: Verification ✅              │
│  TestRunner · LintChecker · MetricComparator · Rollback │
├─────────────────────────────────────────────────────┤
│                 LAYER 2: Patch Engine ✅              │
│  PythonPatcher (AST) · JSPatcher · 5 patterns        │
│  PatchResult (diff, apply, rollback)                 │
├─────────────────────────────────────────────────────┤
│                 LAYER 1: Diagnostics ✅               │
│  7 detectors · CLI runner · integration tests        │
├─────────────────────────────────────────────────────┤
│                 LAYER 0: X-RAY Kernel ✅              │
│  17 modules · Trace/Span · persistence · causal      │
│  consistency · retention · sanitizer · audit         │
└─────────────────────────────────────────────────────┘
```

### Data Flow (полный healing cycle)

```
Запрос в проекте → X-RAY пишет trace на диск
  → HEALER: diagnostics.runner
    → 7 детекторов анализируют трейсы
    → DiagnosticReport
  → [если mode=monitor] стоп, только отчёт
  → [если mode=auto/suggest]
    → Orchestrator выбирает паттерн по report.detector
    → PythonPatcher генерирует diff (AST)
    → PatchResult
  → [если mode=auto]
    → Verifier: TestRunner + LintChecker + MetricComparator
    → [тесты прошли]  → apply + MetaLearner: success
    → [тесты упали]   → rollback + MetaLearner: failure
```

---

## 4. Структура проекта

```
HEALER/                               # Ядро self-healing модуля
├── .github/workflows/ci.yml          # GitHub Actions
├── aethon/xray/                      # X-RAY kernel (17 файлов)
│   ├── trace.py / span.py            # Модели
│   ├── trace_store.py                # Хранилище (in-memory + disk)
│   ├── causal_validator.py           # 4 проверки причинности
│   ├── consistency_audit.py          # 5 проверок консистентности
│   ├── diagnostics.py                # 5 встроенных checks
│   ├── contracts.py                  # Event/Trace/Span/Metric схемы
│   ├── metrics.py                    # Counter, Gauge, Histogram
│   ├── http_propagation.py           # 5 X-RAY заголовков
│   ├── event.py                      # Event система
│   ├── data_sanitizer.py             # Очистка данных
│   ├── retention.py                  # Политика хранения
│   ├── manual_scenarios.py           # Сценарии A/B/C
│   ├── version.py                    # Версионирование
│   └── control_plane/                # DTO + нормализация
├── healer/                           # Self-Healing модуль
│   ├── diagnostics/                  # Layer 1 (7 детекторов)
│   │   ├── report.py                 # DiagnosticReport + severity/category
│   │   ├── span_analyzer.py          # Дубликаты, orphan, глубина
│   │   ├── slow_import.py            # Медленные импорты
│   │   ├── error_path.py             # Ошибки без fallback
│   │   ├── dead_code.py              # Неиспользуемые компоненты
│   │   ├── resource_leak.py          # Утечки ресурсов
│   │   ├── causal_violation.py       # Нарушения причинности
│   │   ├── latency_anomaly.py        # Аномалии задержек
│   │   ├── runner.py                 # CLI (--watch, --fail-on, --output)
│   │   └── integration_test.py       # 9 синтетических сценариев
│   ├── patcher/                      # Layer 2 (5 паттернов)
│   │   ├── base.py / result.py       # BasePatcher ABC + PatchResult
│   │   ├── python_patcher.py         # AST-трансформер Python
│   │   ├── js_patcher.py             # JS-патчер (regex)
│   │   └── patterns/                 # 5 AST-паттернов
│   ├── verifier/                     # Layer 3 (5 компонентов)
│   │   ├── result.py                 # VerificationResult + PhaseVerdict
│   │   ├── test_runner.py            # pytest/npm автоопределение
│   │   ├── lint_checker.py           # ruff/mypy/eslint
│   │   ├── metric_compare.py         # сравнение метрик до/after
│   │   └── rollback.py               # *.healer.bak → restore
│   ├── orchestrator.py               # Layer 4 (SelfHealingLoop + API)
│   ├── api.py                        # HTTP API (8 endpoints + SSE)
│   ├── meta/                         # Layer 5 (Meta-обучение)
│   │   ├── meta_learner.py           # MetaLearner + статистика
│   │   └── strategies.py             # AdaptiveStrategies
│   └── __init__.py
├── scripts/                          # Вспомогательные скрипты
│   ├── smoke_test.py                 # Smoke test (6 слоёв)
│   ├── smoke.bat                     # Smoke test двойным кликом
│   └── deploy.bat                    # Deploy скрипт
├── docs/                             # Документация разработчика
│   ├── ADDING_DETECTOR.md            # Как добавить детектор
│   └── ADDING_PATTERN.md             # Как добавить паттерн
├── tests/                            # 121 тест
│   ├── test_diagnostics.py           # 20 тестов
│   ├── test_patcher.py               # 33 теста
│   ├── test_verifier.py              # 21 тест
│   ├── test_orchestrator.py          # 17 тестов
│   └── test_meta.py                  # 30 тестов
├── data/trace_store/                 # X-RAY трейсы на диске
├── main.py                           # Демо
├── HEALER_STRATEGY.md                # Стратегия
├── HEALER_ROADMAP.md                 # Дорожная карта
└── README.md                         # Быстрый старт

healer-viewer/                        # Приложение-наблюдатель
├── viewer.py                         # HTTP сервер (stdlib)
├── start.bat                         # Запуск на :8085
├── static/index.html                 # SPA (чистый JS)
├── docs/                             # Документация viewer
│   ├── ARCHITECTURE.md               # Архитектура
│   ├── API.md                        # API endpoints
│   ├── DEVELOPER.md                  # Разработчику
│   └── HEALER_INTEGRATION.md         # Связь с HEALER
├── data/trace_store/                 # Свои X-RAY трейсы
└── README.md                         # Быстрый старт viewer
```

---

## 5. Ключевые решения

### 5.1 Прямой импорт HEALER (не subprocess) — viewer

Viewer не вызывает HEALER через shell. Вместо этого — прямой Python-import:
```python
from healer.diagnostics.runner import run_diagnostics
reports = run_diagnostics()
```
**Почему:** subprocess на Windows ломает Unicode. Прямой импорт гарантирует корректную кодировку русского текста.

### 5.2 AST-based patching, не regex

AST гарантирует синтаксически корректный output. `ast.parse(ast.unparse(tree))` — roundtrip валидация.

### 5.3 Zero external dependencies

Весь проект работает на чистом Python stdlib. Никаких pip install, кроме опционального pytest для тестов.

### 5.4 X-RAY как foundation

X-RAY-INTEGRATION-KIT — zero-dependency observability kernel. Causal integrity, disk persistence, consistency audit. Без него HEALER не может работать, но его можно подключить к любому проекту.

### 5.5 HEALER не знает о viewer

Viewer — отдельный проект. HEALER может диагностировать его как любой другой, через `--path`. Разработка HEALER и viewer независимы.

---

## 6. healer-viewer (приложение-наблюдатель)

Отдельное веб-приложение, которое:
- Показывает трейсы HEALER (списки, деревья span, длительности)
- Запускает HEALER диагностику через прямой Python-import
- Применяет HEALER патчи к своему коду (self-healing)
- Сам инструментирован X-RAY — HEALER может диагностировать и его

**Вкладки:** Обзор, Трейсы HEALER, Мои трейсы, Самодиагностика  
**Self-healing cycle в viewer:**
1. Viewer пишет трейсы → HEALER читает → находит проблемы
2. Viewer отображает отчёты → кнопка P (Patch) → PythonPatcher генерирует diff
3. diff применяется → бэкап `viewer.py.healer.bak`
4. При неудаче — rollback

---

## 7. Технологии

- **Python 3.12+** — единственное требование
- **0 внешних зависимостей** — весь код на stdlib
- **AST** — синтаксические деревья для патчинга Python
- **JSON on disk** — хранение трейсов и мета-данных
- **HTTP.server** — встроенный HTTP-сервер (stdlib)
- **SPA без фреймворков** — чистый HTML/CSS/JS

---

## 8. Статистика

| Модуль | Файлов | Строк кода |
|--------|--------|-----------|
| aethon/xray/ (ядро) | 17 | ~2500 |
| healer/ (все 5 слоёв) | ~30 | ~2600 |
| tests/ | 5 | ~1300 |
| scripts/ | 3 | ~200 |
| docs/ | 2 (+2 viewer) | ~300 |
| **HEALER итого** | **~57** | **~6900** |
| healer-viewer/ | 3 | ~800 |
| **ПРОЕКТ ИТОГО** | **~60** | **~7700** |

**Тесты:** 121, 0 failures, время выполнения ~6 секунд  
**Время разработки:** 86 часов / 7 фаз  
**Дата начала/конца:** 2026-05-?? → 2026-06-09

---

## 9. Быстрый старт

```bash
cd HEALER

# Демо
python main.py

# CLI диагностика
python -m healer.diagnostics.runner
python -m healer.diagnostics.runner --path ../project/data/trace_store --quiet --fail-on error

# Мониторинг
python -m healer.diagnostics.runner --watch --interval 30

# Тесты (121)
python -m pytest tests/

# Интеграционные тесты
python -m healer.diagnostics.integration_test

# Smoke test
python scripts/smoke_test.py

# Оркестратор API
python -m healer.api --port 8090

# Viewer
cd ../healer-viewer
start.bat    # http://127.0.0.1:8085
```

---

## 10. Дальнейшее развитие

**Короткий срок (новые детекторы):**
- NplusOneDetector — N+1 запросы в цикле
- BroadExceptDetector — `except: pass` без обработки
- RaceConditionDetector — гонки данных (async без lock)
- CircularImportDetector — циклические импорты

**Короткий срок (новые паттерны):**
- add_retry — оборачивает вызов в retry-цикл
- add_circuit_breaker — circuit breaker к HTTP вызовам

**Средний срок:**
- ML-based anomaly detection (scikit-learn, изолированный лес)
- Multi-project orchestration (управление N проектами)

**Долгий срок:**
- Поддержка JS/TS/Go через tree-sitter AST
- GitHub App / GitLab CI интеграция
- WebSocket dashboard (замена polling на push)
