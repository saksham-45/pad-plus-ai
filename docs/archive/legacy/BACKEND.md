# ⚙️ Backend — PAD+ AI v4.0

## Обзор

Backend реализован на **Python 3.14** с использованием **FastAPI**. Порт: `8080`.

## Структура проекта

```
backend/
├── main.py                        # Entry point (FastAPI app, lifespan, CORS)
│
├── api/
│   ├── routes.py                  # Основные API роуты
│   └── frontend_routes.py         # Роуты для фронтенда (Auth, Keys, Chat, Providers)
│
├── core/                          # Ядро системы
│   ├── anti_directive.py          # Философское ядро
│   ├── async_http_client.py       # Асинхронный HTTP клиент
│   ├── cache_manager.py           # Кэширование (Redis + in-memory)
│   ├── cache_manager.py           # Кэширование (Redis + in-memory)
│   ├── cognitive_metrics.py       # Когнитивные метрики
│   ├── config_manager.py          # Управление конфигурацией
│   ├── data_manager.py            # Управление данными
│   ├── dependencies.py            # Dependency Injection (16 зависимостей)
│   ├── dreams.py                  # Сновидения
│   ├── encryption.py              # Шифрование API ключей (Fernet)
│   ├── event_bus.py               # Событийная система
│   ├── fallback_generator.py      # Fallback генерация
│   ├── feedback_system.py         # Система обратной связи
│   ├── health_monitor.py          # Мониторинг здоровья
│   ├── intent_router.py           # Классификация намерений
│   ├── logging_config.py          # Настройка логирования
│   ├── meta_controller.py         # Мета-когнитивный контроллер
│   ├── metrics.py                 # Метрики
│   ├── monitoring.py              # Мониторинг
│   ├── pipeline.py                # Pipeline Executor
│   ├── pipeline_handlers.py       # Обработчики пайплайна
│   ├── rate_limiter.py            # Rate Limiting
│   ├── response_cache.py          # Кэш ответов
│   ├── safety_layer.py            # Безопасность
│   ├── session_manager.py         # Управление сессиями
│   ├── style_manager.py           # Управление стилем ответов
│   ├── supabase_client.py         # Supabase клиент
│   ├── truth_loop.py              # Верификация
│   └── websocket_manager.py       # WebSocket менеджер
│
├── memory/                        # Подсистема памяти
│   ├── consolidation.py           # Консолидация памяти
│   ├── episodic.py                # Эпизодическая память
│   ├── fact_memory.py             # Факты (SQLite)
│   ├── hygiene.py                 # Гигиена памяти
│   ├── persona.py                 # Личность
│   ├── rag.py                     # RAG v3.0 (PostgreSQL/pgvector)
│   ├── roots.py                   # Корневые знания
│   ├── semantic.py                # Семантическая память
│   ├── smartcache.py              # Временный кэш
│   ├── user_persona.py            # Персона пользователя
│
├── emotion/                       # Эмоции
│   ├── pad_model.py               # PAD+ модель (6 измерений)
│   └── async_pad_model.py         # Асинхронная PAD модель
│
├── knowledge/                     # Граф знаний
│   └── graph.py                   # NetworkX граф
│
├── autonomy/                      # Автономность
│   ├── planner.py                 # Планировщик + рефлексия
│   └── hierarchical_planner.py    # Иерархический планировщик
│
├── analytics/                     # Аналитика
│   └── metrics.py                 # Метрики
│
├── runtime/                       # Runtime сервисы
│   └── litellm_service.py         # LiteLLM сервис (20+ провайдеров)
│
├── database/migrations/           # SQL миграции
│   ├── 001_initial_schema.sql
│   ├── 002_rls_policies.sql
│   └── 003_fix_rls_policies.sql
│
└── data/                          # Данные (SQLite, JSON)
```

## Ключевые компоненты

### main.py

**FastAPI приложение** с lifespan управлением:

```python
app = FastAPI(title="PAD+ AI", version="4.0.0")
```

