# План ликвидации и нормализации проекта PAD+ AI v3.5

## Приоритет: P0 → P1 → P2 → P3 → P4

---

## P0: ChromaDB — полная зачистка

> ChromaDB больше не используется (удалён в пользу PostgreSQL/Supabase Vector).
> Все упоминания вредят разработке — создают ложные ожидания и путают импорты.

### P0.1 — Файлы целиком на удаление

| Файл | Причина |
|------|---------|
| `backend/core/chroma_memory.py` | Базовый класс ChromaDB — мёртвый код |
| `scripts/preload_chroma_model.py` | Скрипт предзагрузки для ChromaDB |
| `scripts/migrate_facts_to_chroma.py` | Миграция фактов в ChromaDB |

### P0.2 — Импорты и код

| Файл | Что делать |
|------|------------|
| `backend/core/pipeline.py:919-956` | Удалить блок `try:` с импортами `vector_memory_chroma` и `smartcache_chroma` (оба модуля не существуют, код всегда падает в `except`) |
| `backend/memory/__init__.py` | Удалить все комментарии про ChromaDB (строки 6-8, 15, 21, 33, 36, 60) |
| `backend/main.py:110` | Удалить/заменить комментарий `# ChromaDB инициализация (можно отложить)` |
| `backend/main_stable.py:814` | Удалить `"chroma": "disabled"` из статуса |
| `backend/memory/rag.py:22` | Удалить комментарий `# ChromaDB удален в пользу PostgreSQL-версии` |
| `backend/memory/rag_postgres.py:5` | Удалить комментарий `# ChromaDB удалён для экономии памяти.` |

### P0.3 — Инфраструктура

| Файл | Что делать |
|------|------------|
| `mypy.ini:41` | Удалить секцию `[mypy-chromadb.*]` |
| `requirements.txt:31-32` | Удалить комментарий про ChromaDB |
| `render.yaml:12` | Убрать `data/chroma` из команды очистки |

### P0.4 — Фронтенд

| Файл | Строки | Что делать |
|------|--------|------------|
| `frontend/src/pages/InstructionsPage.jsx:590` | Заменить `(SQLite, ChromaDB)` на `(SQLite, PostgreSQL)` |
| `frontend/src/pages/InstructionsPage.jsx:624` | Заменить `векторный поиск (ChromaDB)` на `векторный поиск (PostgreSQL)` |

### P0.5 — Тесты

| Файл | Что делать |
|------|------------|
| `tests/integration_tests/test_phase2_rag_personalization.py:84` | Переформулировать: `без ChromaDB` → `без внешних зависимостей` |
| `tests/integration_tests/test_phase2_rag_personalization.py:145-149` | Переписать тест — проверять отсутствие `chromadb` неактуально |

### P0.6 — Документация (17 файлов)

| Файл | Действие |
|------|----------|
| `README.md:62` | Удалить строку `- ChromaDB` |
| `docs/BACKEND.md` | Заменить все упоминания ChromaDB на PostgreSQL |
| `docs/MEMORY.md` | Убрать ChromaDB из описания RAG и Fact Memory |
| `docs/ARCHITECTURE.md` | Заменить ChromaDB на PostgreSQL в таблице компонентов |
| `docs/RAG.md` | Переписать — текущий RAG на PostgreSQL/Supabase |
| `docs/API.md:125` | Убрать `persist_dir: data/chroma` |
| `docs/SYSTEM_ANALYSIS_REPORT.md` | Убрать секции про ChromaDB версии |
| `docs/AUDIT_REPORT.md` | Убрать дубликаты _chroma файлов |
| `docs/HARDENING_PLAN.md` | Убрать план удаления старых версий и _chroma импорты |
| `docs/ISSUE_FIX_PLAN.md` | Убрать пункт про обновление на _chroma версии |
| `docs/MIGRATION_TO_SUPABASE_VECTOR.md` | Убрать ChromaDB fallback |
| `docs/DEPLOYMENT_SUPABASE_VECTOR.md` | Убрать секции миграции из ChromaDB |
| `docs/RENDER_DEPLOYMENT.md` | Убрать ChromaDB секцию |
| `docs/LOCAL_SETUP_POSTGRES.md` | Убрать таблицу ChromaDB→PostgreSQL |
| `docs/archive/AUDIT_REPORT_2026_05_08.md` | Убрать `убраны chromadb зависимости` |
| `docs/план.md` (и `.kilo/plans/plan.md`) | Заменить ChromaDB на PostgreSQL в стеке |
| `AUDIT_PROVIDERS_MODELS.md:81` | Убрать `Pipeline обращается к ChromaDB` |
| `FRONTEND_SECURITY_REPORT.md` | Проверить, убрать если есть |
| `QUICK_DEPLOY_GUIDE.md` | Проверить, убрать если есть |
| `RENDER_DEPLOYMENT_GUIDE.md` | Убрать `ChromaDB инициализируется` |
| `COMPLETED_IMPROVEMENTS_SUMMARY.md` | Проверить, убрать если есть |

