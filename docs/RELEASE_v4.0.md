# PAD+ AI v4.0 — Release Manifest

**Дата:** 16 июня 2026  
**Ветка:** `main`  
**Коммит:** `6ca949c` (fix(v4.0): исправлен data contract pipeline, подключен IdentityPhase)  
**Статус:** ⚠ READY WITH WARNINGS

---

## 1. Что вошло в релиз

### 1.1. Когнитивное ядро (Cognitive Core)
- **PAD Emotional Model** — Pleasure, Arousal, Dominance + Curiosity, Confidence, Social Connection
- **Pipeline v4.0** — 24 фазы обработки: от идентификации до генерации ответа
- **TruthLoop** — цикл проверки достоверности
- **Anti-Directive** — защита от инжекции инструкций
- **Intent Router** — маршрутизация намерений
- **Response Guard** — защита ответов (безопасность, тональность, когнитивный слой)
- **Knowledge Graph** — граф знаний на NetworkX
- **Dreams** — автономная генерация сценариев / «снов» системы
- **Emotion Decay** — система затухания эмоций
- **Persona Evolution** — эволюция персоны системы

### 1.2. Память (Memory Systems)
- **Episodic Memory** — эпизодическая память (диалоги, события)
- **Semantic Memory** — семантическая память (факты, концепты)
- **RAG (PostgreSQL + pgvector)** — retrieval-augmented generation через векторный поиск
- **Memory Consolidation** — консолидация: Husk → Soil → Roots
- **Memory Hygiene** — гигиена памяти (очистка устаревших записей)

### 1.3. Наблюдаемость (Observability)
- **X-Ray System** — полная трассировка pipeline в реальном времени
  - Trace Collector, Broadcaster, Meta Learner
  - WebSocket-трансляция состояния
  - Thought Stream, Decision Log, Emotion Panel
  - Healer Trace Panel

### 1.4. API (Backend)
- FastAPI приложение, ~130 endpoints
- Поддержка множества LLM-провайдеров через LiteLLM-совместимый менеджер
- Управление API-ключами провайдеров (шифрованное хранение)
- WebSocket endpoint для real-time обновлений
- Supabase Auth (JWT) + service role для операций с обходом RLS
- CSRF-защита, валидация запросов, circuit breaker для БД
- Metrics endpoint (Prometheus-формат)
- Health check

### 1.5. Frontend
- React 18 + Vite 5 + Tailwind CSS 3
- 13 страниц: Chat, Dashboard, Providers, Documents, Memory, History, X-Ray, Healer, Experience, Knowledge, Settings, Instructions, Connected Providers
- X-Ray панели в реальном времени (WebSocket)
- Адаптивный дизайн (MobileMenu)
- ErrorBoundary

### 1.6. Инфраструктура
- `render.yaml` — конфигурация Render (Python runtime, PostgreSQL, Redis)
- `.github/workflows/ci.yml` — CI (pytest, ruff, black, mypy)
- `.github/workflows/deploy.yml` — деплой на Render через GitHub Actions
- `requirements.txt` — зависимости Python
- `.env.example` — шаблон конфигурации

### 1.7. Документация
- `docs/ARCHITECTURE.md` — архитектура
- `docs/DEPLOYMENT.md` — деплой
- `docs/PROJECT_STRUCTURE.md` — структура проекта
- `docs/API.md` — спецификация API
- `docs/XRAY.md`, `docs/XRAY_GUIDE.md` — X-Ray
- `docs/EMOTION_SYSTEM.md`, `docs/MEMORY_SYSTEM.md`, `docs/META_SYSTEM.md`
- `docs/OVERVIEW.md`, `docs/PIPELINE.md`
- `docs/RLS_POLICIES.md` — политики Row Level Security
- `docs/SELF_HEALING_ARCHITECTURE.md` — архитектура самовосстановления
- `docs/STABILIZATION_PLAN.md` — план стабилизации
- `docs/IMPLEMENTATION_PLAN.md` — план реализации
- `docs/experience.md`, `docs/impulse/` — подсистема опыта и импульса
- Архив устаревшей документации: `docs/archive/legacy/`
- Apache License 2.0

