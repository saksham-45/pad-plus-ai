# План реализации PAD+ AI

> Создан на основе аудита кода проекта.
> Все оценки — в часах чистой разработки.

---

## Фаза 1 — Критические баги

~1ч

| # | Задача | Где | Что делать | Оценка |
|---|--------|-----|------------|--------|
| 1.1 | Починить импорт `provider_manager` | `backend/core/fallback_generator.py:238` | Заменить `from llm.provider_manager import get_provider_manager` → `from runtime.provider_manager import get_provider_manager`. Сейчас import всегда падает, `is_fallback_needed()` всегда возвращает `True` — система постоянно в fallback-режиме | 10мин |
| 1.2 | Убрать пустой `try-except` в DreamsPhase | `backend/core/pipeline/phases/dreams.py:15-16` | `except Exception: return PhaseResult(success=True)` проглатывает все ошибки. Нужно логировать и пробрасывать | 15мин |
| 1.3 | HEALER orchestrator — логировать сбой импорта | `HEALER/healer/orchestrator.py:105-110` | `except Exception: pass` скрывает ошибку загрузки `PythonPatcher`. Добавить `logger.warning` | 10мин |
| 1.4 | Залогировать все голые `except: pass` | `security_middleware.py:15`, `knowledge_graph.py` и др. | Заменить `pass` на `logger.warning(...)` по всему проекту | 20мин |
| 1.5 | Накатить миграцию `is_deleted` для корзины | `backend/database/migrations/017_documents_trash.sql` | Выполнить ALTER TABLE, чтобы корзина заработала | 5мин |

---

## Фаза 2 — Заполнить заглушки

~6ч

| # | Задача | Где | Что делать | Оценка |
|---|--------|-----|------------|--------|
| 2.1 | FallbackGenerator — реальные ответы | `backend/core/fallback_generator.py` | 6 стилей (Philosophical, Humorous, Serious, Curious, Empathetic, Minimalistic), ~15 хардкодных ответов. Заменить на шаблоны с подстановкой контекста пользователя + эмоциональной окраской | 2ч |
| 2.2 | MemoryInterface — реализовать заглушки | `backend/memory/base.py:97,110,122` | `clear()`, `update()`, `get()` — `NotImplementedError`. Реализовать в конкретных классах (episodic, semantic, rag) | 1ч |
| 2.3 | HEALER — первый рабочий детектор + патчер | `HEALER/healer/detectors/`, `patcher/` | `HighMemoryDetector` — проверяет `memory_usage > 90%`. `CacheCleanerPatcher` — чистит кэш L1. Связать через orchestrator | 2ч |
| 2.4 | HealerBridge — реальные запросы | `backend/integration/healer_bridge.py` | Сейчас все методы возвращают `[]`/`{}`. Подключить HTTP-клиент к HEALER API | 1ч |
| 2.5 | Monitoring — реальные метрики | `backend/core/monitoring.py:200,216,222` | `_calculate_avg_response_time()` всегда 0.5, `_get_active_connections()` всегда `[]`, `_get_queue_size()` всегда 0. Подключить к реальным данным | 30мин |

---

## Фаза 3 — Допилить UI

~7ч

| # | Задача | Где | Что делать | Оценка |
|---|--------|-----|------------|--------|
| 3.1 | Корзина документов — доделать | `frontend/src/pages/DocumentsPage.jsx` + `backend/api/document_routes.py` | Уже частично реализована (soft-delete, trash API). Доделать: кнопка "Восстановить все", бадж счётчика в sidebar, подтверждение очистки корзины | 1ч |
| 3.2 | Коллекции документов | `backend/api/document_routes.py` + `DocumentsPage.jsx` | Починить `POST/PATCH /collections`. Добавить: переименование коллекции, drag-n-drop документов между коллекциями | 2ч |
| 3.3 | Feedback в чате | `frontend/src/pages/ChatPage.jsx` + `backend/api/feedback_routes.py` | Добавить кнопки 👍/👎 к каждому сообщению ассистента. Отправлять `POST /feedback`. Показывать счётчик рейтинга | 2ч |
| 3.4 | Настройки документов | `backend/api/document_routes.py` + `DocumentsPage.jsx` | Подключить `PATCH /settings` к реальному сохранению в БД/файл | 1ч |
| 3.5 | Memory Dashboard — улучшить виджеты | `frontend/src/pages/MemoryPage.jsx` | Сейчас — плоский список ключ-значение. Добавить: прогресс-бары, графики, timeline консолидации | 1ч |

