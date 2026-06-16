# 📁 Структура проекта PAD+ AI

**Версия:** 2.1  
**Последнее обновление:** Декабрь 2024
**Статус:** ✅ Актуально

---

## Обзор

```
PAD+ AI/
├── backend/                    # Python backend (FastAPI)
├── frontend/                   # React frontend (Vite)
├── docs/                       # Документация
├── tests/                      # Тесты
├── scripts/                    # Вспомогательные скрипты
├── data/                       # Локальные данные (SQLite, JSON)
└── experiments/                # Эксперименты и исследования
```

---

## Backend (`backend/`)

```
backend/
├── main.py                     # Точка входа FastAPI
├── api/                        # API маршруты
│   ├── frontend_routes.py      # Основные эндпоинты (чат, ключи, провайдеры)
│   ├── dialog_routes.py        # История диалогов
│   ├── rag_routes.py           # RAG память
│   ├── episodic_routes.py      # Эпизодическая память
│   ├── semantic_routes.py      # Семантическая память
│   ├── knowledge_routes.py     # Граф знаний
│   ├── emotion_routes.py       # Эмоции (PAD+)
│   ├── autonomy_routes.py      # Автономные процессы
│   ├── dreams_routes.py        # Сновидения
│   ├── consolidation_routes.py # Консолидация памяти
│   ├── persona_routes.py       # Персона
│   ├── pipeline_routes.py      # Pipeline статистика
│   ├── hygiene_routes.py       # Гигиена памяти
│   ├── safety_routes.py        # Безопасность
│   ├── truth_routes.py         # Truth Loop
│   ├── events_routes.py        # События
│   ├── health_routes.py        # Health check
│   ├── analytics_routes.py     # Аналитика
│   ├── cache_routes.py         # Кэш
│   ├── feedback_routes.py      # Обратная связь
│   ├── config_routes.py        # Конфигурация
│   └── safe_endpoint.py        # Декоратор безопасных эндпоинтов
├── core/                       # Ядро системы
│   ├── pipeline/               # Pipeline_executor и фазы
│   │   ├── executor.py         # PipelineExecutor v4.0
│   │   ├── context.py          # PipelineContext
│   │   ├── models.py           # PipelineResult, PhaseResult
│   │   ├── base.py             # Базовый класс PipelinePhase
│   │   └── phases/             # Фазы pipeline
│   │       ├── safety.py
│   │       ├── intent.py
│   │       ├── rag.py
│   │       ├── knowledge_graph.py
│   │       ├── episodic.py
│   │       ├── semantic.py
│   │       ├── emotion.py
│   │       ├── emotion_update.py
│   │       ├── identity.py
│   │       ├── persona.py
│   │       ├── roots.py
│   │       ├── generate.py
│   │       ├── truth_loop.py
│   │       ├── save_episode.py
│   │       ├── persona_evolution.py
│   │       ├── events_broadcast.py
│   │       ├── health.py
│   │       ├── reflection.py
│   │       ├── dreams.py
│   │       ├── metrics.py
│   │       └── response_guard.py
│   ├── xray/                   # X-Ray система наблюдаемости
│   │   ├── trace_collector.py  # Сбор trace событий
│   │   ├── broadcaster.py      # WebSocket broadcaster
│   │   ├── thought_visualizer.py # Визуализация мыслей
│   │   ├── healing_detectors.py # Детекторы проблем
│   │   ├── meta_learner.py     # MetaLearner (адаптация стратегий)
│   │   └── reflection.py       # ReflectionLoop
│   ├── guard/                  # Response Guard
│   │   ├── response_guard.py   # Очистка ответов
│   │   ├── self_healing.py     # Self-Healing Guard
│   │   ├── tone_engine.py      # Tone Engine
│   │   └── cognitive_layer.py  # Cognitive Layer
│   ├── experience/             # Experience Layer
│   │   ├── experience.py       # Capture experience
│   │   └── extractor.py        # ExperienceExtractor
│   ├── safety_layer.py         # Safety Layer (безопасность)
│   ├── intent_router.py        # Intent Router (классификация)
│   ├── pipeline_helpers.py     # Helper-функции pipeline
│   ├── anti_loop.py            # Anti-Loop Guard
│   ├── config_manager.py       # Конфигурация
│   ├── cache_manager.py        # Cache Manager (L1/L2)
│   ├── supabase_client.py      # Supabase клиент
│   ├── dependencies.py         # FastAPI зависимости
│   └── exceptions.py           # Исключения
├── memory/                     # Системы памяти
│   ├── base.py                 # MemoryInterface (базовый класс)
│   ├── rag.py                  # RAG v3.0 (pgvector)
│   ├── episodic.py             # Эпизодическая память (SQLite)
│   ├── semantic.py             # Семантическая память (SQLite)
│   ├── facts.py                # Факты (SQLite)
│   ├── roots.py                # Roots (JSON)
│   ├── persona.py              # Персона (SQLite)
│   ├── knowledge_graph.py      # Граф знаний (SQLite)
│   ├── consolidation.py        # Консолидация памяти
│   └── hygiene.py              # Гигиена памяти
├── emotion/                    # Эмоциональная модель
│   ├── pad_model.py            # PAD+ модель (6 измерений)
│   └── style_generator.py      # Генерация стиля ответа
├── runtime/                    # Provider Management
│   ├── provider_manager.py     # ProviderManager (fallback-цепочки)
│   ├── llm_service.py          # LLMService (единый интерфейс)
│   └── gigachat_client.py      # GigaChat SDK
├── autonomy/                   # Автономные процессы
│   ├── planner.py              # Планировщик задач
│   ├── quality_monitor.py      # Мониторинг качества
│   └── scheduler.py            # Планировщик расписаний
├── scripts/                    # Скрипты
│   ├── impulse.py              # Impulse Core
│   └── apply_migrations.py     # Применение миграций БД
├── database/                   # База данных
│   └── migrations/             # SQL миграции (29 файлов)
└── core/impulse/               # Impulse Core (вопросы)
    └── impulse_core.py         # ImpulseCore (6 измерений)
```