---

## 2. Что сознательно не вошло в релиз

### 2.1. Dead files (оставлены для истории, НЕ удалены)
- `backend/main_simple.py` — упрощённая версия main, не используется
- `backend/main_stable.py` — предыдущая стабильная версия, не используется
- `backend/check_*.py`, `backend/test_decrypt.py`, `backend/test_endpoints.py` — debug-скрипты
- `backend/data/chroma/` — остатки ChromaDB (1.2 MB, код переехал на pgvector)
- `backend/neurocore_memory.db` — SQLite БД (68 KB, не используется)
- `backend/startup*.log` — логи предыдущих запусков
- `backend/core/logging_config.py` — structured logging (определён, но не подключён)
- `test_persona.py` — тест вне testpaths
- `frontend/.github/modernize/` — мусор от попытки модернизации
- `experiments/` — экспериментальный код
- `scripts/archive/` — старые скрипты

**Почему не удалены:** Первый публичный релиз — консервативный подход. Если код не мешает сборке и не содержит секретов — он остаётся. Удаление будет в v4.1.

### 2.2. HEALER — подсистема самовосстановления
HEALER — отдельный проект, интегрированный в репозиторий. Имеет:
- Собственный CI (`.github/workflows/ci.yml`)
- Свои тесты, mypy кэш, pytest кэш
- Собственную код-базу (`healer/`, `aethon/`)
- Интеграцию через `backend/healing/` и `backend/integration/`

**Почему не вынесен:** В v4.0 HEALER уже является частью системы — `start_impulse()` вызывается при старте сервера. Выделение в submodule — архитектурное изменение, запланированное на v4.1.

### 2.3. Изменения, отклонённые для v4.0
- Рефакторинг CORS (работает, изменение «для красоты»)
- Переписывание логирования (работает через basicConfig)
- Изменение структуры проекта
- Добавление новых метрик
- Code-splitting фронтенда (chunk 689 KB — известное ограничение)
- Замена `SupabaseServiceKey` (требует ручных действий в Supabase Dashboard)

---

## 3. Известные ограничения

### 3.1. Производственные
- **Один worker** — и gunicorn, и uvicorn настроены на 1 worker. При росте нагрузки потребуется увеличение.
- **HEALER не изолирован** — интегрирован в тот же процесс, ошибка в HEALER может уронить сервер.
- **`SUPABASE_SERVICE_KEY`** — service role ключ хранится как переменная окружения. При компрометации даёт полный доступ к БД.
- **Chunk size** — главный JS-бандл 689 KB (до code-splitting).

### 3.2. Архитектурные
- **CORS** использует проверку `"onrender.com" in origin` — пропускает любые поддомены Render.
- **Debug-роуты** (`/api/v1/debug/`) — отключаются флагом `DEBUG`, но код остаётся в репозитории.
- **Memory consolidation** — работает в синхронном режиме, потенциальный блокировщик event loop.
- **X-Ray meta learner** — сохраняет данные в JSON-файлы, не в БД.

### 3.3. Зависимости
- `supabase>=2.0.0` — работает, но может конфликтовать с httpx.
- `psycopg2-binary` — не рекомендуется для production (использовать `psycopg2`).
- `aioredis` удалён (deprecated), но код всё ещё может содержать `import aioredis`.

### 3.4. Документационные
- `README.md` ссылается на репозиторий `Ovladimirovich/PAD-AI-v3.5` — URL устарел.
- Нет отдельной инструкции по быстрому старту для новых контрибьюторов.

---

## 4. План на v4.1

