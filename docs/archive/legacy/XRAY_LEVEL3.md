# 🔬 X-Ray Level 3 — Cognitive Infrastructure

## Обзор

X-Ray эволюционировал из простого observability layer в **Cognitive Infrastructure** — систему, которая не только наблюдает, но и понимает внутреннюю динамику AI, обнаруживает аномалии и предоставляет feedback для self-optimization.

## Архитектура Level 3

```
┌─────────────────────────────────────────────────────────────────┐
│                    X-Ray Cognitive Infrastructure                │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Trace Context  │  │ Cognitive State │  │  Event Buffer   │  │
│  │  (hierarchical) │  │  (metrics)      │  │  (backpressure) │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Insights      │  │    Thought      │  │   Broadcaster   │  │
│  │   (analytics)   │  │  Visualizer     │  │   (real-time)   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              History Recorder (sessions, replay)            ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Ключевые компоненты

### 1. Trace Context (Иерархическая трассировка)

**Файл:** `backend/core/xray/trace_context.py`

```python
from core.xray import get_trace_context_manager, SpanStatus

# Начало трассировки
ctx = get_trace_context_manager()
trace = ctx.start_trace("Что такое квантовая физика?")

# Создаём спан для стадии
span = ctx.start_span("safety_check", attributes={"passed": True})
# ... выполнение ...
ctx.end_span(span, SpanStatus.OK)

# Завершение трассировки
ctx.end_trace(trace.trace_id)

# Получаем дерево спанов
tree = trace.get_span_tree()
critical_path = trace.get_critical_path()
```

**Особенности:**
- `trace_id` — глобальный ID сессии
- `span_id` — локальный ID операции
- `parent_span_id` — связь с родительской операцией
- `get_span_tree()` — построение дерева выполнения
- `get_critical_path()` — нахождение самого длинного пути

### 2. Cognitive State (Когнитивное состояние)

**Файл:** `backend/core/xray/cognitive_state.py`

```python
from core.xray import get_cognitive_state_manager

csm = get_cognitive_state_manager()
state = csm.create_state(trace_id, user_message)

# Обновление метрик
state.update_metrics(
    uncertainty=0.3,
    cognitive_load=0.5,
    confidence=0.8,
    complexity=0.6
)

# Запись решения
state.record_decision(
    name="strategy_selection",
    decision_type="strategy",
    options=["simple", "deep", "creative"],
    selected="deep",
    confidence=0.9,
    reasoning="Complex query requires deep analysis"
)

# Веса источников
state.set_source_weight("rag", weight=0.45, confidence=0.8)
state.set_source_weight("facts", weight=0.25, confidence=0.7)
state.set_source_weight("llm", weight=0.30, confidence=0.6)

# Итоговая уверенность
final_confidence = state.calculate_final_confidence()

# Проверка необходимости верификации
if state.should_verify():
    # Включаем верификацию
    pass

# Когнитивная нагрузка
load_score = state.get_cognitive_load_score()
if state.should_simplify():
    # Упрощаем стратегию
    pass
```

**Метрики:**
- `uncertainty` — неопределённость (0-1)
- `cognitive_load` — когнитивная нагрузка
- `confidence` — уверенность в ответе
- `complexity` — сложность запроса

**Формулы:**
```
final_confidence = Σ(source_weight × source_confidence × contribution)
cognitive_load_score = complexity × uncertainty × (1 + steps_count × 0.1)
```

### 3. Event Buffer (Буфер с backpressure)

**Файл:** `backend/core/xray/event_buffer.py`

```python
from core.xray import get_event_buffer, EventPriority

buffer = get_event_buffer()
await buffer.start()

# Публикация с приоритетом
await buffer.publish(
    event_type="trace_event",
    data={"stage": "safety", "passed": True},
    priority=EventPriority.HIGH,  # CRITICAL > HIGH > NORMAL > LOW
    channel="trace"
)

# Подписка на события
async def handle_events(events):
    for event in events:
        await websocket.send_json(event)

buffer.subscribe(handle_events)
```

**Особенности:**
- Priority queue (критичные события не теряются)
- Backpressure при 80% заполнении
- Drop low-priority events при перегрузке
- Batching для эффективной отправки

### 4. Insights Engine (Аналитика и аномалии)

**Файл:** `backend/core/xray/insights.py`

```python
from core.xray import get_insights_engine

insights = get_insights_engine()

# Запись трассировки для анализа
insights.record_trace(trace_data)

# Получение аномалий
anomalies = insights.get_anomalies(
    limit=10,
    severity="high",
    type_filter="slow_stage"
)

# Статистика по стадиям
stage_stats = insights.get_stage_stats()

# Тренды
trends = insights.get_trends()
# {
#   "confidence": {"current": 0.75, "trend": "decreasing", "change_percent": -5.2},
#   "cognitive_load": {"current": 0.45, "trend": "stable"},
#   "latency": {"current": 1250, "trend": "increasing", "change_percent": 12.3}
# }

