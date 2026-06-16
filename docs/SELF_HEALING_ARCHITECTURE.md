# Self-Healing Architecture для PAD+ AI

**Дата:** 2026-06-10
**Основание:** Архитектурные принципы HEALER (self-healing module), адаптированные под существующую инфраструктуру PAD+ AI.

---

## 1. Философия

PAD+ AI уже имеет механизмы деградации (`PipelineState.DEGRADED`, `_mark_degraded()`, fallback-провайдеры). Проблема: **они не замкнуты**. Система падает, деградирует, но не учится на ошибках и не адаптируется автоматически.

Self-healing = **замкнутый цикл**:

```
Pipeline → мониторинг → диагностика → remediation → MetaLearner → адаптация → Pipeline
```

Без AST-патчинга. Только runtime-изменения: конфиги, провайдеры, стратегии, лимиты.

---

## 2. Текущее состояние PAD+ (что уже есть)

### ✅ Наблюдение (Observe)

| Компонент | Файл | Статус |
|---|---|---|
| TraceCollector (8 стадий pipeline) | `backend/core/xray/trace_collector.py` | ✅ Работает |
| XRayBroadcaster (WebSocket, 6 каналов) | `backend/core/xray/broadcaster.py` | ✅ Работает |
| ThoughtVisualizer (16 типов мыслей) | `backend/core/xray/thought_visualizer.py` | ✅ Работает |
| CognitiveState (PAD-метрики) | `backend/core/xray/cognitive_state.py` | ✅ Работает |
| X-Ray persistence | ❌ In-memory, теряется при рестарте | ❌ |

### ✅ Диагностика (Diagnose)

| Компонент | Файл | Статус |
|---|---|---|
| TraceValidator (инварианты, silent failures) | `backend/core/xray/validator.py` | ✅ Работает |
| InsightsEngine (аномалии, статистика) | `backend/core/xray/insights.py` | ✅ Работает |

### 🟡 Исправление (Patch/Remediation)

| Компонент | Файл | Статус |
|---|---|---|
| Pipeline state management | `backend/core/pipeline/executor.py:_mark_degraded()` | 🟡 Есть, не замкнут |
| DegradationInfo | `backend/core/pipeline/models.py` | 🟡 Есть, не влияет на стратегию |
| Fallback-провайдеры | `backend/core/pipeline/phases/generate.py` | 🟡 Есть, статический |

### 🟡 Обучение (Learn)

| Компонент | Файл | Статус |
|---|---|---|
| MetaLearner (статистика стратегий) | `backend/core/xray/meta_learner.py` | 🟡 **Не замкнут** — `should_adjust_strategy()` нигде не вызывается |
| ReflectionLoop (анализ результатов) | `backend/core/xray/reflection.py` | 🟡 **Не замкнут** — `should_adjust` ни на что не влияет |

---

## 3. Целевая архитектура

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PipelineExecutor                             │
│  safety → intent → rag → ... → generate → ... → response_guard     │
│         │                                          ▲                │
│         │ _mark_degraded()                         │                │
│         ▼                                          │                │
│  ┌──────────────────┐     ┌──────────────────┐     │                │
│  │  X-Ray Collector │────▶│ Healer Listener  │─────┘                │
│  │  (events)        │     │ (subscription)   │                      │
│  └──────────────────┘     └────────┬─────────┘                      │
│                                    │                                │
└────────────────────────────────────┼────────────────────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
              ▼                      ▼                      ▼
   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
   │  5 Detectors     │   │  Remediation     │   │  MetaLearner     │
   │  (BaseDetector)  │──▶│  Engine          │──▶│  (замкнутый)     │
   │                  │   │  (config-driven) │   │                  │
   │  • SlowPhase     │   │                  │   │  • record()      │
   │  • ErrorPath     │   │  • switch model  │   │  • adjust()      │
   │  • BrokenPhase   │   │  • clear cache   │   │  • recommend()   │
   │  • ProviderHealth│   │  • fallback      │   │                  │
   │  • StrategyDrift │   │  • downshift     │   └──────────────────┘
   └──────────────────┘   └──────────────────┘
```

### Ключевое решение: HealerListener — тонкая прослойка

**HealerListener** — это не отдельный оркестратор-монстр, а подписка на события `TraceCollector`. Он:

1. Слушает `session_completed` и `event_recorded`
2. Прогоняет завершённые сессии через детекторы
3. Если детектор нашёл проблему → выполняет remediation action
4. Записывает результат в MetaLearner

Не дублирует `PipelineExecutor._mark_degraded()`, а **дополняет** его: деградация от executor → input для MetaLearner.

---

## 4. Детекторы

### BaseDetector ABC

```python
class BaseDetector(ABC):
    @abstractmethod
    def detect(self, session: TraceSession) -> list[DiagnosticReport]: ...
