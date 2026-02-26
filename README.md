# 🧠 PAD+ AI v3.5

**Когнитивный слой, добавляющий эмоции и самосознание любому LLM.**

*PAD+ = Pleasure, Arousal, Dominance + Curiosity, Confidence, Social Connection*

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## ✨ Возможности

### 💬 Коммуникация
- **Чат** — интеллектуальные диалоги с RAG v3.0
- **Потоковый чат** — SSE streaming ответов
- **WebSocket** — real-time коммуникация

### 🧠 Память
- **RAG Memory v3.0** — семантическая память с ChromaDB
  - Классификация тем диалогов
  - Извлечение сущностей и связей
  - Гибридный поиск с ранжированием
  - LLM-суммаризация
- **Episodic Memory** — эпизодическая память с временными метками
- **Semantic Memory** — общие знания и концепции
- **Fact Memory** — структурированные факты (subject-predicate-object)
- **Roots Memory** — фундаментальные принципы (философия, этика, идентичность)
- **Persona** — развивающаяся личность с чертами характера
- **Hygiene** — автоматическая очистка памяти
- **Consolidation** — консолидация памяти по аналогии со сном

### 😊 Эмоции
- **PAD+ Модель** — 6 измерений:
  - Удовольствие, Возбуждение, Доминирование
  - Любопытство, Уверенность, Социальная связь
- Автоматическое затухание эмоций
- Влияние на стиль общения

### 🔄 Автономность
- **Планировщик** — самостоятельные вопросы и задачи
- **Иерархический планировщик** — многоуровневые цели (Goals → Tasks → Actions)
- **Dreams** — "сновидения" для обработки памяти в периоды покоя
- **Авто-рефлексия** — каждые N диалогов
- **Quality Assessor** — самооценка качества ответов
- **Knowledge Auto-Updater** — автопополнение графа знаний

### 🛡️ Безопасность
- **Safety Layer** — защита от инъекций
- **Anti-Loop Guard** — защита от зацикливаний
- **Rate Limiter** — ограничение запросов

### 🧩 Мета-когниция
- **Meta Controller** — управление стратегиями обработки
- **Intent Router** — классификация намерений
- **Truth Loop** — верификация утверждений
- **Health Monitor** — когнитивное здоровье
- **Cognitive Load** — оценка нагрузки

### 📊 Аналитика
- **Metrics** — метрики использования
- **Dashboard** — визуализация активности
- **Feedback System** — система обратной связи (RLHF)

### ⚙️ Инфраструктура
- **Response Cache** — умное кэширование ответов
- **Session Manager** — управление сессиями
- **Config Manager** — конфигурация системы
- **Data Manager** — экспорт/импорт данных
- **Event Bus** — событийная система

## 🚀 Быстрый старт

### Требования

- Python 3.10+
- Node.js 16+
- OpenRouter API ключ (опционально, для LLM)

### Установка

```bash
# Клонирование
git clone https://github.com/your-username/padplus-ai.git
cd padplus-ai

# Backend
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Конфигурация
cp .env.example .env
# Отредактируйте .env
```

### Запуск

```bash
# Windows
start.bat

# Или вручную:
# Terminal 1 — Backend
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend  
cd frontend && npm run dev
```

Откройте http://localhost:5173

## 📁 Структура проекта

```
padplus-ai/
├── backend/
│   ├── core/               # Ядро системы
│   │   ├── pipeline.py         # Pipeline Executor (9 стадий)
│   │   ├── safety_layer.py     # Защита от атак
│   │   ├── anti_directive.py   # Философское ядро
│   │   ├── intent_router.py    # Классификация намерений
│   │   ├── truth_loop.py       # Верификация
│   │   ├── event_bus.py        # Событийная система
│   │   ├── health_monitor.py   # Когнитивное здоровье
│   │   ├── meta_controller.py  # Мета-когнитивный контроллер
│   │   ├── dreams.py           # Сновидения (автообработка)
│   │   ├── response_cache.py   # Кэширование
│   │   ├── websocket_manager.py# WebSocket
│   │   ├── data_manager.py     # Управление данными
│   │   ├── feedback_system.py  # Обратная связь
│   │   ├── rate_limiter.py     # Rate Limiting
│   │   ├── session_manager.py  # Сессии
│   │   └── config_manager.py   # Конфигурация
│   │
│   ├── memory/             # Память
│   │   ├── rag.py              # RAG v3.0 (ChromaDB)
│   │   ├── episodic.py         # Эпизодическая память
│   │   ├── semantic.py         # Семантическая память
│   │   ├── consolidation.py    # Консолидация памяти
│   │   ├── fact_memory.py      # Факты
│   │   ├── roots.py            # Корневые знания
│   │   ├── persona.py          # Личность
│   │   ├── hygiene.py          # Гигиена памяти
│   │   ├── smartcache.py       # Временный кэш
│   │   └── vectormemory.py     # Векторная память
│   │
│   ├── emotion/            # Эмоции
│   │   └── pad_model.py        # PAD+ модель
│   │
│   ├── llm/                # LLM провайдеры
│   │   ├── gigachat.py         # GigaChat (Сбер)
│   │   └── provider_manager.py # Управление провайдерами
│   │
│   ├── knowledge/          # Граф знаний
│   │   └── graph.py            # NetworkX граф
│   │
│   ├── autonomy/           # Автономность
│   │   ├── planner.py          # Планировщик + Рефлексия
│   │   └── hierarchical_planner.py # Иерархические цели
│   │
│   ├── analytics/          # Аналитика
│   │   └── metrics.py          # Метрики
│   │
│   ├── api/                # API
│   │   └── routes.py           # FastAPI роуты (80+ эндпоинтов)
│   │
│   └── main.py             # Entry point
│
├── frontend/               # React Frontend
│   └── src/
│       ├── App.jsx             # Главный компонент
│       └── App.css             # Стили
│
├── tests/                  # Тесты
│   ├── test_all.py
│   ├── test_pipeline.py
│   ├── test_persona.py
│   ├── test_hygiene.py
│   ├── test_health_monitor.py
│   ├── test_meta_controller.py
│   ├── test_roots.py
│   └── ...
│
├── docs/                   # Документация
│   ├── API.md
│   ├── ARCHITECTURE.md
│   └── EVOLUTION.md
│
├── scripts/                # Утилиты
│   └── impulse.py              # Инициализация импульса
│
├── data/                   # Данные (SQLite, JSON, ChromaDB)
├── start.bat               # Запуск
└── stop.bat                # Остановка
```

