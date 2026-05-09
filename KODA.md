# KODA — Контекст проекта PAD+ AI

> **Версия:** 4.0  
> **Тип:** Программный проект (Full-Stack AI Application)  
> **Язык разработки:** Python (backend), TypeScript/React (frontend)  
> **Дата актуализации:** 2026-05-08

---

## 1. Обзор проекта

**PAD+ AI** — когнитивный слой для искусственных интеллектуальных систем. Это не просто обёртка над LLM, а полноценная когнитивная архитектура с эмоциональной моделью, памятью, наблюдаемостью и самообучением.

### Ключевые особенности

- **Эмоциональная модель PAD** — Pleasure, Arousal, Dominance + Curiosity, Confidence
- **Система X-Ray** — полная наблюдаемость внутренней работы в реальном времени
- **Многомодельная архитектура** — работает с GPT-4, Gemini, Llama 3, Claude, локальными моделями через LiteLLM
- **Собственная память** — эпизодическая, семантическая, процедурная, фактическая
- **Цикл проверки правды TruthLoop**
- **Граф знаний**
- **Автономность** — планировщик, рефлексия, адаптация

---

## 2. Архитектура и технологии

### Backend

| Компонент | Технология |
|-----------|------------|
| Web Framework | FastAPI 0.104.1 |
| ASGI Server | Uvicorn 0.24.0 |
| База данных | PostgreSQL 15+ (Supabase) |
| ORM | SQLAlchemy 2.0.23 |
| Векторный поиск | pgvector 0.2.4 |
| Кэш | Redis 7+ / redis.asyncio |
| LLM интерфейс | LiteLLM 1.30.7 |
| WebSocket | websockets 12.0 |
| Граф знаний | NetworkX 3.2.1 |
| Клиент БД | supabase-py 2.0.3 |
| Шифрование | cryptography 41.0.7 |
| Валидация | Pydantic 2.5.3 |

### Frontend

| Компонент | Технология |
|-----------|------------|
| Framework | React 18.2 |
| Bundler | Vite 5.0.6 |
| Routing | react-router-dom 6.20 |
| Стили | Tailwind CSS 3.3.6 |
| UI анимации | Framer Motion 10.16 |
| Графики | Recharts 2.10 |
| Схемы | React Flow 11.10 |
| Иконки | Lucide React 0.294 |
| Supabase клиент | @supabase/supabase-js 2.39 |

### Инфраструктура

- **Контейнеризация:** Docker (Python 3.11-slim)
- **Мониторинг:** Prometheus + Grafana + Node Exporter + cAdvisor + Alertmanager
- **Платформа деплоя:** Render (free tier)
- **Облачная БД:** Supabase (PostgreSQL + Auth + Storage)
- **Облачный кэш:** Upstash Redis

---

## 3. Структура директорий

```
PAD+ AI/
├── backend/                 # FastAPI приложение
│   ├── api/                 # API endpoints
│   │   ├── dialog_routes.py
│   │   ├── document_routes.py
│   │   ├── file_routes.py
│   │   ├── metrics_routes.py
│   │   ├── user_routes.py
│   │   ├── xray_routes.py
│   │   └── routes.py
│   ├── core/                # Ядро системы
│   │   ├── supabase_client.py
│   │   ├── cache_manager.py
│   │   ├── monitoring.py
│   │   ├── anti_directive.py
│   │   └── dependencies.py
│   ├── memory/              # Подсистемы памяти
│   ├── emotion/             # Эмоциональная модель
│   ├── knowledge/           # Граф знаний
│   ├── autonomy/            # Автономность
│   ├── adapters/            # Адаптеры LLM
│   ├── analytics/           # Аналитика
│   ├── runtime/             # Runtime компоненты
│   ├── security_middleware.py
│   ├── main.py              # Точка входа
│   └── main_simple.py       # Упрощённый запуск
├── frontend/                # React приложение
│   ├── src/
│   │   ├── components/      # React компоненты
│   │   ├── pages/           # Страницы
│   │   ├── services/        # API сервисы
│   │   └── hooks/           # React hooks
│   ├── package.json
│   └── vite.config.js
├── docs/                    # Документация (40+ файлов)
├── monitoring/              # Конфиги Prometheus/Grafana
├── scripts/                 # SQL миграции и утилиты
├── tests/                   # Pytest тесты
├── requirements.txt         # Python зависимости
├── Dockerfile
├── docker-compose.monitoring.yml
├── Makefile
├── render.yaml              # Конфигурация Render
└── .env.example             # Шаблон переменных окружения
```

---

## 4. Сборка и запуск

### Локальная разработка

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd PAD+ AI

# 2. Установить Python зависимости
pip install -r requirements.txt

# 3. Установить frontend зависимости
cd frontend
npm install

# 4. Скопировать и настроить .env
cp .env.example .env
# Заполнить: SUPABASE_URL, SUPABASE_KEY, DATABASE_URL, ENCRYPTION_KEY, CSRF_SECRET_KEY

# 5. Применить миграции БД (если есть)
python scripts/apply_migrations.py

# 6. Запустить backend (порт 8080)
cd ..
python backend/main.py

# 7. В другом терминале запустить frontend (порт 5174)
cd frontend
npm run dev
```

### Docker

```bash
# Сборка образа
docker build -t padplus-ai .

# Запуск
docker run -p 8080:8080 --env-file .env padplus-ai
```

### Мониторинг (Docker Compose)

```bash
docker-compose -f docker-compose.monitoring.yml up -d
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

### Тестирование

```bash
# Все тесты
make test

# Unit тесты
make test-unit

# Интеграционные тесты
make test-integration

# С покрытием
make test-coverage

# API тесты (требуют запущенный сервер)
make test-api
```

---

## 5. Переменные окружения