```

### 4.1 SlowPhasesDetector (P0)

**Назначение:** Фазы pipeline, выполняющиеся дольше порога.

| Phase | Порог (ms) |
|---|---|
| generate | 8000 |
| rag | 2000 |
| truth_loop | 3000 |
| Любая другая | 5000 |

**Remediation:**
- Slow generate → переключить на более быструю модель (отразить в `provider_manager.py`)
- Slow RAG → включить cache-only mode (использовать `get_cache_manager()`)
- Slow truth_loop → пропустить verify (установить `skip_verification=True`)

**False positive prevention:** Только если медленно 3+ раза подряд из 5 последних запросов.

### 4.2 ErrorPathDetector (P0)

**Назначение:** Error-спаны без fallback.

**Семантика ошибок в pipeline (20 фаз):**

| Тип | Пример | Ожидаемая реакция |
|---|---|---|
| DegradationInfo | RAG недоступен | Штатная деградация — НЕ ошибка |
| Unhandled exception | Crash в `persona` | Ошибка — нужен алерт |
| Phase result success=False | Generate не дал ответ | Ошибка — нужен fallback |

**Remediation:**
- Unhandled exception → включить `safe_mode` (пропускать проблемную фазу)
- Generate fail → повторить с другой моделью
- 3+ ошибок подряд → снизить стратегию (reasoning → retrieval → simple)

**False positive prevention:** Игнорировать фазы с `DegradationInfo` — только реальные ошибки.

### 4.3 BrokenPhasesDetector (P1)

**Назначение:** Обязательные фазы pipeline не выполнились.

**Ожидаемый порядок:** `safety → intent → rag → knowledge_graph → episodic → semantic → emotion → persona → roots → generate → truth_loop → save_episode → emotion_update → persona_evolution → events_broadcast → health → reflection → dreams → metrics → response_guard`

**Remediation:**
- Пропущена generate → ошибка, перезапустить с кэшированным контекстом
- Пропущена safety → критическая ошибка, перезагрузить pipeline state

### 4.4 ProviderHealthDetector (P1)

**Назначение:** Провайдеры LLM, которые стабильно падают.

**Метрика:** `failures / total_calls` за последние 30 минут.

**Remediation:**
- failure_rate > 30% → понизить приоритет провайдера
- failure_rate > 60% → исключить из ротации на N минут
- Все провайдеры падают → вернуться к базовому (OpenRouter)

**Источник данных:** `provider_failures` из `backend/core/metrics.py` или `runtime/llm_service.py`.

### 4.5 StrategyDriftDetector (P2)

**Назначение:** Стратегия деградирует по метрикам.

**Метрика:** Сравнить execution_time и confidence за последние 10 запросов vs предыдущие 10.

**Remediation:**
- Стратегия стабильно медленнее на 30% → рекомендовать смену через MetaLearner
- Стратегия стабильно ниже confidence на 20% → сменить на `simple`

---

## 5. Remediation Engine

### Принцип: config-driven, не AST

```python
# backend/healing/remediation.py

REMEDIATION_TABLE = [
    {
        "detector": "SlowPhasesDetector",
        "condition": "generate > 8000ms × 3",
        "action": "switch_model",
        "params": {"prefer": "groq/llama-3.1-8b", "reason": "generate too slow"},
        "rollback": "restore_model",
    },
    {
        "detector": "ErrorPathDetector",
        "condition": "unhandled exception in any phase",
        "action": "enable_safe_mode",
        "params": {"skip_phases": [], "timeout_multiplier": 2.0},
        "rollback": "disable_safe_mode",
    },
    {
        "detector": "ProviderHealthDetector",
        "condition": "failure_rate > 0.3",
        "action": "deprioritize_provider",
        "params": {"cooldown_minutes": 15},
        "rollback": "restore_provider",
    },
]
```

### Rollback

Каждое remediation action сохраняет предыдущее состояние (backup конфига). Если после изменения метрики ухудшились → rollback.

---

## 6. Замыкание MetaLearner

### Текущее состояние (разрыв)

```python
# executor.py:215 — стратегия выбирается статически
result.strategy = self._determine_strategy(user_message)
# MetaLearner.should_adjust_strategy() — не вызывается

# meta_learner.py — собирает статистику
# reflection.py — анализирует
# Ничто из этого не влияет на pipeline
```

### Целевое состояние

```python
# executor.py — после execute()
from core.xray import get_meta_learner
meta = get_meta_learner()
meta.record_outcome(result.strategy, result.to_dict())

