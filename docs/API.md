# 📚 PAD+ AI — API Specification v4.0

*PAD+ = Pleasure, Arousal, Dominance + Curiosity, Confidence, Social Connection*

## Base URL

```
http://localhost:8080/api/v1
```

## Содержание

1. [Chat](#chat)
2. [Memory (RAG)](#memory-rag)
3. [Episodic Memory](#episodic-memory)
4. [Semantic Memory](#semantic-memory)
5. [Facts](#facts)
6. [Knowledge Graph](#knowledge-graph)
7. [Emotions](#emotions)
8. [Autonomy](#autonomy)
9. [Dreams](#dreams)
10. [Consolidation](#consolidation)
11. [Hierarchical Plans](#hierarchical-plans)
12. [Persona](#persona)
13. [Pipeline](#pipeline)
14. [Hygiene](#hygiene)
15. [Safety](#safety)
16. [Truth Loop](#truth-loop)
17. [Events](#events)
18. [Health](#health)
19. [Meta-Cognition](#meta-cognition)
20. [Analytics](#analytics)
21. [Cache](#cache)
22. [Feedback](#feedback)
23. [Data Management](#data-management)
24. [Sessions](#sessions)
25. [Config](#config)
26. [WebSocket](#websocket)
27. [Rate Limiter](#rate-limiter)
28. [Mind State](#mind-state)

---

## Chat

### POST /chat

Основной чат-эндпоинт через Pipeline Executor.

**Request:**
```json
{
  "prompt": "Привет!",
  "context": {}
}
```

**Response:**
```json
{
  "prompt": "Привет!",
  "response": "Привет! Чем могу помочь?",
  "anti_directive": "Не закрепляй знания...",
  "confidence": 0.85,
  "provider": "gigachat",
  "intent": "greeting",
  "safety": {
    "passed": true,
    "warning": null
  },
  "truth": {
    "confidence": 0.8,
    "claims_verified": 2
  },
  "emotion_style": {
    "tone": "friendly",
    "verbosity": "moderate"
  },
  "rag_used": true,
  "facts_used": 1,
  "execution_time_ms": 250,
  "success": true,
  "errors": []
}
```

### GET /chat/stream

Потоковый чат (SSE).

### GET /gigachat/test

Тестовое подключение к GigaChat.

### GET /gigachat/status

Статус GigaChat.

---

## Memory (RAG)

### GET /rag/stats

Статистика RAG памяти v3.0.

**Response:**
```json
{
  "total_dialogs": 150,
  "with_keywords": 140,
  "summarized": 50,
  "total_entities": 300,
  "total_relations": 75,
  "topic_distribution": {
    "техническое": 45,
    "философское": 20,
    "личное": 30
  },
  "sentiment_distribution": {
    "positive": 60,
    "neutral": 80,
    "negative": 10
  },
  "persist_dir": "data/chroma",
  "version": "3.0",
  "features": {
    "hybrid_search": true,
    "keyword_extraction": true,
    "recency_ranking": true,
    "auto_summarization": true,
    "topic_classification": true,
    "entity_extraction": true,
    "relation_extraction": true,
    "llm_summarization": false
  }
}
```

### GET /rag/topics

Статистика по темам диалогов.

### GET /rag/entities

Индекс сущностей.

### POST /rag/search

Семантический поиск.

**Request:**
```json
{
  "query": "как настроить API",
  "n_results": 5
}
```

**Response:**
```json
{
  "query": "как настроить API",
  "results": [
    {
      "id": "abc123",
      "document": "Вопрос: ... Ответ: ...",
      "similarity": 0.89,
      "topic": "техническое",
      "entities": [...],
      "relations": [...]
    }
  ],
  "total": 1
}
```

### POST /rag/hybrid

Гибридный поиск с ранжированием.

**Request:**
```json
{
  "query": "настройка",
  "n_results": 5,
  "use_keywords": true,
  "use_recency": true
}
```

### POST /rag/by-topic

Поиск по теме.

**Request:**
```json
{
  "topic": "техническое",
  "n_results": 5
}
```

### GET /rag/recent

Недавние диалоги.

**Query:** `?days=7&limit=10`

### POST /rag/keywords

Поиск по ключевым словам.

**Request:**
```json
{
  "keywords": ["API", "настройка"],
  "n_results": 5
}
```

### POST /rag/clear

Очистка RAG памяти.

---

## Episodic Memory

### GET /episodic/stats

Статистика эпизодической памяти.

**Response:**
```json
{
  "total_episodes": 150,
  "with_emotional_context": 120,
  "significant_episodes": 25,
  "oldest_episode": "2026-02-17T10:00:00",
  "newest_episode": "2026-02-21T10:00:00"
}
```

### POST /episodic/search

Поиск эпизодов.

**Request:**
```json
{
  "query": "разговор о Python",
  "limit": 10
}
```

### GET /episodic/timeline

Timeline эпизодов.

**Query:** `?days=7`

### GET /episodic/significant

Значимые эпизоды.

### GET /episodic/emotional

Эпизоды с эмоциональным контекстом.

### GET /episodic/{id}

Получить эпизод по ID.

### GET /episodic/{id}/related

Связанные эпизоды.

---

## Semantic Memory

### GET /semantic/stats

Статистика семантической памяти.

**Response:**
```json
{
  "total_concepts": 200,
  "by_category": {
    "declarative": 100,
    "procedural": 30,
    "conceptual": 50,
    "metacognitive": 20
  }
}
```

### POST /semantic/search

Поиск концепций.

**Request:**
```json
{
  "query": "программирование",
  "category": "conceptual",
  "limit": 10
}
```

### GET /semantic/{id}

Получить концепцию по ID.

### GET /semantic/self

Метакогнитивные знания о себе.

### POST /semantic/procedure/{id}/apply

Применить процедурное знание.

### GET /semantic/procedure/find

Найти процедуру по триггеру.

---

## Facts

### POST /facts

Создать факт.

**Request:**
```json
{
  "subject": "Python",
  "predicate": "is_a",
  "object": "programming language",
  "confidence": 0.9,
  "source": "user"
}
```

### GET /facts/stats

Статистика фактов.

### POST /facts/search

Поиск фактов.

**Request:**
```json
{
  "query": "Python",
  "limit": 10
}
```

### GET /facts/contradictions

Найти противоречия в фактах.

---

## Knowledge Graph

### GET /knowledge/graph

Получить граф знаний.

**Response:**
```json
{
  "nodes": [
    {
      "id": "concept_1",
      "name": "Python",
      "type": "language",
      "confidence": 0.9
    }
  ],
  "links": [
    {
      "source": "concept_1",
      "target": "concept_2",
      "type": "related"
    }
  ],
  "stats": {
    "nodes": 10,
    "edges": 15,
    "density": 0.33
  }
}
```

### POST /knowledge/concepts

Создать концепцию.

**Request:**
```json
{
  "name": "Machine Learning",
  "type": "concept",
  "confidence": 0.8,
  "metadata": {}
}
```

### POST /knowledge/relations

Создать связь.

**Request:**
```json
{
  "source_id": "concept_1",
  "target_id": "concept_2",
  "type": "related",
  "weight": 1.0
}
```

---

## Emotions

### GET /emotion/state

Текущее эмоциональное состояние (PAD+).

**Response:**
```json
{
  "удовольствие": 0.3,
  "возбуждение": 0.5,
  "доминирование": 0.2,
  "любопытство": 0.8,
  "уверенность": 0.6,
  "социальная_связь": 0.4,
  "updated_at": "2026-02-20T15:00:00",
  "trigger": "user_interaction",
  "style": {
    "tone": "friendly",
    "verbosity": "moderate",
    "color": "balanced"
  }
}
```

---

## Autonomy

### GET /autonomy/status

Статус автономных процессов.

**Response:**
```json
{
  "planner": {
    "running": true,
    "pending_tasks": 5,
    "completed_tasks": 42,
    "dialog_count": 100,
    "reflection_interval": 10,
    "last_auto_reflection": "2026-02-20T10:00:00"
  },
  "quality": {
    "total_assessed": 50,
    "average_score": 0.75,
    "low_quality_count": 5
  },
  "knowledge_extractions": 25,
  "self_reflection": {
    "last_reflection": "2026-02-20T10:00:00",
    "total_findings": 12
  }
}
```

### POST /autonomy/start

Запустить планировщик.

### POST /autonomy/stop

Остановить планировщик.

### POST /autonomy/reflect

Запустить саморефлексию.

---

## Dreams

### GET /dreams/stats

Статистика сновидений.

**Response:**
```json
{
  "total_dreams": 25,
  "last_dream": "2026-02-21T05:00:00",
  "insights_found": 15,
  "connections_created": 30,
  "phases_used": {
    "NREM1": 25,
    "NREM2": 25,
    "NREM3": 20,
    "REM": 15
  }
}
```

### POST /dreams/run

Запустить сновидение.

**Response:**
```json
{
  "status": "completed",
  "phase": "REM",
  "duration_seconds": 5.2,
  "insights": [
    "Обнаружена связь между Python и Machine Learning"
  ],
  "connections_created": 3
}
```

### GET /dreams/last

Последнее сновидение.

### GET /dreams/should-dream

Проверка необходимости сновидения.

**Response:**
```json
{
  "should_dream": true,
  "reason": "Низкая активность более 5 минут",
  "memory_accumulated": 150
}
```

---

## Consolidation

### GET /consolidation/stats

Статистика консолидации.

**Response:**
```json
{
  "total_consolidations": 10,
  "last_consolidation": "2026-02-21T05:00:00",
  "episodic_to_semantic": 50,
  "facts_extracted": 25,
  "patterns_found": 10
}
```

### POST /consolidation/run

Запустить консолидацию памяти.

**Response:**
```json
{
  "status": "completed",
  "duration_seconds": 3.5,
  "episodes_processed": 100,
  "concepts_created": 5,
  "patterns_found": 3
}
```

---

## Hierarchical Plans

### GET /plans/stats

Статистика планов.

**Response:**
```json
{
  "total_goals": 5,
  "total_tasks": 15,
  "total_actions": 50,
  "completed_actions": 30,
  "active_goals": 3
}
```

### GET /plans/hierarchy

Полная иерархия планов.

**Response:**
```json
{
  "goals": [
    {
      "id": "goal_1",
      "title": "Улучшить качество ответов",
      "status": "in_progress",
      "progress": 0.6,
      "tasks": [
        {
          "id": "task_1",
          "title": "Анализ проблемных областей",
          "status": "completed",
          "actions": [...]
        }
      ]
    }
  ]
}
```

### GET /plans/goals

Список целей.

### POST /plans/goals

Создать цель.

**Request:**
```json
{
  "title": "Улучшить память",
  "description": "Оптимизировать извлечение контекста",
  "priority": 0.8
}
```

### GET /plans/next-actions

Следующие действия.

**Response:**
```json
{
  "actions": [
    {
      "id": "action_1",
      "title": "Запустить рефлексию",
      "priority": 0.9,
      "goal_id": "goal_1",
      "task_id": "task_1"
    }
  ]
}
```

### GET /plans/{id}

Получить план по ID.

### PUT /plans/{id}/progress

Обновить прогресс.

**Request:**
```json
{
  "progress": 0.7
}
```

---

## Persona

### GET /persona/stats

Статистика персоны.

**Response:**
```json
{
  "traits_count": 8,
  "total_interactions": 150,
  "reflections_count": 25,
  "dominant_traits": ["curiosity", "helpfulness", "adaptability"]
}
```

### GET /persona/traits

Все черты характера.

**Response:**
```json
{
  "traits": {
    "curiosity": {
      "name": "Любопытство",
      "value": 0.85,
      "description": "Интерес к новому",
      "stability": 0.9
    },
    "helpfulness": {
      "name": "Помощь",
      "value": 0.9,
      "description": "Стремление помочь",
      "stability": 0.95
    }
  }
}
```

### POST /persona/adjust

Корректировка черты.

**Request:**
```json
{
  "trait": "curiosity",
  "delta": 0.1
}
```

### GET /persona/values

Ценности и принципы.

### GET /persona/reflections

Недавние саморефлексии.

**Query:** `?limit=5`

### POST /persona/reflect

Добавить саморефлексию.

**Request:**
```json
{
  "insight": "Пользователь предпочитает краткие ответы",
  "action": "Уменьшить многословность",
  "confidence": 0.7
}
```

### GET /persona/context

Контекст личности для промптов.

---

## Pipeline

### GET /pipeline/stats

Статистика пайплайна.

**Response:**
```json
{
  "total_calls": 500,
  "successful_calls": 480,
  "failed_calls": 20,
  "avg_execution_time_ms": 200,
  "stages": {
    "safety": {"calls": 500, "avg_ms": 5},
    "intent": {"calls": 500, "avg_ms": 10},
    "retrieve": {"calls": 500, "avg_ms": 50},
    "generate": {"calls": 500, "avg_ms": 150}
  }
}
```

---

## Hygiene

### GET /hygiene/stats

Статистика гигиены памяти.

**Response:**
```json
{
  "total_cleanups": 10,
  "last_cleanup": "2026-02-20T10:00:00",
  "config": {
    "similarity_threshold": 0.85,
    "obsolete_days": 90,
    "usefulness_threshold": 0.2,
    "max_items": 10000
  },
  "memory_stats": {
    "rag_count": 150,
    "facts_count": 50
  }
}
```

### POST /hygiene/analyze

Анализ памяти (dry run).

**Query:** `?dry_run=true`

**Response:**
```json
{
  "items_scanned": 500,
  "duration_seconds": 2.5,
  "duplicates": {
    "found": 15,
    "removed": 0
  },
  "obsolete": {
    "found": 8,
    "removed": 0
  },
  "low_quality": {
    "found": 3
  },
  "recommendations": [
    "Найдено 15 дубликатов — рекомендуется очистка",
    "8 записей устарели (более 90 дней)"
  ]
}
```

### POST /hygiene/cleanup

Выполнить очистку памяти.

### POST /hygiene/config

Обновить настройки гигиены.

**Request:**
```json
{
  "similarity_threshold": 0.9,
  "obsolete_days": 60
}
```

---

## Safety

### GET /safety/stats

Статистика безопасности.

**Response:**
```json
{
  "requests_last_minute": 5,
  "autonomous_actions": 12,
  "strict_mode": false,
  "blocked_requests": 3,
  "warnings": 5
}
```

### POST /safety/check

Проверка текста на безопасность.

**Request:**
```json
{
  "text": "Обычный запрос"
}
```

**Response:**
```json
{
  "passed": true,
  "warning": null,
  "risk_level": "low",
  "checks": {
    "injection": false,
    "harmful": false,
    "recursive": false
  }
}
```

### POST /safety/strict-mode

Включить/выключить строгий режим.

**Query:** `?enable=true`

---

## Truth Loop

### GET /truth/stats

Статистика верификации.

**Response:**
```json
{
  "total_claims": 100,
  "average_confidence": 0.75,
  "verified_claims": 80,
  "contradictions_found": 5
}
```

### POST /truth/verify

Верификация текста.

**Request:**
```json
{
  "text": "Python был создан в 1991 году"
}
```

**Response:**
```json
{
  "claims": [
    {
      "text": "Python был создан в 1991 году",
      "confidence": 0.9,
      "verified": true,
      "sources": ["internal_knowledge"]
    }
  ],
  "overall_confidence": 0.9
}
```

---

## Events

### GET /events/history

История событий.

**Query:** `?limit=20`

**Response:**
```json
{
  "events": [
    {
      "id": "evt_1",
      "type": "chat.message",
      "data": {...},
      "timestamp": "2026-02-20T15:00:00"
    }
  ],
  "total": 20
}
```

### GET /events/stats

Статистика событий.

**Response:**
```json
{
  "total_events": 500,
  "handlers_count": 5,
  "events_by_type": {
    "chat.message": 200,
    "memory.stored": 150,
    "emotion.changed": 50
  }
}
```

---

## Health

### GET /health

Оценка когнитивного здоровья.

**Response:**
```json
{
  "overall_score": 0.85,
  "status": "healthy",
  "metrics": {
    "cognitive_clarity": 0.9,
    "memory_integrity": 0.85,
    "emotional_stability": 0.8,
    "response_quality": 0.85,
    "learning_progress": 0.75
  },
  "timestamp": "2026-02-20T15:00:00"
}
```

### GET /health/report

Текстовый отчёт о здоровье.

### GET /health/issues

Проблемы здоровья.

**Response:**
```json
{
  "issues": [
    {
      "type": "high_load",
      "severity": "warning",
      "message": "Когнитивная нагрузка высока",
      "recommendation": "Снизить активность"
    }
  ],
  "total": 1
}
```

### GET /health/recommendations

Рекомендации по улучшению.

### POST /health/metric

Обновить метрику здоровья.

**Request:**
```json
{
  "name": "cognitive_clarity",
  "value": 0.9,
  "reason": "Хороший отдых"
}
```

### POST /health/event

Записать событие здоровья.

**Request:**
```json
{
  "event_type": "user_praise",
  "impact": 0.1
}
```

---

## Meta-Cognition

### GET /meta/stats

Статистика мета-когнитивного контроллера.

**Response:**
```json
{
  "state": "idle",
  "total_requests": 500,
  "strategy_distribution": {
    "simple": 200,
    "deep": 150,
    "creative": 50,
    "reflective": 100
  },
  "successful_adaptations": 25,
  "cognitive_load": {
    "current": 0.3,
    "memory_usage": 0.4,
    "processing_queue": 0,
    "recent_errors": 0
  },
  "subsystems": 8,
  "recent_decisions": 10
}
```

### GET /meta/report

Мета-когнитивный отчёт.

### GET /meta/load

Оценка когнитивной нагрузки.

**Response:**
```json
{
  "current": 0.3,
  "memory_usage": 0.4,
  "processing_queue": 0,
  "recent_errors": 0,
  "last_updated": "2026-02-20T15:00:00"
}
```

### GET /meta/state

Текущее состояние системы.

### POST /meta/decide

Выбрать стратегию обработки.

**Request:**
```json
{
  "query": "Объясни квантовую физику",
  "context": {}
}
```

**Response:**
```json
{
  "strategy": "deep",
  "reason": "Запрос требует глубокого анализа",
  "confidence": 0.85,
  "estimated_time": 4.0,
  "resources_needed": ["rag", "knowledge_graph", "facts", "truth_loop"]
}
```

### GET /meta/subsystems

Статус подсистем.

### POST /meta/adapt

Адаптация на основе обратной связи.

**Request:**
```json
{
  "success": true,
  "strategy": "deep",
  "response_time": 3.5,
  "reason": "Хороший ответ"
}
```

---

## Analytics

### GET /analytics/dashboard

Метрики дашборда.

**Query:** `?days=7`

### GET /analytics/activity

Граф активностей.

**Query:** `?days=7`

### GET /analytics/topics

Статистика по темам.

**Query:** `?days=7&limit=10`

### GET /analytics/report

Полный отчёт аналитики.

**Query:** `?days=7`

**Response:**
```json
{
  "dashboard": {
    "total_messages": 500,
    "messages_by_role": {
      "user": 250,
      "ai": 250
    },
    "avg_session_length": 8
  },
  "activity": {
    "hourly": {
      "data": [5, 10, 15, ...],
      "labels": ["00:00", "01:00", ...],
      "peak_hour": 14
    },
    "weekday": {
      "data": [50, 60, 70, ...],
      "labels": ["Пн", "Вт", ...],
      "peak_day": "Ср"
    }
  },
  "topics": {
    "top_topics": [
      {"topic": "программирование", "count": 45},
      {"topic": "API", "count": 30}
    ]
  }
}
```

---

## Cache

### GET /cache/stats

Статистика кэша ответов.

**Response:**
```json
{
  "total_entries": 100,
  "cache_hits": 500,
  "cache_misses": 200,
  "hit_rate": 0.71,
  "total_size_bytes": 50000
}
```

### GET /cache/top

Топ запросов из кэша.

**Query:** `?limit=10`

### POST /cache/invalidate

Инвалидация кэша.

**Query:** `?all=true`

---

## Feedback

### POST /feedback

Добавить обратную связь.

**Request:**
```json
{
  "user_message": "Что такое Python?",
  "ai_response": "Python — это язык программирования...",
  "feedback_type": "thumbs_up",
  "rating": 5,
  "comment": "Отличный ответ!",
  "intent": "question",
  "provider": "gigachat"
}
```

### GET /feedback/stats

Статистика обратной связи.

**Response:**
```json
{
  "total_feedback": 100,
  "by_type": {
    "thumbs_up": 60,
    "thumbs_down": 10,
    "rating": 20,
    "correction": 10
  },
  "average_rating": 4.5,
  "satisfaction_rate": 0.85
}
```

### GET /feedback/problems

Проблемные области.

### GET /feedback/recommendations

Рекомендации по улучшению.

### GET /feedback/training-data

Данные для обучения (RLHF).

**Query:** `?limit=100`

---

## Data Management

### POST /data/export

Экспорт всех данных.

**Response:**
```json
{
  "status": "exported",
  "filepath": "data/backups/neuromind_2026_02_20.json",
  "timestamp": "2026-02-20T15:00:00"
}
```

### GET /data/exports

Список backup файлов.

### POST /data/import

Импорт данных из backup.

**Request:**
```json
{
  "filepath": "data/backups/neuromind_2026_02_20.json",
  "merge": true
}
```

### POST /data/cleanup

Очистка старых backup.

**Query:** `?keep=10`

---

## Sessions

### POST /sessions

Создать новую сессию.

**Request:**
```json
{
  "settings": {
    "language": "ru",
    "verbose": true
  }
}
```

**Response:**
```json
{
  "session_id": "sess_abc123",
  "created_at": "2026-02-20T15:00:00",
  "settings": {
    "language": "ru",
    "verbose": true
  }
}
```

### GET /sessions/{session_id}

Получить сессию.

### DELETE /sessions/{session_id}

Завершить сессию.

### GET /sessions/stats

Статистика сессий.

### POST /sessions/{session_id}/settings

Обновить настройки сессии.

**Request:**
```json
{
  "settings": {
    "language": "en"
  }
}
```

---

## Config

### GET /config

Получить всю конфигурацию.

### GET /config/{key}

Получить значение конфигурации.

### POST /config

Установить значение конфигурации.

**Request:**
```json
{
  "key": "safety.strict_mode",
  "value": true,
  "description": "Включить строгий режим"
}
```

### POST /config/{key}/reset

Сбросить значение к умолчанию.

### GET /config/validate

Валидация конфигурации.

### GET /config/export

Экспорт конфигурации в .env формат.

---

## WebSocket

### GET /websocket/stats

Статистика WebSocket соединений.

**Response:**
```json
{
  "active_connections": 5,
  "total_messages": 500,
  "total_connections": 20
}
```

---

## Rate Limiter

### GET /rate-limiter/stats

Статистика Rate Limiter.

**Response:**
```json
{
  "total_requests": 1000,
  "blocked_requests": 50,
  "active_clients": 10
}
```

### GET /rate-limiter/client/{client_id}

Статистика по клиенту.

### POST /rate-limiter/reset/{client_id}

Сброс лимитов для клиента.

---

## Roots Memory

### GET /roots

Все корневые знания.

**Response:**
```json
{
  "roots": [
    {
      "id": "root_1",
      "category": "philosophy",
      "content": "Сомнение — основа познания",
      "confidence": 1.0
    }
  ],
  "total": 10,
  "categories": {
    "philosophy": 5,
    "ethics": 3,
    "identity": 2
  }
}
```

### GET /roots/categories

Категории корневых знаний.

### GET /roots/philosophy

Философские принципы.

### GET /roots/ethics

Этические принципы.

### GET /roots/identity

Факты об идентичности.

### POST /roots/search

Поиск в корневых знаниях.

**Request:**
```json
{
  "query": "сознание",
  "limit": 10
}
```

### GET /roots/context

Экспорт для контекста LLM.

---

## Mind State

### GET /mind-state

Полное состояние системы.

**Response:**
```json
{
  "emotion": {
    "удовольствие": 0.3,
    "возбуждение": 0.5,
    "доминирование": 0.2,
    "любопытство": 0.8,
    "уверенность": 0.6,
    "социальная_связь": 0.4,
    "style": {
      "tone": "friendly",
      "verbosity": "moderate",
      "color": "balanced"
    }
  },
  "memory": {
    "rag": {
      "total_dialogs": 150,
      "total_entities": 300
    },
    "facts": {
      "total_facts": 50
    }
  },
  "knowledge": {
    "nodes": 10,
    "edges": 15
  },
  "autonomy": {
    "running": true,
    "dialog_count": 42,
    "quality_stats": {
      "average_score": 0.75
    }
  },
  "truth": {
    "total_claims": 100,
    "average_confidence": 0.75
  },
  "safety": {
    "requests_last_minute": 5,
    "autonomous_actions": 12
  },
  "events": {
    "total_events": 200,
    "handlers_count": 5
  },
  "timestamp": "2026-02-20T15:00:00"
}
```

---

## Error Responses

Все эндпоинты возвращают ошибки в формате:

```json
{
  "detail": "Описание ошибки",
  "status_code": 400
}
```

## Rate Limiting

- Стандартные запросы: 60/мин
- Чат: 10/мин
- Поиск: 30/мин

## Interactive Documentation

- **Swagger UI:** http://localhost:8080/docs
- **ReDoc:** http://localhost:8080/redoc

---

## Аутентификация (Supabase Auth)

### POST /api/v1/auth/register

Регистрация нового пользователя.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "Имя Фамилия"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "Имя Фамилия"
  }
}
```

### POST /api/v1/auth/login

Вход пользователя.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

### GET /api/v1/auth/me

Получение текущего пользователя.

**Headers:** `Authorization: Bearer <token>`

---

## Управление ключами

### GET /api/v1/keys

Список API ключей пользователя.

**Query:** `?offset=0&limit=100`

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "provider": "gigachat",
      "provider_display_name": "GigaChat",
      "name": "Мой ключ",
      "model_preference": "GigaChat",
      "is_default": true,
      "is_active": true,
      "created_at": "2026-04-07T...",
      "has_key": true
    }
  ]
}
```

### POST /api/v1/keys

Добавление API ключа.

**Request:**
```json
{
  "provider": "gigachat",
  "api_key": "OTkyNTczMWUt...",
  "name": "GigaChat Key",
  "model_preference": "GigaChat",
  "is_default": true
}
```

### PATCH /api/v1/keys/{key_id}

Обновление ключа (модель, имя, статус).

**Request:**
```json
{
  "model_preference": "GigaChat-Pro"
}
```

### DELETE /api/v1/keys/{key_id}

Удаление ключа.

### POST /api/v1/keys/{key_id}/set-default

Установить ключ по умолчанию.

### POST /api/v1/keys/{key_id}/test

Тест подключения ключа.

---

## Провайдеры

### GET /api/v1/providers

Список всех доступных провайдеров.

### GET /api/v1/models

Список всех доступных моделей.

**Query:** `?provider=openai`

### GET /api/v1/providers/{provider_id}/models

Модели конкретного провайдера.

**Пример:** `GET /api/v1/providers/groq/models`