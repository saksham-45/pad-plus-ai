# X-Ray — Система полной наблюдаемости AI

## Что это

X-Ray — **полная трассировка и визуализация каждого шага мышления** AI в реальном времени.

Не просто логи и метрики, а **интерактивная панель**, показывающая:
- Что AI думает на каждом этапе (мысли AI в реальном времени)
- Какие данные использует (RAG, Facts, Knowledge Graph, Memory)
- Сколько времени тратит (каждая фаза пайплайна)
- Какие ошибки возникают (с трейсами и контекстом)
- Состояние системы (провайдеры, кэш, эмоции)
- Самодиагностику и саморефлексию HEALER

## Архитектура

```
frontend/src/
├── components/
│   ├── xray/
│   │   ├── XRayPanel.jsx            # Основная панель дашборда X-Ray
│   │   ├── XRayTraceView.jsx        # Детальный просмотр трейса
│   │   ├── XRayTraceTimeline.jsx    # Таймлайн трейса
│   │   ├── XRayTraceList.jsx        # Список последних трейсов
│   │   ├── XRayThoughtStream.jsx    # Поток мыслей AI
│   │   ├── HealerTracePanel.jsx     # панель трейсов HEALER
│   │   ├── TraceTreeView.jsx        # Древовидный просмотр span
│   │   └── CognitiveStatePanel.jsx  # Когнитивные метрики
│   └── healer/
│       ├── HealerResults.jsx        # Результаты диагностики HEALER
│       ├── HealerReflection.jsx     # Рефлексия HEALER
│       └── HealerHistory.jsx        # История циклов HEALER
├── pages/
│   ├── XRayPage.jsx                 # Страница X-Ray дашборда
│   ├── HealerPage.jsx               # Страница HEALER
│   └── HealerReflectionPanel.jsx    # Панель рефлексии с WS
└── hooks/
    └── useWebSocket.js              # WebSocket хук


backend/
├── core/xray/
│   ├── __init__.py                  # Экспорт компонентов
│   ├── tracer.py                    # Span + Trace + XRayTracer (синглтон)
│   ├── trace_collector.py           # XRayTraceCollector — сборщик трейсов
│   ├── trace_context.py             # Распределённая трассировка (OpenTelemetry)
│   ├── broadcaster.py               # XRayBroadcaster — WS трансляция
│   ├── cognitive_state.py           # CognitiveState — когнитивные метрики
│   ├── thoughtstream.py             # Поток мыслей AI по фазам пайплайна
│   ├── reflection.py                # ReflectionEngine — самоанализ
│   ├── meta_learner.py              # MetaLearner — обучение на стратегиях
│   ├── insights.py                  # InsightsEngine — аналитика
│   └── models.py                    # Модели данных
├── core/trace_collector.py          # TraceCollector (core, thread-safe)
├── api/
│   ├── xray_routes.py               # API endpoints X-Ray
│   └── healer_routes.py             # API endpoints HEALER + bridge
├── integration/
│   └── healer_bridge.py             # Мост между PAD+ и HEALER
└── healing/
    ├── listener.py                  # HealerListener — подписка на события
    ├── runner.py                    # run_diagnostics — запуск детекторов
    ├── report.py                    # DiagnosticReport — формат отчёта
    ├── remediation.py               # RemediationEngine — исправления
    ├── reflection_loop.py           # ReflectionLoop — мета-анализ
    ├── changes_store.py             # HealingChangesStore — откат изменений
    └── detectors/
        ├── base.py                  # BaseDetector
        ├── slow_phases.py           # Детектор медленных фаз
        ├── error_path.py            # Детектор ошибочных путей
        ├── broken_phases.py         # Детектор сломанных фаз
        ├── provider_health.py       # Детектор здоровья провайдеров
        └── strategy_drift.py        # Детектор дрейфа стратегий

HEALER/
├── healer/
│   └── orchestrator.py             # Полный цикл: diagnose → patch → verify → apply/rollback
└── aethon/xray/
    ├── trace_store.py              # TraceStore для HEALER
    └── trace.py                    # Модели трейсов HEALER
```

## Как работает

### 1. Полный цикл запроса

Каждый запрос проходит через **9 фаз пайплайна**, каждая фаза создаёт span:

```
User Message
    │
    ▼
┌─────────────┐     X-Ray: событие phase_start + мысли AI
│   Safety    │ ──→ TraceCollector: event_recorded
└─────┬───────┘     WebSocket: broadcast trace/thought
      ▼
┌─────────────┐
│   Intent    │ ──→ CognitiveState: confidence, uncertainty
└─────┬───────┘
      ▼
┌─────────────┐
│  Retrieve   │ ──→ RAG + Facts + Knowledge Graph
└─────┬───────┘
      ▼
┌─────────────┐
│   Persona   │ ──→ Эмоции + личность
└─────┬───────┘
      ▼
┌─────────────┐
│  Generate   │ ──→ LLM провайдер (с fallback)
└─────┬───────┘
      ▼
┌─────────────┐
│   Verify    │ ──→ Truth Loop
└─────┬───────┘
      ▼
┌─────────────┐
│  Remember   │ ──→ Сохранение в память
└─────┬───────┘
      ▼
┌─────────────┐
│    Emit     │ ──→ Формирование ответа
└─────┬───────┘
      ▼
┌─────────────┐
│  Complete   │ ──→ Финал + broadcast session_completed
└─────────────┘
        │
        ▼ (если mode=suggest или auto)
┌─────────────────────┐
│  HEALER Diagnostics  │ ──→ 5 детекторов → DiagnosticReport[]
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  ReflectionLoop     │ ──→ learnings + changes + stats
└─────────────────────┘
        │
        ▼ WebSocket
┌─────────────────────┐
│  XRayBroadcaster    │ ──→ trace | thought | emotion | healer | pipeline
└─────────────────────┘
```

### 2. Компоненты X-Ray

#### XRayTracer (`backend/core/xray/tracer.py`)
- **Span**: dataclass имени, времени, статуса, деталей этапа
- **Trace**: dataclass id, сообщения, спанов, ответа, модели
- **XRayTracer**: синглтон для создания/завершения трейсов

#### XRayTraceCollector (`backend/core/xray/trace_collector.py`)
- **TraceStage**: enum фаз SAFETY → COMPLETE
- **TraceEvent**: событие с id, stage, duration, status, error
- **TraceSession**: сессия запроса с коллекцией событий
- Методы: `start_session()`, `record_event()`, `complete_session()`, `get_recent_sessions()`, `get_active_sessions()`, `get_stats()`, `export_session()`

#### TraceContext (`backend/core/xray/trace_context.py`)
- Распределённая трассировка в стиле OpenTelemetry
- **SpanStatus**: UNSET / OK / ERROR
- **SpanContext**: trace_id, span_id, parent_span_id, name, kind, duration_ms
- **TraceContext**: менеджер с `start_span()`, `end_span()`, `get_current_span()`

#### XRayBroadcaster (`backend/core/xray/broadcaster.py`)
- Каналы: `trace`, `thought`, `pipeline`, `emotion`, `decision`, `system`, `healer`, `all`
- **BroadcastMessage**: type + data + timestamp + to_json()
- Методы: `connect()`, `disconnect()`, `subscribe()`, `unsubscribe()`, `broadcast()`, `start()`, `stop()`, `get_stats()`

#### CognitiveState (`backend/core/xray/cognitive_state.py`)
- **CognitiveMetrics**: uncertainty, cognitive_load, confidence, complexity
- **DecisionNode**: tree of decisions с confidence и reasoning
- **CognitiveStateManager**: синглтон, обновление и получение когнитивного состояния

#### ThoughtStream (`backend/core/xray/thoughtstream.py`)
- **Thought**: text, phase, status, metadata, confidence
- **ThoughtStreamManager**: запись и получение мыслей AI по фазам
- **Real-time трансляция** через broadcaster

## API Endpoints

### X-Ray

| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/xray/recent` | Последние 50 трейсов |
| `GET /api/v1/xray/active` | Активные трейсы |
| `GET /api/v1/xray/{trace_id}` | Детали конкретного трейса |
| `GET /api/v1/xray/stats` | Статистика X-Ray |
| `GET /api/v1/xray/latest` | Последний трейс (для polling) |
| `WS /ws/xray` | Real-time: trace, thought, emotion, decision, pipeline, system, healer |

### HEALER

| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/healer/status` | Статус HealerListener |
| `GET /api/v1/healer/mode` | Режим: monitor/suggest/auto |
| `POST /api/v1/healer/mode?mode=` | Установить режим |
| `POST /api/v1/healer/diagnose` | Запустить диагностику |
| `GET /api/v1/healer/reports` | Отчёты диагностики |
| `GET /api/v1/healer/bridge/status` | Статус HealerBridge |
| `GET /api/v1/healer/bridge/mode` | Режим Bridge |
| `POST /api/v1/healer/bridge/mode?mode=` | Установить режим Bridge |
| `POST /api/v1/healer/bridge/diagnose` | Диагностика через Bridge |
| `POST /api/v1/healer/bridge/cycle` | Полный healing cycle |
| `POST /api/v1/healer/bridge/cycle/stop` | Остановить цикл |
| `GET /api/v1/healer/bridge/orchestrator` | Статус HEALER Orchestrator |
| `GET /api/v1/healer/bridge/reflection/latest` | Последняя рефлексия |
| `GET /api/v1/healer/bridge/changes?status=` | Список изменений |
| `POST /api/v1/healer/bridge/rollback/{patch_id}` | Откатить патч |
| `GET /api/v1/healer/bridge/auto-cycle` | Настройки автоцикла |
| `POST /api/v1/healer/bridge/auto-cycle` | Запуск автоцикла |
| `POST /api/v1/healer/bridge/auto-cycle/stop` | Остановка автоцикла |

