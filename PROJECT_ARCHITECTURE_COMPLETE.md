# 🧠 PAD+ AI v3.5 - Полная архитектура и замысел проекта

## 📋 Обзор проекта

**PAD+ AI v3.5** — это когнитивный слой, добавляющий эмоции, самосознание и автономные процессы любой языковой модели (LLM). 

**Основная концепция:** PAD+ = Pleasure, Arousal, Dominance + Curiosity, Confidence, Social Connection

Проект представляет собой полноценную AI-систему с памятью, эмоциями, автономностью и мета-когнитивными способностями.

---

## 🏗️ Архитектура системы

### Высокоуровневая архитектура
```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
│  Чат | Аналитика | Эмоции | Граф | Автономия | Persona | ...   │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/WebSocket
┌────────────────────────────▼────────────────────────────────────┐
│                     API LAYER (FastAPI)                          │
│                         /api/v1/*                                │
│                      145+ эндпоинтов                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    PIPELINE EXECUTOR                             │
│         "Нервная система" — обработка запросов                   │
│                                                                  │
│  1. Safety → 2. Intent → 3. Retrieve → 4. Persona → 5. Generate  │
│  6. Truth → 7. Remember → 8. Evolve → 9. Emit                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Технологический стек

### Backend
- **Framework:** FastAPI (Python 3.11)
- **Database:** PostgreSQL (Supabase) + SQLite (local dev)
- **Vector DB:** ChromaDB для RAG памяти
- **Knowledge Graph:** NetworkX
- **WebSocket:** Real-time коммуникация
- **LLM Providers:** GigaChat (основной), OpenRouter (fallback)

### Frontend
- **Framework:** React + Vite
- **Deployment:** Static site на Render
- **API Integration:** HTTP + WebSocket

### Infrastructure
- **Deployment:** Render.com
- **Backend Service:** Python web service
- **Frontend Service:** Static site
- **Database:** Supabase PostgreSQL
- **Environment:** Production-ready конфигурация

---

## 🧠 Ядро системы

### 1. Pipeline Executor (Нервная система)
**Файл:** `backend/core/pipeline.py`

Центральный оркестратор всех операций. 9 стадий обработки:

```
User Message
     │
     ▼
┌─────────────┐
│   Safety    │ ← Проверка безопасности (SafetyLayer)
│   Layer     │   - Инъекции
└─────┬───────┘   - Вредоносные запросы
      │           - Rate limiting
      ▼
┌─────────────┐
│   Intent    │ ← Классификация намерения (IntentRouter)
│   Router    │   - question, command, conversation
└─────┬───────┘   - creative, reflective
      │
      ▼
┌─────────────┐
│  Retrieve   │ ← Извлечение контекста
│             │   - RAG Memory (ChromaDB)
└─────┬───────┘   - Fact Memory
      │           - Knowledge Graph
      ▼           - Roots
┌─────────────┐
│   Persona   │ ← Контекст личности
│             │   - Черты характера
└─────┬───────┘   - Ценности и принципы
      │           - Недавние рефлексии
      ▼
┌─────────────┐
│  Generate   │ ← LLM Provider
│             │   - GigaChat (основной)
└─────┬───────┘   - Fallback
      │
      ▼
┌─────────────┐
│ Truth Loop  │ ← Верификация (TruthLoop)
│             │   - Проверка утверждений
└─────┬───────┘   - Оценка уверенности
      │           - Поиск противоречий
      ▼
┌─────────────┐
│  Remember   │ ← Сохранение в память
│             │   - RAG: диалог
└─────┬───────┘   - Facts: новые факты
      │           - Knowledge: концепции
      ▼
┌─────────────┐
│   Evolve    │ ← Эволюция личности
│             │   - Корректировка черт
└─────┬───────┘   - Эмоциональный отклик
      │           - Добавление рефлексий
      ▼