---

## Frontend (`frontend/`)

```
frontend/
├── src/
│   ├── main.jsx                # Точка входа React
│   ├── App.jsx                 # Корневой компонент
│   ├── pages/                  # Страницы
│   │   ├── ChatPage.jsx        # Чат
│   │   ├── ProvidersPage.jsx   # Провайдеры
│   │   ├── SettingsPage.jsx    # Настройки
│   │   ├── HistoryPage.jsx     # История диалогов
│   │   ├── DocumentsPage.jsx   # Документы
│   │   ├── XRayPage.jsx        # X-Ray трассировка
│   │   ├── KnowledgePage.jsx   # Граф знаний
│   │   ├── MemoryPage.jsx      # Память
│   │   ├── EmotionPage.jsx     # Эмоции
│   │   ├── AutonomyPage.jsx    # Автономность
│   │   └── AnalyticsPage.jsx   # Аналитика
│   ├── components/             # Компоненты
│   │   ├── chat/               # Компоненты чата
│   │   ├── providers/          # Компоненты провайдеров
│   │   ├── xray/               # X-Ray компоненты
│   │   ├── knowledge/          # Граф знаний
│   │   └── memory/             # Память
│   ├── services/               # API сервисы
│   │   ├── api.js              # Axios instance
│   │   ├── chatService.js      # Чат API
│   │   ├── providersService.js # Провайдеры API
│   │   └── ...
│   ├── hooks/                  # React hooks
│   │   ├── useChat.js          # Хук чата
│   │   ├── useProviders.js     # Хук провайдеров
│   │   └── ...
│   └── utils/                  # Утилиты
├── public/                     # Статические файлы
├── package.json                # Зависимости npm
└── vite.config.js              # Конфиг Vite
```

---

## Тесты (`tests/`)

```
tests/
├── conftest.py                 # pytest fixtures
├── pytest.ini                  # pytest конфигурация
├── test_providers.py           # ProviderManager тесты (44 теста)
├── test_pipeline.py            # Pipeline тесты
├── test_all_components.py      # Все компоненты (7 тестов)
├── test_api_endpoints.py       # API эндпоинты (2 теста)
├── test_key_status_cache.py    # Кэш статусов ключей (9 тестов)
├── test_dialog_routes.py       # Dialog routes (3 теста)
├── test_hygiene.py             # Hygiene (1 тест)
├── test_anti_directive.py      # Anti-Directive (9 тестов)
├── test_gigachat_client.py     # GigaChat SDK (16 тестов)
├── test_memory_consolidation.py # Консолидация (10 тестов)
├── test_impulse_core.py        # Impulse Core (33 теста)
├── test_persona.py             # Персона
├── test_emotion.py             # Эмоции
├── hardening/                  # Hardening тесты (225 тестов)
│   ├── test_cache_manager.py
│   ├── test_csrf_middleware.py
│   ├── test_db_circuit_breaker.py
│   ├── test_exceptions.py
│   ├── test_input_sanitizer.py
│   ├── test_logging_config.py
│   ├── test_metrics_collector.py
│   ├── test_pipeline_helpers.py
│   └── test_response_guard_v2.py
├── test_pipeline/              # Pipeline фазы (49 тестов)
│   ├── test_anti_loop.py
│   ├── test_dreams.py
│   ├── test_emotion.py
│   ├── test_emotion_update.py
│   ├── test_episodic.py
│   ├── test_events.py
│   ├── test_health.py
│   ├── test_intent.py
│   ├── test_knowledge_graph.py
│   ├── test_metrics.py
│   ├── test_orchestrator.py
│   ├── test_persona.py
│   ├── test_persona_evolution.py
│   ├── test_rag.py
│   ├── test_reflection.py
│   ├── test_response_guard.py
│   ├── test_roots.py
│   ├── test_safety.py
│   ├── test_save_episode.py
│   ├── test_semantic.py
│   └── test_truth_loop.py
├── test_xray/                  # X-Ray тесты (14 тестов)
│   ├── test_healing_detectors.py
│   ├── test_pipeline_monolith.py
│   └── test_pipeline_scenarios.py
├── optimization_tests/         # Оптимизация
│   ├── test_caching.py
│   ├── test_fast_slow_requests.py
│   └── test_health_checks.py
├── integration/                # Интеграционные тесты
│   ├── test_autonomy.py
│   ├── test_rag.py
│   └── test_rag_v3.py
├── moved_from_root/            # Перенесённые из корня
└── tmp/                        # Временные файлы тестов
```