## WebSocket события

### Канал: trace
```json
{"type": "trace_update", "data": {"trace_id": "...", "phase": "...", "duration_ms": 150, "status": "success"}}
{"type": "trace_completed", "data": {"trace_id": "...", "total_duration_ms": 3200, "model": "groq/llama-3.1-70b"}}
```

### Канал: thought
```json
{"type": "thought", "data": {"text": "Анализирую намерение пользователя...", "phase": "intent", "confidence": 0.92}}
```

### Канал: emotion
```json
{"type": "emotion_update", "data": {"pleasure": 0.3, "arousal": 0.7, "dominance": 0.5, "curiosity": 0.85}}
```

### Канал: pipeline
```json
{"type": "phase_start", "data": {"phase": "retrieve", "trace_id": "..."}}
{"type": "phase_complete", "data": {"phase": "retrieve", "duration_ms": 250, "status": "success"}}
```

### Канал: healer
```json
{"type": "healer_bridge_cycle_complete", "data": {"status": "done", "reports": [...], "result": {...}}}
{"type": "healer_bridge_reflection", "data": {"learnings": [...], "changes": [...], "stats": {...}}}
{"type": "healer_bridge_diag_event", "data": {"event": "detector_found", "detector": "SlowPhasesDetector", "report": {...}}}
```

### Канал: system
```json
{"type": "system_state", "data": {"providers": {...}, "cache": {...}, "memory": {...}}}
```

## Frontend компоненты

### X-Ray Dashboard
- **XRayPanel** — Основной дашборд: список трейсов + таймлайн + поток мыслей
- **XRayTraceView** — Детальный просмотр одного трейса
- **XRayTraceTimeline** — Визуальный таймлайн фаз
- **XRayTraceList** — Таблица последних трейсов
- **XRayThoughtStream** — Поток мыслей AI в реальном времени
- **CognitiveStatePanel** — Когнитивные метрики (графики)

### HEALER Dashboard
- **HealerPage** — Главная страница: статус, циклы, мост
- **HealerReflectionPanel** — Панель рефлексии (WS + polling + rollback)
- **HealerTracePanel** — Трейсы HEALER
- **HealerResults** — Результаты диагностики
- **HealerReflection** — Отображение learnings + changes
- **HealerHistory** — История циклов

## TraceCollector (core)

`backend/core/trace_collector.py` — Thread-safe in-memory collector.

```python
class TraceCollector:
    def save_trace(session_id, event)          # Сохранить событие
    def get_trace(session_id) -> list[dict]    # Получить трейс сессии
    def list_traces(limit, phase, severity)    # Сводка с фильтрацией (>= min_severity)
    def subscribe(callback)                    # Подписка на события
    def unsubscribe(callback)                  # Отписка
```

Фильтрация `list_traces()`:
- `phase` — точное совпадение
- `severity` — минимальный уровень (включительно): info < warning < error < critical

## WebSocket архитектура

```
Клиент (React)                     Сервер (FastAPI)
    │                                    │
    │  connect /ws?token=...             │
    │───────────────────────────────────►│
    │                                    │  XRayBroadcaster
    │  subscribe {"channel": "trace"}    │  └── connect(websocket)
    │───────────────────────────────────►│  └── subscribe(ws, "trace")
    │                                    │
    │  trace_update {...}                │  Любой компонент:
    │◄───────────────────────────────────│  broadcaster.broadcast("trace", data)
    │                                    │
    │  thought {...}                     │  Pipeline phase:
    │◄───────────────────────────────────│  thought_stream.record(phase, text)
    │                                    │
    │  healer_bridge_reflection {...}    │  После healing cycle:
    │◄───────────────────────────────────│  reflect() + broadcast
```

## Тесты

### X-Ray тесты (`tests/test_xray/`)
- Monolith: 20 фаз, порядок, длительности
- Anti-loop: блокировка цикла
- Safety block: проверка безопасности
- Strategy: выбор стратегии
- Degradation: деградация non-critical
- Thought stream: мысли AI

### HEALER тесты (`tests/test_healing/`)
- `test_reflection_loop.py` — 7 тестов: пустые циклы, ошибки, фиксы, смешанные статусы
- `test_changes_store.py` — 7 тестов: apply, rollback, статусы, изоляция

Запуск:
```bash
pytest tests/test_xray/ -v
pytest tests/test_healing/ -v
```
