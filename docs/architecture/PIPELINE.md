# Pipeline — система обработки запросов

## Концепция

Pipeline — оркестратор, последовательно выполняющий 22 фазы
обработки каждого пользовательского запроса. Каждая фаза —
изолированный модуль, читающий и пишущий в PipelineContext.

## Порядок выполнения

```
 1. AntiLoop     — обнаружение циклов
 2. Safety       — проверка безопасности
 3. Intent       — классификация намерения
 4. RAG          — векторный поиск по диалогам
 5. KnowledgeGraph — граф знаний
 6. Episodic     — эпизодическая память
 7. Semantic     — процедурные знания
 8. Emotion      — чтение эмоций
 9. Persona      — контекст личности
10. Roots        — фундаментальные принципы
11. Identity     — вопросы о себе
12. Generate     — LLM генерация ответа
13. TruthLoop    — верификация утверждений
14. SaveEpisode  — сохранение эпизода
15. EmotionUpdate — обновление эмоций
16. PersonaEvolution — эволюция личности
17. EventsBroadcast — WebSocket события
18. HealthMonitor — мониторинг здоровья
19. Reflection   — рефлексия
20. Dreams       — запись снов
21. Metrics      — сбор метрик
22. ResponseGuard — финальная проверка
```

## Ключевые классы

| Класс | Файл | Роль |
|-------|------|------|
| `PipelinePhase` | `base.py` | ABC для всех фаз |
| `PipelineContext` | `context.py` | Контейнер данных (in/out каждой фазы) |
| `PipelineExecutor` | `executor.py` | Оркестратор 22 фаз |
| `PipelineResult` | `models.py` | Полный результат обработки |
| `PhaseResult` | `models.py` | Результат одной фазы (success, data, errors) |

## PipelineResult

После выполнения pipeline возвращает:
- `response` — текст ответа
- `strategy` — выбранная стратегия
- `confidence` — уверенность в ответе (0-1)
- `emotion_style` — эмоциональный стиль (tone, verbosity, color)
- `truth_confidence` — уверенность TruthLoop
- `episode_id` — ID сохранённого эпизода
- `degradations` — список деградаций, если фаза fallback'нулась
- `thoughts` — трассировка мыслей для X-Ray

## Интеграция

- X-Ray TraceCollector — каждая фаза трассируется
- MetaLearner — запись статистики стратегий
- ReflectionLoop — post-hoc анализ
- Broadcaster — WebSocket рассылка событий
- Consolidation — каждые N диалогов

## Публичный API

- `get_pipeline()` — фабрика
- `PipelineExecutor.execute(ctx)` — запуск

## Код

- `backend/core/pipeline/` — все компоненты
- `backend/core/pipeline/phases/` — 22 фазы