---

## P1: GigaChat — нормализация

### Проблемы сейчас:
- **4 метода auth подряд** (Basic client_id:secret, Basic secret only, Bearer, Raw) — гадание
- **Нет кэширования access_token** — переавторизация на каждый запрос
- **Нет retry-логики** с exponential backoff (кроме raw retry 2 попытки)
- **Дублирование кода** между `_generate_gigachat` и `_stream_gigachat` (один в один)
- **Нет unit-тестов** для GigaChat-клиента

### План:

1. **Создать `backend/adapters/gigachat_client.py`**
   - Чистый класс с методами:
     - `_auth()` — получение access_token с кэшированием (хранить token + expires_at)
     - `_complete()` — chat completion
     - `_stream()` — streaming completion
   - Единый алгоритм auth (без перебора): Basic Auth с `client_id:secret`
   - Кэш: `{access_token, expires_at}` в памяти, переавторизация при expires_at - 60s
   - Retry с exponential backoff (1s, 2s, 4s, max 3 попытки)

2. **Интегрировать в `LLMService`**
   - Заменить `_generate_gigachat()` на вызов `GigaChatClient.complete()`
   - Заменить `_stream_gigachat()` на вызов `GigaChatClient.stream()`

3. **Убрать хардкод** GIGACHAT_AUTH_URL, GIGACHAT_API_URL — оставить в `.env`

4. **Написать тесты** `tests/test_gigachat_client.py` с моками HTTP

---

## P2: Дашборд — убрать фейк-метрики

### Проблема:
`get_system_metrics()` (строка ~2510) и `get_full_system_status()` (строка ~2540) возвращают `random.*` вместо реальных данных.

### План:
1. **`get_system_metrics()`** — либо собирать реальные метрики (psutil, cache stats), либо выдавать `{"status": "metrics_collection_disabled"}`
2. **`get_full_system_status()`** — каждый `except Exception: return random.*` заменить на осмысленное значение по умолчанию (`0` или `None`, не рандом)
3. **UI** на фронтенде — показывать `"данные недоступны"` вместо случайных цифр

---

## P3: Мёртвый код

### Проблема:
В `frontend_routes.py` в `/chat` endpoint: `use_fast_mode = False` зашито жёстко, но целая ветка `if use_fast_mode:` (строки ~450-480) с логикой fallback UI никогда не выполняется.

### План:
1. Удалить переменную `use_fast_mode`
2. Удалить блок `if use_fast_mode:`...`else:`
3. Оставить только полный pipeline (то, что сейчас в `else`)

---

## P4: Дублирование кода

### Проблема:
В `/chat` endpoint обновление `last_used_at` написано дважды:
- В fast-mode ветке: после `pm.generate()`
- В full-mode ветке: после `pipeline.execute()`

### План:
1. Вынести `update last_used_at` один раз в конец функции, перед `return`

---

## P5: Синхронизация кеша

### Проблема:
- Frontend кеширует статусы в localStorage с TTL 5 мин
- Backend кеширует статусы в Redis/cache с TTL 5 мин
- При `refreshKeyStatus()` на фронте, backend сбрасывает кеш, но фронт всё ещё видит localStorage

### План:
1. После успешного `POST /keys/status/{key_id}/refresh` — фронт должен удалить localStorage-кеш
2. В `refreshKeyStatus()` после получения ответа: `localStorage.removeItem(KEY_STATUS_STORAGE_KEY)`

---

## Порядок выполнения

```
P0.1 → P0.2 → P0.3 → P0.4 → P0.5 → P0.6  (ChromaDB)
  ↓
P1.1 → P1.2 → P1.3 → P1.4                (GigaChat)
  ↓
P2                                       (Дашборд)
  ↓
P3                                       (Мёртвый код)
  ↓
P4                                       (Дублирование)
  ↓
P5                                       (Кеш)
```

**Оценка трудоёмкости:**
- P0 (ChromaDB): ~2-3 часа (в основном документация, удаление мёртвых строк)
- P1 (GigaChat): ~4-6 часов (рефакторинг, новый класс, тесты)
- P2 (Дашборд): ~1-2 часа
- P3 (Мёртвый код): ~0.5 часа
- P4 (Дублирование): ~0.5 часа
- P5 (Кеш): ~0.5 часа

**Итого:** ~9-12 часов чистого времени
