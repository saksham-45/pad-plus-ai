# 🔬 X-Ray Implementation Guide

## Обзор реализации

X-Ray — система полной наблюдаемости внутренней работы PAD+ AI, реализованная в виде:

### Backend компоненты

| Файл | Описание |
|------|----------|
| `backend/core/xray/__init__.py` | Экспорт модулей |
| `backend/core/xray/trace_collector.py` | Сбор данных трассировки |
| `backend/core/xray/thought_visualizer.py` | Визуализация мыслей |
| `backend/core/xray/broadcaster.py` | WebSocket трансляция |
| `backend/core/xray/history_recorder.py` | Запись сессий |
| `backend/api/xray_routes.py` | API endpoints |

### Frontend компоненты

| Файл | Описание |
|------|----------|
| `frontend/src/components/xray/XRayPipeline.jsx` | Визуализация пайплайна |
| `frontend/src/components/xray/ThoughtStream.jsx` | Поток мыслей |
| `frontend/src/components/xray/index.js` | Экспорт компонентов |
| `frontend/src/pages/XRayPage.jsx` | Страница X-Ray |

### Документация

| Файл | Описание |
|------|----------|
| `docs/XRAY.md` | Полная документация системы |

## Быстрый старт

### 1. Запуск backend

```bash
cd backend
uvicorn main:app --reload --port 8080
```

### 2. Запуск frontend

```bash
cd frontend
npm run dev
```

### 3. Доступ к X-Ray

Откройте http://localhost:5174 и перейдите на вкладку "🔬 X-Ray"

## API Endpoints

### REST API

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/v1/xray/` | GET | Информация о системе |
| `/api/v1/xray/sessions` | GET | Список сессий |
| `/api/v1/xray/sessions/{id}` | GET | Детали сессии |
| `/api/v1/xray/sessions/{id}/export` | GET | Экспорт сессии |
| `/api/v1/xray/stats` | GET | Статистика |
| `/api/v1/xray/active` | GET | Активные сессии |
| `/api/v1/xray/recent` | GET | Последние трассировки |

### WebSocket

```
ws://localhost:8080/api/v1/xray/ws
```

#### Подписка на каналы

```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  channels: ['trace', 'thought', 'pipeline', 'emotion', 'decision', 'all']
}));
```

## Интеграция с пайплайном

Для включения X-Ray трассировки в существующий пайплайн:

```python
from core.xray import (
    get_trace_collector,
    get_thought_visualizer,
    get_xray_broadcaster,
    TraceStage
)

# В начале обработки запроса
collector = get_trace_collector()
request_id = collector.start_session(user_message)

# На каждой стадии
start = time.time()
# ... выполнение стадии ...
duration = (time.time() - start) * 1000

collector.record_event(
    request_id=request_id,
    stage=TraceStage.SAFETY,
    data={"passed": True},
    duration_ms=duration
)

# В конце
collector.complete_session(request_id, {
    "response": result.response,
    "success": result.success
})
```

## Визуализация мыслей

```python
from core.xray import get_thought_visualizer

visualizer = get_thought_visualizer()

# Создание мысли
thought = visualizer.intent_classification(
    intent="explain_concept",
    confidence=0.92
)

# Мысль автоматически добавляется в буфер
# и может быть отправлена через WebSocket
```

## Конфигурация

### Переменные окружения

```bash
# Включение/выключение X-Ray
XRAY_ENABLED=true

# Максимальное количество сессий в памяти
XRAY_MAX_SESSIONS=100

# Путь для хранения истории
XRAY_STORAGE_PATH=data/xray_history

# Throttling (обновлений в секунду)
XRAY_THROTTLE_RATE=10
```

## Производительность

Система оптимизирована для minimal overhead:

- **Throttling**: не более 10 обновлений/сек
- **Batching**: группировка событий
- **Sampling**: для длинных процессов
- **Lazy loading**: загрузка деталей по требованию

## Будущие улучшения

1. **EmotionGraph** — визуализация динамики эмоций
2. **DecisionTree** — дерево принятых решений
3. **SourceTracker** — анализ источников информации
4. **XRayDashboard** — полный дашборд
5. **AI-ассистент** — автоматическое объяснение происходящего
6. **Сравнение сессий** — анализ эволюции мышления
7. **Аномалии** — обнаружение странных паттернов

## Структура проекта

```
backend/
├── core/
│   └── xray/
│       ├── __init__.py
│       ├── trace_collector.py
│       ├── thought_visualizer.py
│       ├── broadcaster.py
│       └── history_recorder.py
└── api/
    └── xray_routes.py

frontend/
└── src/
    ├── components/
    │   └── xray/
    │       ├── index.js
    │       ├── XRayPipeline.jsx
    │       └── ThoughtStream.jsx
    └── pages/
        └── XRayPage.jsx

docs/
└── XRAY.md
```

## Тестирование

### Тест WebSocket подключения

```javascript
const ws = new WebSocket('ws://localhost:8080/api/v1/xray/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'subscribe',
    channels: ['all']
  }));
};

ws.onmessage = (event) => {
  console.log('Received:', JSON.parse(event.data));
};
```

### Тест REST API

```bash
# Получить информацию о системе
curl http://localhost:8080/api/v1/xray/

# Получить статистику
curl http://localhost:8080/api/v1/xray/stats

# Получить активные сессии
curl http://localhost:8080/api/v1/xray/active
```

## Поддержка

Для вопросов и предложений:
- Документация: `docs/XRAY.md`
- Issues: GitHub repository