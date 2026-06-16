# HEALER — Стратегия Self-Healing модуля

**Статус:** Фаза 0 ✅ · Фаза 1 ✅ · Фаза 2 ✅ · 53/86 часов (62%)

---

## Философия

**Универсальный self-healing модуль**, способный находить и исправлять проблемы
в любом проекте, не требуя человеческого участия.

Основа — X-RAY-INTEGRATION-KIT: zero-dependency observability kernel,
transport-agnostic, provider-agnostic.

Self-Healing = **Layer 0 (X-RAY kernel)** + **Layer 1 (Diagnostics)** +
**Layer 2 (Patcher)** + **Layer 3 (Verification)** + **Layer 4 (Orchestrator)**.

---

## Текущее состояние (июнь 2026)

### Layer 0: X-RAY Kernel ✅

17 модулей ядра. Полный lifecycle Trace/Span с causal integrity,
disk persistence, consistency audit, retention, data sanitizer.

### Layer 1: Diagnostics ✅

7 детекторов + CLI runner + интеграционные тесты.

| Детектор | Ищет | Тип |
|----------|------|-----|
| SpanAnalyzer | Дубликаты span_id, missing parent, un-ended spans, глубина > 10 | integrity |
| SlowImportDetector | Импорты/init/setup > 100ms | performance |
| ErrorPathDetector | Error-спаны без sibling fallback | correctness |
| DeadCodeDetector | Зарегистрированные kinds без единого вызова | maintainability |
| ResourceLeakDetector | Незавершённые spans > 30s, orphan spans | resource |
| CausalViolationDetector | Обёртка над causal_validator (child > parent, clock regression) | integrity |
| LatencyAnomalyDetector | Выбросы длительности > 3 sigma от среднего по kind | performance |

**CLI runner** (`-m healer.diagnostics.runner`):
- `--path` — путь к trace_store любого проекта
- `--watch` — непрерывный мониторинг с интервалом
- `--quiet` — JSON в stdout (для CI/CD)
- `--fail-on` — exit code 1 при ошибках
- `--min-severity` — фильтр по severity
- `--output` — JSON на диск

### Layer 2: Patch Engine ✅

AST-трансформер для Python + JS-патчер.

| Паттерн | Язык | Что делает | Связанный детектор |
|---------|------|-----------|-------------------|
| lazy_import | Python | Переносит import из module-level в тело функции | SlowImportDetector |
| try_finally | Python | Оборачивает тело функции в try/finally с cleanup | ErrorPathDetector |
| add_timeout | Python | Добавляет timeout=30 к HTTP-вызовам | LatencyAnomalyDetector |
| remove_dead | Python | Удаляет неиспользуемые импорты/пустые функции | DeadCodeDetector |
| close_resource | Python | open() → with-блок | ResourceLeakDetector |
| add_timeout (JS) | JS | AbortSignal.timeout к fetch() | LatencyAnomalyDetector |
| try_finally (JS) | JS | try/finally с cleanup | ErrorPathDetector |

У каждого паттерна: `PatchResult.diff`, `.apply(backup=True)`, `.rollback()`.

---

## Целевая архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                     SELF-HEALING SYSTEM                           │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              LAYER 4: Orchestrator (—)                       ││
│  │  Принимает сигналы → выбирает диагноста → запускает патчер   ││
│  │  → верифицирует → откатывает при неудаче → логирует         ││
│  │  Режимы: monitor / suggest / auto                           ││
│  └─────────────────────────────────────────────────────────────┘│
│                                │                                 │
│  ┌────────────────────────────┼─────────────────────────────┐   │
│  │              LAYER 3: Verification (—)                    │   │
│  │  TestRunner · LintChecker · MetricComparator · Rollback   │   │
│  └────────────────────────────┬─────────────────────────────┘   │
│                               │                                  │
│  ┌────────────────────────────┼─────────────────────────────┐   │
│  │              LAYER 2: Patch Engine ✅                     │   │
│  │  PythonPatcher (AST) · JSPatcher                          │   │
│  │  5 patterns: lazy_import, try_finally, add_timeout,       │   │
│  │  remove_dead, close_resource                              │   │
│  └────────────────────────────┬─────────────────────────────┘   │
│                               │                                  │
│  ┌────────────────────────────┼─────────────────────────────┐   │
│  │              LAYER 1: Diagnostics ✅                      │   │
│  │  7 detectors · CLI runner · integration tests             │   │
│  └────────────────────────────┬─────────────────────────────┘   │
│                               │                                  │
│  ┌────────────────────────────┼─────────────────────────────┐   │
│  │              LAYER 0: X-RAY Kernel ✅                     │   │
│  │  17 modules · Trace/Span · persistence · causal validation│   │
│  │  consistency audit · retention · sanitizer                │   │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: полный healing cycle (цель)

