# � X-Ray — Система наблюдения за внутренней жизнью PAD+ AI

## Что это

X-Ray — это **полная визуализация каждого шага мышления** AI в реальном времени.

Не просто логи. Не просто метрики. А **интерактивная панель** показывающая:
- Что AI думает на каждом этапе
- Какие данные использует
- Сколько времени тратит
- Какие ошибки возникают

## Архитектура

```
backend/core/xray/
├── __init__.py
├── tracer.py          # Trace каждого запроса
├── span.py            # Отдельный этап обработки
├── history_recorder.py # История запросов
└── models.py          # Модели данных

backend/api/
└── xray_routes.py     # API эндпоинты

frontend/src/
└── components/
    └── XRayPanel.jsx  # UI панель
```

## Как работает

### 1. Trace запроса

Каждый запрос получает уникальный `trace_id`:

```
Trace: abc123
├─ [0ms] Intent: question (confidence: 0.92)
├─ [2ms] Cognitive Budget: BALANCED (complexity: 0.45)
├─ [3ms] Model Router: groq/llama-3.1-70b-versatile
├─ [5ms] RAG: найдено 3 диалога
├─ [8ms] Facts: найдено 2 факта
├─ [12ms] Knowledge Graph: 5 концепций
├─ [15ms] Emotion: удовольствие=0.3, любопытство=0.7
├─ [18ms] Persona: curiosity=0.85
├─ [1200ms] LLM: генерация... (45 токенов)
├─ [1205ms] Truth Loop: 2 claims verified (0.88)
├─ [1208ms] ResponseGuard: 0 замен
├─ [1210ms] Memory: сохранено
└─ [1212ms] Ответ отправлен
```

### 2. API Endpoints

| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/xray/recent` | Последние 50 трейсов |
| `GET /api/v1/xray/{trace_id}` | Детали конкретного трейса |
| `GET /api/v1/xray/stats` | Статистика X-Ray |
| `WS /ws/xray` | Real-time обновления |

### 3. UI Панель

Правый сайдбар с вкладками:
- **Trace** — текущий запрос по этапам
- **History** — история запросов
- **Stats** — latency, ошибки, модели

## Реализация

### Шаг 1: Модели данных

```python
@dataclass
class Span:
    name: str           # "RAG", "LLM", "Truth"
    start_ms: float     # Время начала
    end_ms: float       # Время конца
    status: str         # "ok", "error", "skipped"
    details: dict       # Детали этапа
    error: str = None   # Текст ошибки

@dataclass 
class Trace:
    id: str             # Уникальный ID
    user_message: str   # Запрос пользователя
    response: str       # Ответ AI
    spans: list[Span]   # Этапы
    total_ms: float     # Общее время
    timestamp: str      # Время запроса
    model: str          # Использованная модель
    provider: str       # Провайдер
    thinking_mode: str  # fast/balanced/deep
```

### Шаг 2: Интеграция в Pipeline

В `pipeline.py` добавляем:

```python
from core.xray import get_xray_tracer

async def execute(self, user_message, ...):
    tracer = get_xray_tracer()
    trace = tracer.start_trace(user_message)
    
    # Каждый этап:
    with trace.span("RAG"):
        rag_context = rag.get_context(user_message)
    
    with trace.span("LLM"):
        response = await litellm.generate(...)
    
    tracer.finish_trace(trace)
    return result
```

### Шаг 3: Хранилище

In-memory хранилище последних 100 трейсов:

```python
class XRayStore:
    def __init__(self):
        self.traces = {}          # trace_id -> Trace
        self.recent_ids = []      # Последние 100 ID
        self.max_recent = 100
```

## Критерии готовности

- [ ] Trace каждого запроса
- [ ] Детализация по этапам
- [ ] История 100 запросов
- [ ] Real-time через WebSocket
- [ ] UI панель в правом сайдбаре
- [ ] Статистика latency p50/p95