### 4.1. Безопасность
- [ ] Отозвать и перегенерировать `SUPABASE_SERVICE_KEY`
- [ ] Удалить debug-скрипты с выводом ключей (`check_latest_key.py`, `check_with_service.py`)
- [ ] Добавить секрет-сканирование в CI (truffleHog / Gitleaks)

### 4.2. Чистка репозитория
- [ ] `git filter-branch` для удаления `.vs/` из истории
- [ ] Удалить `main_simple.py`, `main_stable.py`
- [ ] Удалить или подключить `logging_config.py`
- [ ] Удалить `frontend/.github/modernize/`
- [ ] Переместить `test_persona.py` в `tests/`
- [ ] Перенести `XRAY_BRAIN.md`, `Инструкция для ИИ-Инженера.md` в `docs/`

### 4.3. Архитектура
- [ ] Выделить HEALER в отдельный репозиторий / submodule
- [ ] Улучшить CORS — точная валидация origin
- [ ] Code-splitting фронтенда
- [ ] Заменить `psycopg2-binary` на `psycopg2` (C-extension)

### 4.4. Новые возможности (кандидаты)
- [ ] Cognitive Observatory — визуализация когнитивных процессов
- [ ] Multi-worker поддержка
- [ ] Асинхронная memory consolidation
- [ ] Structured logging (JSON-формат для ELK/Loki)
- [ ] Graceful degradation при отказе БД

---

## 5. Чек-лист готовности к GitHub

### Обязательно
- [x] `.gitignore` актуален, временные каталоги исключены
- [x] `.env` не в git history (подтверждено)
- [x] Нет секретов в коде (проверено `git grep`)
- [x] Версия едина: `v4.0` (README, backend, frontend)
- [x] Лицензия Apache 2.0 присутствует
- [x] `pyproject.toml` настроен
- [x] `README.md` содержит описание и инструкцию

### Желательно
- [ ] Обновить URL репозитория в README (сейчас `Ovladimirovich/PAD-AI-v3.5`)
- [ ] Удалить `check_latest_key.py` и `check_with_service.py` (содержат вывод ключей)
- [ ] Удалить `backend/startup*.log` (локальные логи)
- [ ] Проверить `git log` на наличие случайно закоммиченных секретов

---

## 6. Чек-лист готовности к Render

### Обязательно
- [x] `render.yaml` присутствует
- [x] `startCommand` корректен: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- [x] `requirements.txt` корректен, дубликаты удалены
- [x] WebSocket URL динамический (не hardcoded localhost)
- [x] Debug-роуты отключены (`DEBUG=false`)
- [x] CORS настроен для Render-доменов
- [x] `SUPABASE_SERVICE_KEY` добавлен в `render.yaml`

### Настроить вручную в Render Dashboard
- [ ] `SUPABASE_URL` — URL проекта Supabase
- [ ] `SUPABASE_KEY` — publishable anon key
- [ ] `SUPABASE_SERVICE_KEY` — service role key (сгенерировать новый)
- [ ] `ENCRYPTION_KEY` — base64, 32 байта
- [ ] `ENCRYPTION_SALT` — base64, 32 байта
- [ ] `CSRF_SECRET_KEY` — token_urlsafe(32)
- [ ] `FRONTEND_URL` — `https://pad-plus-ai.onrender.com`
- [ ] `REDIS_URL` — из созданного Redis сервиса
- [ ] `DATABASE_URL` — из созданного PostgreSQL сервиса

### Проверить после деплоя
- [ ] `GET /health` → `{"status": "healthy"}`
- [ ] `GET /` → frontend index.html
- [ ] WebSocket `/ws` — устанавливается
- [ ] Авторизация (логин/регистрация)
- [ ] Отправка сообщения (pipeline)
- [ ] X-Ray панель
- [ ] Загрузка документов
- [ ] Memory / RAG

---

## 7. Подписи

Подготовлено: **Release Engineer (AI)**  
Утверждено: **Release Manager**  

Дата: 2026-06-16  
Версия: 4.0.0  
Статус: ⚠ READY WITH WARNINGS