# Рекомендации
recommendations = insights.get_recommendations()
```

**Типы аномалий:**
- `slow_stage` — стадия выполняется слишком долго
- `low_confidence` — уверенность ниже порога
- `high_load` — когнитивная нагрузка выше порога
- `failure` — ошибка на стадии
- `timeout` — общее время превысило таймаут

## API Endpoints (обновлено)

### REST API

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/v1/xray/` | GET | Информация о системе |
| `/api/v1/xray/traces` | GET | Список трассировок |
| `/api/v1/xray/traces/{id}` | GET | Детали трассировки с деревом спанов |
| `/api/v1/xray/traces/{id}/tree` | GET | Дерево спанов |
| `/api/v1/xray/traces/{id}/critical-path` | GET | Критический путь |
| `/api/v1/xray/cognitive/{trace_id}` | GET | Когнитивное состояние |
| `/api/v1/xray/anomalies` | GET | Аномалии |
| `/api/v1/xray/trends` | GET | Тренды |
| `/api/v1/xray/recommendations` | GET | Рекомендации |
| `/api/v1/xray/stats` | GET | Статистика |

### WebSocket

```
ws://localhost:8080/api/v1/xray/ws
```

Каналы:
- `trace` — события трассировки
- `thought` — поток мыслей
- `cognitive` — когнитивное состояние
- `anomaly` — аномалии
- `pipeline` — статус пайплайна
- `all` — все события

## Интеграция с Pipeline

```python
from core.xray import (
    get_trace_context_manager,
    get_cognitive_state_manager,
    get_event_buffer,
    get_insights_engine,
    EventPriority
)

async def execute_with_xray(user_message: str):
    # Инициализация
    ctx = get_trace_context_manager()
    csm = get_cognitive_state_manager()
    buffer = get_event_buffer()
    insights = get_insights_engine()
    
    # Начало трассировки
    trace = ctx.start_trace(user_message)
    state = csm.create_state(trace.trace_id, user_message)
    
    try:
        # 1. Safety
        span = ctx.start_span("safety")
        safety_result = await check_safety(user_message)
        ctx.end_span(span, SpanStatus.OK if safety_result.passed else SpanStatus.ERROR)
        
        await buffer.publish(
            "trace_event",
            {"stage": "safety", "passed": safety_result.passed},
            priority=EventPriority.HIGH
        )
        
        # 2. Intent
        span = ctx.start_span("intent")
        intent = await classify_intent(user_message)
        ctx.end_span(span)
        
        state.record_decision(
            "intent_classification",
            "classification",
            options=["question", "command", "chat"],
            selected=intent.label,
            confidence=intent.confidence,
            reasoning=intent.reasoning
        )
        
        # 3. Retrieve
        span = ctx.start_span("retrieve")
        context = await retrieve_context(user_message)
        ctx.end_span(span)
        
        state.set_source_weight("rag", 0.45, context.confidence)
        state.set_source_weight("facts", 0.25, facts.confidence)
        
        # ... остальные стадии ...
        
        # Завершение
        state.update_metrics(confidence=final_confidence)
        csm.complete_state(trace.trace_id)
        ctx.end_trace(trace.trace_id, SpanStatus.OK)
        
        # Анализ
        insights.record_trace(trace.to_dict())
        
        # Проверка аномалий
        anomalies = insights.get_anomalies(limit=5)
        if anomalies:
            logger.warning(f"Detected {len(anomalies)} anomalies")
        
        return result
        
    except Exception as e:
        ctx.end_trace(trace.trace_id, SpanStatus.ERROR)
        raise
```

## Self-Optimization Loop

X-Ray Level 3 позволяет системе **самостоятельно оптимизироваться**:

```python
# В pipeline
if state.should_verify():
    # Включаем верификацию при низкой уверенности
    result = await verify_response(result)

if state.should_simplify():
    # Упрощаем стратегию при высокой нагрузке
    strategy = "simple"
else:
    strategy = "deep"

# На основе трендов
trends = insights.get_trends()
if trends["latency"]["trend"] == "increasing":
    # Увеличиваем кэширование
    cache_manager.increase_ttl()

if trends["confidence"]["trend"] == "decreasing":
    # Проверяем качество источников
    await validate_sources()
```

## Производительность

| Метрика | Значение |
|---------|----------|
| Overhead на запрос | < 5ms |
| Макс. событий/сек | 1000+ |
| Потеря критичных событий | 0% |
| Backpressure threshold | 80% |
| Max queue size | 1000 |

## Будущие улучшения

1. **Trace Replay** — воспроизведение сессий с контролем скорости
2. **Anomaly Alerting** — уведомления об аномалиях
3. **Auto-tuning** — автоматическая настройка порогов
4. **Distributed Tracing** — трассировка across microservices
5. **ML-based Anomaly Detection** — обнаружение аномалий через ML