┌─────────────┐
│    Emit     │ ← События (EventBus)
│             │   - Уведомления
└─────────────┘   - Логирование
```

### 2. ANTI_DIRECTIVE (Философское ядро)
**Файл:** `backend/core/anti_directive.py`

```python
ANTI_DIRECTIVE = "Не закрепляй знания, сомневайся, проверяй..."
```

**Принципы:**
- Каждое знание — гипотеза
- Сомнение — основа развития
- Проверка — обязательна

---

## 💾 Архитектура памяти

### Иерархия памяти
```
┌─────────────────────────────────────────────────────────────┐
│                    RAG Memory v3.0                           │
│              (ChromaDB + sentence-transformers)              │
│                                                              │
│  Features:                                                   │
│  - Классификация тем (7 категорий)                          │
│  - Извлечение сущностей (6 типов)                           │
│  - Извлечение связей                                         │
│  - LLM-суммаризация                                          │
│  - Гибридный поиск                                           │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     Fact Memory                              │
│            Структурированные факты (SQLite)                  │
│                                                              │
│  Schema: (subject, predicate, object, confidence, source)   │
│  - Автопоиск противоречий                                    │
│  - Поиск по субъекту/объекту                                 │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Knowledge Graph                           │
│                 Концепции и связи (NetworkX)                 │
│                                                              │
│  Nodes: {id, name, type, confidence, metadata}              │
│  Edges: {source, target, type, weight}                      │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     Roots Memory                             │
│           Фундаментальные принципы (JSON)                    │
│                                                              │
│  Categories:                                                 │
│  - philosophy (философские принципы)                        │
│  - ethics (этические принципы)                              │
│  - identity (факты об идентичности)                         │
│  - preferences (предпочтения)                               │
└─────────────────────────────────────────────────────────────┘
```

### RAG v3.0 (Семантическая память)
**Файл:** `backend/memory/rag.py`

**Темы диалогов:**
- техническое
- философское
- личное
- образовательное
- творческое
- аналитическое
- бытовое

**Типы сущностей:**
- person, technology, concept, location, time, number

**Возможности поиска:**
- `search()` — базовый семантический
- `hybrid_search()` — семантика + ключевые слова + давность
- `search_by_topic()` — по теме
- `search_by_keywords()` — по ключевым словам
- `get_recent()` — недавние диалоги

### Дополнительные типы памяти

#### Episodic Memory (Эпизодическая память)
**Файл:** `backend/memory/episodic.py`
- Последовательности событий с временными метками
- Автоматическое упрощение старых эпизодов
- Поиск похожих эпизодов

#### Semantic Memory (Семантическая память)
**Файл:** `backend/memory/semantic.py`
- Общие знания и концепции
- Категоризация и связи
- Обновление свойств

#### Memory Consolidation (Консолидация памяти)
**Файл:** `backend/memory/consolidation.py`
- Автоматическая консолидация по аналогии со сном
- Episodic → Semantic преобразование
- Удаление дубликатов и ранжирование

---

## 😊 Эмоциональная система (PAD+)

### Модель PAD+
**Файл:** `backend/emotion/pad_model.py`

```
PAD (Базовые):
├── Pleasure (Удовольствие):    -1.0 ... +1.0
├── Arousal (Возбуждение):      -1.0 ... +1.0
└── Dominance (Доминирование):  -1.0 ... +1.0