# Если стратегия стабильно плоха
recommended = meta.should_adjust_strategy(result.strategy)
if recommended:
    result.metadata["strategy_recommended"] = recommended
    # В следующем запросе executor учтёт рекомендацию
```

### MetaLearner + ReflectionLoop + Healer (единый цикл)

```python
# backend/healing/orchestrator.py (тонкая прослойка)

def on_pipeline_complete(self, result: PipelineResult):
    # 1. Записать в MetaLearner
    self.meta.record_outcome(result.strategy, result.to_dict())

    # 2. Прогнать детекторы
    reports = self.detectors.run(result)

    # 3. Если есть проблемы — remediation
    for report in reports:
        action = self.remediation_table.match(report)
        if action:
            action.execute()
            self.meta.record_healing(report.detector, action.name, success=True)

    # 4. Проверить, нужна ли смена стратегии
    adjustment = self.meta.should_adjust_strategy(result.strategy)
    if adjustment:
        self._suggest_strategy_change(adjustment)
```

---

## 7. Этапы реализации

### Этап 0: Persistence (1.5ч)

**Цель:** X-Ray перестаёт терять данные при рестарте.

```sql
-- supabase/migrations/xray_traces.sql
CREATE TABLE xray_traces (
    trace_id     UUID PRIMARY KEY,
    user_message TEXT,
    response     TEXT,
    spans_json   JSONB,
    total_ms     FLOAT,
    success      BOOLEAN,
    strategy     TEXT,
    model        TEXT,
    provider     TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- RLS: пользователь видит только свои трейсы
ALTER TABLE xray_traces ENABLE ROW LEVEL SECURITY;
```

**Изменения в `trace_collector.py`:**
- `complete_session()` → запись в `xray_traces`
- `__init__` → `load_history()` из Supabase
- `get_recent_sessions()` → читает из Supabase + in-memory fallback

### Этап 1: Diagnostics (3-4ч)

Новый модуль `backend/healing/`:

```
backend/healing/
├── __init__.py
├── detectors/
│   ├── base.py                # BaseDetector ABC
│   ├── slow_phases.py         # SlowPhasesDetector
│   ├── error_path.py          # ErrorPathDetector
│   ├── broken_phases.py       # BrokenPhasesDetector
│   ├── provider_health.py     # ProviderHealthDetector
│   └── strategy_drift.py      # StrategyDriftDetector
├── runner.py                  # run_diagnostics(event_callback=)
├── report.py                  # DiagnosticReport (совместим с X-Ray)
├── remediation.py             # RemediationEngine (config-driven)
└── listener.py                # HealerListener (подписка на TraceCollector)
```

**Интеграция:**
- `HealerListener.subscribe(get_trace_collector())` — подписка на события
- Детекторы получают завершённые сессии через `collector.subscribe()`
- Результаты диагностики → X-Ray Broadcaster → frontend

### Этап 2: Remediation + Замыкание (4ч)

- `remediation.py` — config-driven таблица
- Rollback — backup конфига перед каждым изменением
- Замкнуть `MetaLearner.should_adjust_strategy()` на `_determine_strategy()`
- Замкнуть `ReflectionLoop.should_adjust` на `HealerListener`

### Этап 3: Тесты (2ч)

- 4 новых теста: детекторы по одному, интеграционный (полный цикл)
- smoke test: `run_healing_cycle()` — проверка что listener не ломает pipeline

---

## 8. Границы безопасности

| Что разрешено auto | Что только suggest |
|---|---|
| Смена модели (generate → быстрее/дешевле) | Отключение фазы pipeline |
| Включение кэша (RAG → cache-only) | Изменение safety-политик |
| Очистка кэша (memory > threshold) | Рестарт сервиса |
| Понижение стратегии (reasoning → simple) | Изменение provider API keys |
| Fallback провайдера | AST-изменения кода |

---

## 9. Критерии готовности

- [ ] **Persistence:** X-Ray теряет 0 данных при рестарте (проверяется тестом)
- [ ] **SlowPhasesDetector:** алерт при generate > 8s 3 раза подряд
- [ ] **ErrorPathDetector:** 0 false positives на штатной деградации pipeline
- [ ] **MetaLearner:** `should_adjust_strategy()` реально влияет на выбор стратегии
- [ ] **HealerListener:** подписка не замедляет pipeline (benchmark: < 1ms overhead)
- [ ] **Rollback:** каждое remediation action откатывается при ухудшении метрик
- [ ] **Тесты:** 4 новых теста проходят, 6 существующих X-Ray тестов зелёные