---

## Фаза 4 — X-Ray + MetaLearner + Dreams

~6ч

| # | Задача | Где | Что делать | Оценка |
|---|--------|-----|------------|--------|
| 4.1 | DreamsPhase — запустить dream() | `backend/core/pipeline/phases/dreams.py` + `executor.py` | Сейчас `record_activity()` вызывается, но `dream()` нет. Добавить вызов после N диалогов или по расписанию | 1ч |
| 4.2 | ReflectionPhase — MetaController | `backend/core/pipeline/phases/reflection.py` | Сейчас блок с `core.meta_controller` закомментирован (модуль не создан). Создать `MetaController` или адаптировать существующий X-Ray Brain | 2ч |
| 4.3 | X-Ray Pipeline Flow — визуализация | `frontend/src/pages/XRayPage.jsx` | 14 фаз pipeline. Показать: текущую фазу, время выполнения, статус (ok/warn/error). WebSocket для real-time | 2ч |
| 4.4 | MetaLearner — анализатор стратегий | `backend/core/xray/meta_learner.py` | Метод `analyze_patterns()` возвращает `{}`. Реализовать: кластеризацию стратегий по успешности, рекомендацию смены стратегии | 1ч |

---

## Фаза 5 — Knowledge Graph

~6ч

| # | Задача | Где | Что делать | Оценка |
|---|--------|-----|------------|--------|
| 5.1 | API роуты для Knowledge Graph | `backend/api/knowledge_routes.py` (создать) | CRUD: GET /knowledge/concepts, POST /knowledge/relations, GET /knowledge/search, DELETE /knowledge/concept/{id} | 2ч |
| 5.2 | UI визуализация графа | `frontend/src/pages/KnowledgePage.jsx` (создать) | Force-directed graph на D3.js или cytoscape.js. Отображать: узлы (концепты), рёбра (связи), поиск/фильтр. + вкладка в App.jsx | 3ч |
| 5.3 | Интеграция с pipeline | `backend/core/pipeline/executor.py` → `knowledge_graph.py` | После Semantic Phase — сохранять связи между извлечёнными концептами. Обогащение графа из диалогов | 1ч |

---

## Фаза 6 — Оптимизация

~2ч

| # | Задача | Где | Что делать | Оценка |
|---|--------|-----|------------|--------|
| 6.1 | Lazy import роутов | `backend/main.py` | Перенести `import frontend_routes` внутрь функции, а не на уровень модуля | 20мин |
| 6.2 | Ленивая инициализация RAG | `backend/memory/rag.py:__init__` | Не подключаться к PostgreSQL при старте, только при первом запросе | 15мин |
| 6.3 | React.lazy + Suspense | `frontend/src/App.jsx` | Все страницы грузить лениво: `const Page = React.lazy(() => import('./pages/...'))` | 30мин |
| 6.4 | Мемоизация WebSocket | `frontend/src/hooks/useWebSocket.js` | Не обновлять state, если данные не изменились (deep compare). Не ререндерить скрытые компоненты | 30мин |
| 6.5 | Убрать фоновые запросы | `frontend/src/App.jsx` | Компоненты на скрытых вкладках не должны делать API-запросы до первого показа | 15мин |

---

## Сводка

| Фаза | Часы | Суть |
|------|------|------|
| Фаза 1: Критические баги | ~1ч | FallbackGenerator, пустые `except`, миграция |
| Фаза 2: Заполнить заглушки | ~6ч | FallbackGenerator, MemoryInterface, HEALER, HealerBridge |
| Фаза 3: Допилить UI | ~7ч | Корзина, коллекции, feedback, настройки, memory dashboard |
| Фаза 4: X-Ray + MetaLearner | ~6ч | Dreams, MetaController, pipeline flow, анализатор |
| Фаза 5: Knowledge Graph | ~6ч | API + force-directed визуализация |
| Фаза 6: Оптимизация | ~2ч | Lazy imports, React.lazy, мемоизация |
| **Итого** | **~28ч** | |

Порядок важен: каждая фаза опирается на предыдущую.