```
Pipeline завершает запрос
  → TraceStore сохраняет trace на диск
  → CausalValidator проверяет целостность
  → [если violations > 0]
  → Orchestrator получает сигнал
  → выбирает DiagnosticRule по типу violations
  → DiagnosticRule анализирует trace
  → DiagnosticReport
  → [если severity >= warning]
  → Orchestrator выбирает PatchPattern
  → Patcher генерирует diff
  → Verifier запускает тесты
    ├── [тесты прошли] → apply patch → запись в MetaLearner: success
    └── [тесты упали] → rollback → запись в MetaLearner: failure → альтернативный патч
  → X-RAY trace закрывается с метаданными healing
```

---

## Проекты

### HEALER (`HEALER/`) — разработка self-healing модуля

Ядро + детекторы + патчи. Никаких внешних зависимостей, только Python stdlib.

```bash
cd HEALER
python main.py                                          # демо
python -m healer.diagnostics.runner                      # CLI диагностика
python -m healer.diagnostics.runner --path ../PROJECT/data/trace_store  # диагностика любого проекта
python -m pytest tests/                                 # 53 теста
python -m healer.diagnostics.integration_test           # интеграционные тесты
```

### HEALER Viewer (`healer-viewer/`) — приложение-наблюдатель

Автономный веб-дашборд. Инструментирован X-RAY — пишет свои трейсы.
HEALER может диагностировать viewer через `--path healer-viewer/data/trace_store`.

```bash
cd healer-viewer
start.bat            # открывает браузер на :8085
```

---

## Ключевые решения

### 1. X-RAY-INTEGRATION-KIT как foundation
Zero dependency, causal integrity, disk persistence, consistency audit.

### 2. AST-based patching, не regex
AST гарантирует синтаксически корректный output, атомарный apply/rollback.

### 3. Три режима работы
- `monitor` — только наблюдение (безопасно для production)
- `suggest` — человек в цикле (review перед apply)
- `auto` — полная автоматизация (verified паттерны)

### 4. MetaLearner как feedback loop
Статистика успешности паттернов → адаптивные пороги → веса диагностов.

### 5. HEALER не знает о viewer
Viewer — отдельный проект. HEALER может диагностировать его как любой другой,
через `--path`. Разработка HEALER независима.

---

## Оценка времени

| Фаза | Статус | Часы |
|------|--------|------|
| 0. X-RAY Kernel | ✅ | 12 |
| 1. Diagnostics | ✅ | 14 |
| 2. Patch Engine | ✅ | 20 |
| 3. Verification | ⏳ | 8 |
| 4. Orchestrator | 📋 | 14 |
| 5. Meta-обучение | 📋 | 10 |
| 6. Документация | 📋 | 8 |
| **Всего** | **62%** | **86** |

---

## Пути расширения

### Короткий срок (после Фазы 6)
- Новые DiagnosticRule: логические ошибки, гонки данных
- Новые PatchPattern: circuit breaker, retry
- Поддержка Go/Rust (tree-sitter AST)

### Средний срок (3-6 месяцев)
- Multi-project orchestration
- ML-based anomaly detection
- Распределённая трассировка healing-циклов

### Долгий срок (6-12 месяцев)
- Полностью автономная система
- Предсказание проблем до их возникновения
- Кросспроектный анализ паттернов отказов
