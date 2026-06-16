# Meta/Cognitive System — мета-система

## Компоненты

### MetaLearner (`backend/core/xray/meta_learner.py`)

Система мета-обучения: анализирует успешность стратегий
и адаптирует поведение.

- `get_best_strategy(context)` — выбор оптимальной стратегии
- `should_adjust_strategy(ctx)` — проверка необходимости смены
- `set_strategy_override(strategy)` — принудительный override
- `record_outcome(ctx, result)` — запись результата
- `get_stats()` — статистика по всем стратегиям

### CognitiveState (`backend/core/xray/cognitive_state.py`)

Когнитивные метрики текущей сессии:

| Метрика | Описание |
|---------|----------|
| uncertainty | Неопределённость (0-1) |
| cognitive_load | Когнитивная нагрузка (0-1) |
| confidence | Уверенность (0-1) |
| complexity | Сложность задачи (0-1) |

Также: дерево решений (`DecisionNode`), веса источников
информации (`SourceWeight`).

### ReflectionLoop (`backend/core/xray/reflection.py`)

Post-hoc анализ результатов:

- Сравнение ожидаемой и фактической уверенности
- Извлечение уроков
- Обновление MetaLearner на основе результатов

### SystemState (`backend/core/xray/system_state.py`)

Общее состояние системы:

- `SystemState` — load, confidence, errors
- `SystemStateManager` — управление, снапшоты
- `get_system_state_manager()` — singleton

## Dream System (`backend/core/dreams.py`)

Автономная обработка вне сессии:

- **REM-фаза** — затухание эмоций
- **Slow-wave фаза** — консолидация памяти
- **Integration фаза** — построение связей

## Truth Loop (`backend/core/truth_loop.py`)

Верификация утверждений в ответе:

- `Claim` — проверяемое утверждение
- `ClaimStatus` — VERIFIED / CONTRADICTED / UNVERIFIED
- `TruthEngine` — проверка на противоречия с памятью

## X-Ray: система наблюдаемости

14 модулей в `backend/core/xray/`:

| Компонент | Роль |
|-----------|------|
| TraceCollector | Сбор трасс выполнения |
| Broadcaster | WebSocket рассылка |
| ThoughtVisualizer | Визуализация мыслей |
| HistoryRecorder | Запись сессий в БД |
| EventBuffer | Буферизация событий |
| InsightsEngine | Аналитика и аномалии |

## Архитектурная схема

```
Запрос → Pipeline (22 фазы)
              ↓
         MetaLearner ←→ ReflectionLoop
              ↓
       CognitiveState (метрики сессии)
              ↓
         TraceCollector → Broadcaster → WebSocket
              ↓
       HistoryRecorder → Supabase/Postgres
              ↓
     (каждые N диалогов) Consolidation
              ↓
         DreamSystem (вне сессии)
```

## Интеграция

- Все pipeline фазы записываются в X-Ray
- MetaLearner влияет на выбор стратегии в pipeline
- ReflectionLoop запускается после выполнения pipeline
- CognitiveState обновляется на каждой фазе