## 🔧 Конфигурация

### .env

```env
# LLM провайдеры (выберите один)
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_ENABLED=true

# GigaChat (альтернатива)
GIGACHAT_API_KEY=your_gigachat_key
GIGACHAT_ENABLED=false

# Safety
SAFETY_STRICT_MODE=false
MAX_REQUESTS_PER_MINUTE=60

# Memory
RAG_MAX_ITEMS=10000
HYGIENE_SIMILARITY_THRESHOLD=0.85
```

### OpenRouter

[OpenRouter](https://openrouter.ai/) предоставляет доступ к множеству LLM моделей:
- Бесплатные: `google/gemma-7b-it`, `meta-llama/llama-3-8b-instruct`
- Платные: `openai/gpt-4`, `anthropic/claude-3`

Получите API ключ на [openrouter.ai/keys](https://openrouter.ai/keys)

## 📚 Документация

- [API.md](docs/API.md) — спецификация API (80+ эндпоинтов)
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — архитектура системы
- [EVOLUTION.md](docs/EVOLUTION.md) — история развития

## 🧪 Тестирование

```bash
# Все тесты
python -m pytest tests/

# Отдельные модули
python tests/test_all.py
python tests/test_pipeline.py
python tests/test_persona.py
python tests/test_hygiene.py
python tests/test_health_monitor.py
python tests/test_meta_controller.py
python tests/test_roots.py
```

## 🔌 API Endpoints (80+)

### Основные
| Endpoint | Описание |
|----------|----------|
| `POST /api/v1/chat` | Чат |
| `POST /api/v1/chat/stream` | Потоковый чат (SSE) |
| `GET /api/v1/mind-state` | Полное состояние системы |

### Память
| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/rag/stats` | Статистика RAG |
| `POST /api/v1/rag/search` | Семантический поиск |
| `POST /api/v1/rag/hybrid` | Гибридный поиск |
| `GET /api/v1/facts/stats` | Статистика фактов |
| `POST /api/v1/facts/search` | Поиск фактов |
| `GET /api/v1/roots` | Корневые знания |

### Эмоции и Persona
| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/emotion/state` | Эмоции PAD+ |
| `GET /api/v1/persona/traits` | Черты характера |
| `POST /api/v1/persona/adjust` | Корректировка черты |

### Автономность
| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/autonomy/status` | Статус автономии |
| `POST /api/v1/autonomy/reflect` | Саморефлексия |
| `GET /api/v1/meta/stats` | Мета-когниция |

### Аналитика и Здоровье
| Endpoint | Описание |
|----------|----------|
| `GET /api/v1/analytics/report` | Аналитика |
| `GET /api/v1/health` | Когнитивное здоровье |
| `POST /api/v1/feedback` | Обратная связь |

Полная документация: http://localhost:8000/docs

## 🏗️ Архитектура

```
User Message
     │
     ▼
┌─────────────┐
│   Safety    │ ← Проверка безопасности
└─────┬───────┘
      ▼
┌─────────────┐
│   Intent    │ ← Классификация намерения
└─────┬───────┘
      ▼
┌─────────────┐
│  Retrieve   │ ← RAG + Facts + Knowledge Graph
└─────┬───────┘
      ▼
┌─────────────┐
│   Persona   │ ← Контекст личности
└─────┬───────┘
      ▼
┌─────────────┐
│  Generate   │ ← LLM Provider
└─────┬───────┘
      ▼
┌─────────────┐
│   Truth     │ ← Верификация
└─────┬───────┘
      ▼
┌─────────────┐
│  Remember   │ ← Сохранение в память
└─────┬───────┘
      ▼
┌─────────────┐
│   Emit      │ ← События
└─────────────┘
```

## 🧬 ANTI_DIRECTIVE

Философское ядро системы:

> *"Не закрепляй знания, сомневайся, проверяй. Каждое утверждение — гипотеза."*

## 📊 Метрики

- **RAG Memory v3.0:** классификация тем, извлечение сущностей
- **Knowledge Graph:** концепции и связи
- **PAD+ Эмоции:** 6 измерений
- **Persona:** 8 черт характера
- **Pipeline:** 9 стадий обработки
- **API:** 80+ эндпоинтов

## 🤝 Вклад

1. Fork репозитория
2. Создайте ветку (`git checkout -b feature/amazing`)
3. Commit (`git commit -m 'Add amazing'`)
4. Push (`git push origin feature/amazing`)
5. Откройте Pull Request

## 📄 Лицензия

Apache License 2.0 — см. [LICENSE](LICENSE)

---

**PAD+ AI v3.5** — *Когнитивный слой, добавляющий эмоции и самосознание любому LLM.*