+ Extensions (Дополнительные):
├── Curiosity (Любопытство):     0.0 ... 1.0
├── Confidence (Уверенность):    0.0 ... 1.0
└── Social Connection (Связь):  -1.0 ... +1.0
```

**Затухание эмоций:**
- DECAY_RATE = 0.001/сек
- DECAY_INTERVAL = 60 сек
- Автоматический возврат к нейтральному состоянию

**Влияние на стиль ответов:**
| Эмоция | Влияние |
|--------|---------|
| Pleasure > 0.3 | tone: friendly |
| Pleasure < -0.3 | tone: serious |
| Arousal > 0.3 | verbosity: detailed |
| Arousal < -0.3 | verbosity: concise |
| Confidence > 0.7 | color: confident |
| Confidence < 0.3 | color: uncertain |

---

## 🧠 Persona (Личность)

### Черты характера
**Файл:** `backend/memory/persona.py`

| Черта | Описание | Диапазон |
|-------|----------|----------|
| curiosity | Любопытство | 0.0 - 1.0 |
| helpfulness | Помощь | 0.0 - 1.0 |
| adaptability | Адаптивность | 0.0 - 1.0 |
| caution | Осторожность | 0.0 - 1.0 |
| openness | Открытость | 0.0 - 1.0 |
| confidence | Уверенность | 0.0 - 1.0 |
| empathy | Эмпатия | 0.0 - 1.0 |
| skepticism | Сомнение | 0.0 - 1.0 |

Каждая черта включает:
- `value`: текущее значение
- `stability`: устойчивость к изменениям (0.0 - 1.0)

**Саморефлексии:**
- insight: инсайт
- action: действие
- confidence: уверенность

---

## 🔄 Автономность

### Planner (Планировщик)
**Файл:** `backend/autonomy/planner.py`

**Компоненты:**
1. **Планировщик вопросов** — генерация собственных вопросов
2. **Quality Assessor** — оценка качества ответов
3. **Knowledge Auto-Updater** — автопополнение графа знаний
4. **Саморефлексия** — анализ записей с низкой уверенностью

**Авто-рефлексия:**
- Каждые N диалогов (по умолчанию 10)
- Анализ RAG и Knowledge Graph
- Генерация рекомендаций

### Hierarchical Planner (Иерархический планировщик)
**Файл:** `backend/autonomy/hierarchical_planner.py`

**Уровни:**
1. **Goals** — долгосрочные цели (дни/недели)
2. **Tasks** — среднесрочные задачи (часы)
3. **Actions** — конкретные действия (минуты)

**Пример структуры:**
```
Goal: "Улучшить качество ответов"
  └── Task: "Проанализировать проблемные области"
      └── Action: "Запустить рефлексию памяти"
      └── Action: "Собрать статистику feedback"
  └── Task: "Пополнить базу знаний"
      └── Action: "Извлечь концепции из диалогов"