---

## Документация (`docs/`)

```
docs/
├── README.md                   # Индекс документации
├── ARCHITECTURE.md             # Архитектура системы
├── API.md                      # API спецификация (28 разделов)
├── DEPLOYMENT.md               # Руководство по деплою
├── XRAY.md                     # X-Ray система
├── XRAY_GUIDE.md               # Руководство по X-Ray
├── AUDIT_REPORT.md             # Аудит безопасности
├── STABILIZATION_PLAN.md       # План стабилизации
├── PROJECT_STRUCTURE.md        # Этот файл
├── impulse/                    # Impulse Core документация
│   ├── IMPULSE_CORE.md
│   ├── IMPULSE_API.md
│   └── IMPULSE_ARCHITECTURE.md
├── architecture/               # Детальная архитектура
│   ├── OVERVIEW.md
│   ├── PIPELINE.md
│   ├── MEMORY_SYSTEM.md
│   ├── EMOTION_SYSTEM.md
│   └── META_SYSTEM.md
└── archive/legacy/             # 77 устаревших файлов
```

---

## Скрипты (`scripts/`)

```
scripts/
├── apply_migrations.py         # Применение миграций БД
├── impulse.py                  # Impulse Core CLI
├── cleanup_*.py                # Очистители
└── migration_*.py              # Миграционные скрипты
```

---

## Данные (`data/`)

```
data/
├── *.json                      # Состояния (эмоции, persona, roots, impulse)
├── *.db                        # SQLite базы (episodic, semantic, facts, persona)
└── chroma/                     # ChromaDB (RAG векторы)
```

---

## Эксперименты (`experiments/`)

```
experiments/
├── I-002/                      # Эксперимент I-002
│   ├── HYPOTHESIS.md
│   └── REPORT.md
├── I-003/                      # Эксперимент I-003
│   ├── HYPOTHESIS.md
│   └── REPORT.md
├── I-004/                      # Эксперимент I-004
│   ├── HYPOTHESIS.md
│   └── REPORT.md
├── I-005/                      # Эксперимент I-005
│   ├── HYPOTHESIS.md
│   └── REPORT.md
├── RESEARCH_PACKAGE.md         # Исследовательский пакет
└── researches.md               # Исследования
```

---

## Ключевые файлы

| Файл | Описание | Строк |
|------|----------|-------|
| `backend/main.py` | Точка входа FastAPI | ~200 |
| `backend/api/frontend_routes.py` | Основные эндпоинты | ~1200 |
| `backend/core/pipeline/executor.py` | PipelineExecutor v4.0 | ~500 |
| `backend/runtime/provider_manager.py` | ProviderManager + fallback | ~400 |
| `backend/memory/rag.py` | RAG v3.0 (pgvector) | ~350 |
| `backend/emotion/pad_model.py` | PAD+ модель (6 измерений) | ~200 |
| `frontend/src/App.jsx` | Корневой компонент React | ~300 |
| `frontend/src/pages/ChatPage.jsx` | Страница чата | ~400 |

---

## Статистика проекта

| Метрика | Значение |
|---------|----------|
| **Backend файлов** | 100+ |
| **Frontend файлов** | 50+ |
| **Тестов** | 400+ |
| **Эндпоинтов** | 130+ |
| **Строк кода (backend)** | ~15,000 |
| **Строк кода (frontend)** | ~8,000 |
| **Строк тестов** | ~5,000 |
| **Строк документации** | ~3,000 |

---

## Зависимости

### Backend (Python)

```
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.0.0
supabase>=2.0.0
asyncpg>=0.29.0
redis>=5.0.0
openai>=1.0.0
anthropic>=0.18.0
google-generativeai>=0.3.0
groq>=0.4.0
aiohttp>=3.9.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
gunicorn>=21.0.0
```

### Frontend (Node.js)

```
react>=18.2.0
react-dom>=18.2.0
vite>=5.0.0
axios>=1.6.0
@supabase/supabase-js>=2.39.0
tailwindcss>=3.4.0
recharts>=2.10.0
d3>=7.8.0
```

---

## Архитектурные принципы

1. **Модульность** — каждый компонент изолирован
2. **Наблюдаемость** — X-Ray трассировка всех фаз
3. **Отказоустойчивость** — fallback-цепочки, circuit breakers
4. **Безопасность** — валидация, санитизация, шифрование
5. **Тестируемость** — 400+ тестов, coverage >70%
6. **Документированность** — 8 основных файлов + архив