Критически важные переменные (файл `.env`):

| Переменная | Назначение | Пример |
|------------|-----------|--------|
| `SUPABASE_URL` | URL Supabase проекта | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Публичный (anon) ключ Supabase | `sb_publishable_xxx` |
| `SUPABASE_SERVICE_KEY` | Service Role ключ (для админ-операций) | `sb_secret_xxx` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `ENCRYPTION_KEY` | Ключ шифрования API ключей (base64, 32 bytes) | — |
| `ENCRYPTION_SALT` | Соль шифрования | — |
| `CSRF_SECRET_KEY` | Секрет для CSRF токенов | — |
| `REDIS_URL` | Redis connection string | `rediss://...` |
| `FRONTEND_URL` | URL frontend (для CORS) | `http://localhost:5174` |
| `BACKEND_PORT` | Порт backend | `8080` |
| `RATE_LIMIT_PER_MINUTE` | Лимит запросов в минуту | `200` |

**⚠️ Важно:** `.env` НЕ должен коммититься в git. Уже добавлен в `.gitignore`.

---

## 6. API Endpoints (основные)

| Метод | Endpoint | Назначение |
|-------|----------|------------|
| POST | `/api/v1/auth/register` | Регистрация |
| POST | `/api/v1/auth/login` | Вход |
| POST | `/api/v1/auth/refresh` | Обновление токена |
| GET | `/api/v1/metrics/activity` | Активность системы |
| GET | `/api/v1/metrics/system` | Системные метрики |
| GET | `/api/v1/mind-state` | Состояние разума (эмоции) |
| POST | `/api/v1/chat` | Диалог с AI |
| POST | `/api/v1/documents/upload` | Загрузка документа |
| GET | `/api/v1/documents` | Список документов |
| GET | `/api/v1/documents/stats` | Статистика документов |
| GET | `/api/v1/collections` | Коллекции документов |
| GET | `/api/v1/keys` | API ключи пользователя |
| GET | `/api/v1/xray/state` | Состояние X-Ray |
| WS | `/ws` | WebSocket для real-time обновлений |

---

## 7. База данных (Supabase)

### Основные таблицы

- `users` — пользователи
- `user_settings` — настройки пользователя
- `dialogs` — диалоги
- `messages` — сообщения
- `documents` — документы для RAG
- `document_collections` — коллекции документов
- `user_api_keys` — зашифрованные API ключи LLM
- `api_calls` — лог API вызовов

### Storage Buckets

- `documents` — загруженные документы (public)
- `user_files` — пользовательские файлы
- `avatars` — аватары пользователей

### RLS Политики

Все таблицы используют Row Level Security с политиками на основе `auth.uid()`. При проблемах с доступом — проверять политики в Supabase Dashboard.

---

## 8. Правила разработки

### Стиль кода

- Python: PEP 8, type hints обязательны
- Именование: `snake_case` для функций/переменных, `PascalCase` для классов
- Логирование через `logging.getLogger("padplus.")` с русскоязычными сообщениями
- Все endpoint'ы должны иметь docstrings

### Безопасность

- API ключи шифруются перед сохранением в БД (AES-256-GCM)
- НИКОГДА не коммитить `.env` и ключи
- Использовать только `SUPABASE_KEY` (anon) на frontend
- `SUPABASE_SERVICE_KEY` использовать ТОЛЬКО на backend
- Rate limiting: 200 req/min для разработки
- CSRF защита включена
- CORS настроен строго (только `FRONTEND_URL`)

### Тестирование

- Pytest для всех тестов
- Маркеры: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- API тесты требуют запущенный сервер
- Перед коммитом: `make test-fast`

### Git

- Ветка по умолчанию: `main`
- `.env` в `.gitignore`
- Коммиты на русском или английском (консистентно)

---

## 9. Известные проблемы и решения

### RLS Policy Violation (403)

**Причина:** Supabase Storage или таблицы блокируют операции из-за RLS.  
**Решение:**
1. Проверить, что bucket создан и public
2. Проверить RLS политики в Supabase SQL Editor
3. Временно отключить RLS для диагностики: `ALTER TABLE ... DISABLE ROW LEVEL SECURITY`

### Rate Limiting (429)

**Причина:** Слишком много запросов с frontend (polling).  
**Решение:** Увеличить `RATE_LIMIT_PER_MINUTE` в `.env` (для dev: 200).

### Storage API

**Важно:** Supabase Python SDK использует `storage.from_("bucket")`, НЕ `storage.bucket()`.

### MIME Type Validation

Для загрузки файлов используется проверка по расширению (не только MIME type), т.к. браузеры могут отправлять `application/octet-stream`.

---

## 10. Документация

Ключевые файлы в `docs/`:

| Файл | Содержание |
|------|------------|
| `QUICK_DEPLOY_GUIDE.md` | Быстрая инструкция по деплою |
| `RENDER_DEPLOYMENT_GUIDE.md` | Подробная инструкция для Render |
| `AUDIT_REPORT_2026_05_08.md` | Отчёт аудита безопасности |
| `API.md` | Документация API |
| `ARCHITECTURE.md` | Архитектура системы |
| `MEMORY.md` | Подсистема памяти |
| `EMOTION.md` | Эмоциональная модель |
| `XRAY.md` | Система X-Ray |
| `RAG.md` | RAG и векторный поиск |
| `SECURITY_AUDIT_REPORT.md` | Отчёт безопасности |

---

## 11. Контакты и ссылки

- **Лицензия:** Apache License 2.0
- **Deploy:** Кнопка "Deploy to Render" в README
- **Статус:** Готов к production (8.5/10) после ротации ключей

---

*Файл создан для Koda AI Assistant. Обновлять при значимых изменениях архитектуры или деплоя.*