**Startup:**
1. Регистрация зависимостей (DI)
2. Проверка ANTI_DIRECTIVE
3. Инициализация кэш менеджера
4. Запуск мониторинга
5. Инициализация импульса

**CORS:**
```python
allow_origins = [
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://0.0.0.0:5173",
    "http://127.0.0.1:5173"
]
```

### LiteLLM Service

**Файл:** `runtime/litellm_service.py`

Единый интерфейс к **20+ LLM провайдерам**:

| Провайдер | Тип | Модели |
|-----------|-----|--------|
| GigaChat | OAuth (прямой SDK) | GigaChat, GigaChat-Pro, GigaChat-Plus |
| Groq | API Key | llama-3.3-70b, llama-3.1-70b, gemma2-9b |
| OpenAI | API Key | gpt-4o, gpt-4o-mini, o1, o3-mini |
| Google | API Key | gemini-2.0-flash, gemini-1.5-pro |
| Anthropic | API Key | claude-3-5-sonnet, claude-3-haiku |
| OpenRouter | API Key | 100+ моделей |

**GigaChat** использует официальный SDK (`gigachat`) с OAuth аутентификацией.

**Методы:**
- `generate()` — генерация ответа
- `generate_stream()` — потоковая генерация
- `get_available_models()` — список моделей
- `test_connection()` — тест подключения

### Supabase Client

**Файл:** `core/supabase_client.py`

Подключение к Supabase (PostgreSQL):
- `SUPABASE_URL` — URL проекта
- `SUPABASE_KEY` — публичный ключ (для чтения)
- `SUPABASE_SERVICE_KEY` — сервисный ключ (для записи)

### Encryption

**Файл:** `core/encryption.py`

Шифрование API ключей пользователей:
- Алгоритм: **Fernet** (symmetric encryption)
- Ключ: `ENCRYPTION_KEY` из `.env`
- Соль: `ENCRYPTION_SALT` из `.env`

### Dependency Injection

**Файл:** `core/dependencies.py`

Регистрация 16 зависимостей:
- RAG Memory (PostgreSQL/pgvector)
- Fact Memory (SQLite)
- Emotion Manager
- Knowledge Graph
- Persona
- LiteLLM Service
- и другие

### Pipeline

**Файл:** `core/pipeline.py`

9 стадий обработки запроса:
1. **Safety** → проверка безопасности
2. **Intent** → классификация намерения
3. **Retrieve** → извлечение контекста (RAG + Facts + Knowledge)
4. **Persona** → контекст личности
5. **Generate** → LLM ответ
6. **Truth** → верификация
7. **Remember** → сохранение в память
8. **Evolve** → эволюция личности
9. **Emit** → события

## API Endpoints

### Auth
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/auth/register` | Регистрация |
| POST | `/api/v1/auth/login` | Вход |
| GET | `/api/v1/auth/me` | Текущий пользователь |

### Keys
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/keys` | Список ключей |
| POST | `/api/v1/keys` | Добавить ключ |
| PATCH | `/api/v1/keys/{id}` | Обновить ключ |
| DELETE | `/api/v1/keys/{id}` | Удалить ключ |
| POST | `/api/v1/keys/{id}/set-default` | Установить по умолчанию |
| POST | `/api/v1/keys/{id}/test` | Тест ключа |

### Providers
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/providers` | Список провайдеров |
| GET | `/api/v1/providers/{id}/models` | Модели провайдера |

### Chat
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/chat` | Чат |
| POST | `/api/v1/chat/stream` | Потоковый чат (SSE) |

### Health
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/health` | Проверка здоровья |

Полный список: http://localhost:8080/docs

## Запуск

```bash
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8080
```

## Зависимости

| Пакет | Назначение |
|-------|-----------|
| fastapi | Web фреймворк |
| uvicorn | ASGI сервер |
| supabase | Клиент Supabase |
| litellm | Unified LLM interface |
| gigachat | Официальный SDK GigaChat |
| cryptography | Шифрование (Fernet) |

| httpx / requests | HTTP клиенты |
| pydantic | Валидация данных |