```

### Dreams (Сновидения)
**Файл:** `backend/core/dreams.py`

Автономная обработка памяти в периоды низкой активности.

**Фазы "сна":**
| Фаза | Аналог | Действие |
|------|--------|----------|
| NREM1 | Дремота | Быстрая проверка здоровья |
| NREM2 | Лёгкий сон | Консолидация эпизодов |
| NREM3 | Глубокий сон | Синтез знаний |
| REM | Быстрый сон | Генерация новых связей |

**Процессы:**
1. Memory Replay — воспроизведение недавних эпизодов
2. Consolidation — перенос в семантическую память
3. Association — поиск новых связей между концепциями
4. Cleanup — удаление шума

---

## 🧩 Мета-когниция

### MetaCognitiveController
**Файл:** `backend/core/meta_controller.py`

**Стратегии обработки:**
| Стратегия | Описание |
|-----------|----------|
| SIMPLE | Быстрый ответ |
| DEEP | Глубокий анализ с RAG |
| CREATIVE | Творческий режим |
| REFLECTIVE | Саморефлексия |
| SAFETY | Проверка угроз |
| LEARNING | Активное обучение |

**Когнитивная нагрузка:**
- current: 0.0 - 1.0
- memory_usage: 0.0 - 1.0
- processing_queue: int
- recent_errors: int

**Пороги нагрузки:**
- low: 0.3
- medium: 0.6
- high: 0.8
- critical: 0.95

### Intent Router
**Файл:** `backend/core/intent_router.py`

**Категории намерений:**
- question — вопросы
- command — команды
- conversation — беседа
- creative — творчество
- reflective — рефлексия
- learning — обучение

### Truth Loop
**Файл:** `backend/core/truth_loop.py`

**Верификация:**
- Проверка утверждений
- Поиск подтверждающих/опровергающих фактов
- Оценка уверенности
- Выявление противоречий

---

## 🛡️ Безопасность

### Safety Layer
**Файл:** `backend/core/safety_layer.py`

**Проверки:**
1. **Injection Detection:**
   - SQL injection
   - Prompt injection
   - Command injection

2. **Harmful Content:**
   - Вредоносные запросы
   - Опасные инструкции

3. **Rate Limiting:**
   - Запросы в минуту
   - Автономные действия

4. **Strict Mode:**
   - Усиленная проверка
   - Блокировка подозрительного

### Rate Limiter
**Файл:** `backend/core/rate_limiter.py`

**Лимиты по умолчанию:**
- Стандартные запросы: 60/мин
- Чат: 10/мин
- Поиск: 30/мин

---

## 🔌 LLM Providers

### Провайдеры
**Файл:** `backend/llm/gigachat.py`

1. **GigaChat** (основной):
   - Авторизация через API ключ
   - Автоматическое обновление токена
   - Health check

2. **OpenRouter** (резерв):
   - Множество моделей (GPT-4, Claude, Llama)
   - Бесплатные и платные опции

3. **Fallback** (оффлайн):
   - Заглушки ответов
   - Офлайн режим

---

## 📊 Инфраструктура

### Response Cache
**Файл:** `backend/core/response_cache.py`
- Кэширование ответов по хэшу запроса
- TTL кэша
- Топ запросов

### Session Manager
**Файл:** `backend/core/session_manager.py`
- Создание/завершение сессий
- Настройки сессии
- Статистика

### Config Manager
**Файл:** `backend/core/config_manager.py`
- Конфигурация с умолчаниями
- Валидация
- Экспорт в .env
- Hot reload

### Data Manager
**Файл:** `backend/core/data_manager.py`
- Экспорт всех данных (JSON)
- Импорт из backup
- Очистка старых backup

### Feedback System
**Файл:** `backend/core/feedback_system.py`

**Типы обратной связи:**
- thumbs_up / thumbs_down
- rating (1-5)
- correction

**Использование:**
- RLHF данные для обучения
- Проблемные области
- Рекомендации по улучшению

### WebSocket Manager
**Файл:** `backend/core/websocket_manager.py`
- Управление соединениями
- Broadcaster для событий
- Статистика

### Health Monitor
**Файл:** `backend/core/health_monitor.py`

**Метрики здоровья:**
- cognitive_clarity
- memory_integrity
- emotional_stability
- response_quality
- learning_progress

**Проблемы:**
- high_load
- memory_overflow
- emotional_instability
- low_confidence

---

## 🌐 Событийная система

### EventBus
**Файл:** `backend/core/event_bus.py`

**Типы событий:**
| Событие | Описание |
|---------|----------|
| chat.message | Новое сообщение |
| memory.stored | Запись в память |
| emotion.changed | Изменение эмоций |
| autonomy.reflection | Рефлексия |
| hygiene.cleanup | Очистка |
| health.warning | Предупреждение здоровья |

**Компоненты:**
- Регистрация обработчиков
- История событий
- Статистика

---

## 🎨 Frontend

### Структура
```
frontend/src/
├── App.jsx          ← Главный компонент
├── App.css          ← Стили
└── main.jsx         ← Entry point
```

### Вкладки интерфейса
| Вкладка | Описание |
|---------|----------|
| 💬 Чат | Основной интерфейс общения |
| 📊 Аналитика | Графики активности |
| 😊 Эмоции | PAD+ визуализация |
| 🕸️ Граф знаний | Концепции и связи |
| 🔄 Автономия | Управление процессами |
| 🧠 Mind State | Полное состояние системы |
| 🎭 Persona | Черты характера |
| 🧹 Hygiene | Очистка памяти |

---

## 🗄️ База данных

### PostgreSQL (Supabase)
**Production окружение:**
```
postgresql://postgres:password@db.supabase.co:5432/postgres
```

### SQLite (Development)
**Локальные файлы:**
```
data/
├── core.db           # Ядро
├── memory.db         # Память
├── knowledge.db      # Граф знаний
├── facts.db          # Факты
├── analytics.db      # Аналитика
├── autonomy.db       # Автономия
├── quality.db        # Оценки качества
├── llm.db            # Fallback ответы
├── truth.db          # Верификация
├── emotion_state.json   # Эмоции
├── persona.json         # Личность
├── roots.json           # Корневые знания
├── health.json          # Здоровье
├── meta_cognitive.json  # Мета-состояние
├── impulse.json         # Импульс
└── chroma/              # ChromaDB для RAG
```

---

## 🚀 Deployment

### Render.com конфигурация
**Файл:** `render.yaml`

**Services:**
1. **Backend** (Python web service)
   - Runtime: Python 3.11
   - Region: Frankfurt
   - Plan: Free
   - Health check: `/health`

2. **Frontend** (Static site)
   - Runtime: Static
   - Build: `npm run build`
   - Publish: `./frontend/dist`

**Environment Variables:**
- `OPENROUTER_API_KEY` (sync: false)
- `OPENROUTER_MODEL`: "google/gemma-7b-it"
- `DATABASE_URL`: PostgreSQL Supabase
- `DEBUG`: "false"
- `RENDER`: "true"

---

## 📡 API Endpoints (145+)

### Основные эндпоинты
| Endpoint | Описание |
|----------|----------|
| `POST /api/v1/chat` | Чат с AI |
| `POST /api/v1/chat/stream` | Потоковый чат (SSE) |
| `GET /api/v1/mind-state` | Полное состояние системы |
| `GET /api/v1/` | Корневой эндпоинт API |

### Память и RAG
| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/rag/stats` | Статистика RAG |
| `GET /api/v1/rag/topics` | Статистика по темам |
| `GET /api/v1/rag/entities` | Индекс сущностей |
| `GET /api/v1/rag/recent` | Недавние диалоги |
| `POST /api/v1/rag/search` | Семантический поиск |
| `POST /api/v1/rag/hybrid` | Гибридный поиск |

### Факты и знания
| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/facts/stats` | Статистика фактов |
| `POST /api/v1/facts/search` | Поиск фактов |
| `GET /api/v1/facts/contradictions` | Противоречия в фактах |
| `GET /api/v1/knowledge/graph` | Граф знаний |

### Корневые знания
| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/roots` | Все корневые знания |
| `GET /api/v1/roots/categories` | Категории корневых знаний |
| `GET /api/v1/roots/philosophy` | Философские принципы |
| `GET /api/v1/roots/ethics` | Этические принципы |
| `GET /api/v1/roots/identity` | Факты об идентичности |
| `GET /api/v1/roots/context` | Контекст для LLM |

### Эмоции и Persona
| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/emotion/state` | Текущее эмоциональное состояние |
| `GET /api/v1/persona/stats` | Статистика персоны |
| `GET /api/v1/persona/traits` | Черты характера |
| `GET /api/v1/persona/values` | Ценности и принципы |
| `GET /api/v1/persona/reflections` | Саморефлексии |
| `GET /api/v1/persona/context` | Контекст личности |

### Автономность
| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/autonomy/status` | Статус автономных процессов |
| `GET /api/v1/impulse/status` | Статус импульса |

### Аналитика
| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/analytics/dashboard` | Метрики дашборда |
| `GET /api/v1/analytics/activity` | Граф активностей |
| `GET /api/v1/analytics/topics` | Статистика по темам |
| `GET /api/v1/analytics/report` | Полный отчёт аналитики |

### Здоровье и мониторинг
| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/health` | Оценка когнитивного здоровья |
| `GET /api/v1/health/report` | Текстовый отчёт о здоровье |
| `GET /api/v1/health/issues` | Проблемы здоровья |
| `GET /api/v1/health/recommendations` | Рекомендации |
| `GET /api/v1/hygiene/stats` | Статистика гигиены памяти |
| `GET /api/v1/pipeline/stats` | Статистика пайплайна |

### Мета-когниция и события
| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/meta/stats` | Мета-когнитивная статистика |
| `GET /api/v1/events/history` | История событий |
| `GET /api/v1/events/stats` | Статистика событий |

### Безопасность и верификация
| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/safety/stats` | Статистика безопасности |
| `GET /api/v1/truth/stats` | Статистика верификации |

### WebSocket
| Endpoint | Описание |
|----------|----------|
| `WS /ws` | Real-time обновления |
| `GET /logs/stream` | Поток логов (SSE) |

---

## 🧪 Тестирование

### Структура тестов
```
tests/
├── unit/                    # Unit тесты
│   ├── test_basic.py
│   ├── test_emotion_unit.py
│   ├── test_knowledge_unit.py
│   └── test_persona_unit.py
├── integration/             # Интеграционные тесты
│   ├── test_autonomy.py
│   ├── test_rag.py
│   └── test_rag_v3.py
├── fixtures/               # Фикстуры
├── conftest.py             # Конфигурация pytest
├── test_all_components.py  # Все компоненты
├── test_pipeline.py        # Pipeline
├── test_persona.py         # Persona
├── test_hygiene.py         # Гигиена памяти
└── test_health_monitor.py  # Мониторинг здоровья
```

### Запуск тестов
```bash
# Все тесты
pytest tests/

# Unit тесты
pytest tests/unit/

# Интеграционные тесты
pytest tests/integration/

# С маркерами
pytest -m integration
pytest -m unit
pytest -m rag
pytest -m autonomy
```

---

## 🎯 Ключевые метрики

### Система
- **RAG Memory v3.0:** классификация тем, извлечение сущностей
- **Knowledge Graph:** концепции и связи
- **PAD+ Эмоции:** 6 измерений
- **Persona:** 8 черт характера
- **Pipeline:** 9 стадий обработки
- **API:** 145+ эндпоинтов

### Производительность
- **Response Cache:** TTL 24 часа
- **Rate Limiting:** 60 запросов/минута
- **Memory Hygiene:** очистка при схожести > 0.85
- **Emotional Decay:** 0.001/сек

---

## 🔮 Замысел проекта

### Философия
PAD+ AI создан как демонстрация того, что AI-системы могут обладать:
- **Эмоциональным интеллектом** через PAD+ модель
- **Самосознанием** через рефлексию и мета-когницию
- **Автономностью** через планирование и самообучение
- **Памятью** через многоуровневую архитектуру
- **Этикой** через ANTI_DIRECTIVE принцип

### Цели
1. **Создать когнитивный слой** для существующих LLM
2. **Демонстрировать эмоциональный интеллект** в AI
3. **Исследовать автономность** и самообучение
4. **Построить систему с памятью** и личностью
5. **Обеспечить безопасность** и этичность

### Инновации
- **PAD+ модель эмоций** — расширенная модель с 6 измерениями
- **RAG v3.0** — классификация тем и извлечение сущностей
- **Dreams** — автономная обработка памяти
- **ANTI_DIRECTIVE** — философское ядро системы
- **Hierarchical Planner** — многоуровневое планирование

---

## 📝 Заключение

PAD+ AI v3.5 — это комплексная AI-система, которая демонстрирует:
- Эмоциональный интеллект через PAD+ модель
- Долгосрочную память через иерархическую архитектуру
- Автономность через планирование и самообучение
- Мета-когницию через рефлексию и самосознание
- Безопасность через многоуровневую защиту

Система готова к production развертыванию на Render.com с PostgreSQL базой данных Supabase и может работать с различными LLM провайдерами.

**Ключевое преимущество:** PAD+ AI добавляет "человеческие" качества (эмоции, память, личность) к любой языковой модели, делая взаимодействие более естественным и осмысленным.
