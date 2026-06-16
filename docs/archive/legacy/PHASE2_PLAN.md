# План нормализации — Фаза 2: Стабилизация и чистка legacy

## Приоритет: P0 → P1 → P2

---

## P0: Объединение main.py и main_stable.py

**Сейчас:** Два почти идентичных entry point. `main_stable.py` — урезанная копия `main.py`. Фиксы в одном не попадают в другой. Это источник регрессий.

### Проблемы:
- Дублирование роутов (`/api/v1/metrics/system` существует в обоих)
- Разная инициализация компонентов (в `main.py` pipeline, truth_loop, PAD; в `main_stable.py` — нет)
- Баги фиксятся в одном файле и забываются в другом

| Файл | Размер | Роуты | Комментарий |
|------|--------|-------|-------------|
| `backend/main.py` | ~250 строк | 4 | Основной entry point, инициализирует PAD+ AI |
| `backend/main_stable.py` | ~1320 строк | 25+ | Урезанная копия, используется на Render? |

### План:
1. **Аудит роутов:** перенести отсутствующие в `main.py` роуты из `main_stable.py`
   - `GET /api/v1/models/metrics` (быстрый хелсчек)
   - Любые другие уникальные для `main_stable.py`
2. **Сравнить middleware и startup/shutdown** — унифицировать
3. **Удалить `main_stable.py`** или заменить его содержимое на `from main import app`
4. Обновить `render.yaml` `startCommand` на `backend.main:app`

**Оценка:** ~2-3 часа

---

## P1: Чистка мёртвого кода в memory/

### Сейчас:
После ChromaDB-зачистки остались legacy-файлы, которые никуда не импортируются.

| Файл | Легаси от | Статус |
|------|-----------|--------|
| `backend/memory/vectormemory.py` | SQLite-векторная память | Не импортируется? |
| `backend/memory/smartcache.py` | SQLite-кэш | Не импортируется? |
| `backend/memory/fact_memory.py` | SQLite-факты | Не импортируется? |
| `backend/memory/async_pad_model.py` | Асинхронная копия PAD | Не импортируется? |
| `backend/memory/rag_supabase.py` | Supabase Vector RAG | Если не используется |
| `backend/memory/rag_optimizer.py` | Оптимизатор RAG | Не импортируется? |

### План:
1. Проверить git grep — импортируется ли каждый файл хоть где-то
2. Для неиспользуемых — удалить
3. Для сомнительных — оставить, но добавить `# TODO: deprecate` и комментарий

**Оценка:** ~1 час

---

## P2: Чистка requirements.txt

### Сейчас:
65 строк, из них 6 закомментированы (chromaDB), некоторые не используются.

### Что удалить:
```
gigachat                       # SDK не используется — пишем HTTP-клиент
chromadb                       # закомментировано
sentence-transformers          # закомментировано
numpy>=2.0.0                   # закомментировано
orjson>=3.9.0                  # закомментировано
onnxruntime>=1.14.0            # закомментировано
```

### Что проверить на актуальность:
```
litellm           — используется ли реально? Или только OpenRouter?
chromadb          — убедиться что не импортируется нигде
```

**Оценка:** ~30 минут

---

## P3: Чистка scripts/

### Сейчас:
Папка `scripts/` содержит скрипты для миграций, тестов, деплоя. Часть уже неактуальна.

| Скрипт | Статус | Действие |
|--------|--------|----------|
| `scripts/migrate_rag_user_id.py` | ❌ Удалён (использовал chromadb) | — |
| `scripts/preload_chroma_model.py` | ❌ Удалён | — |
| `scripts/migrate_facts_to_chroma.py` | ❌ Удалён | — |
| `scripts/apply_migrations.py` | ❓ Актуален? | Проверить |
| `scripts/fix_history.py` | ❓ Актуален? | Проверить |
| `scripts/setup.py` | ❓ Актуален? | Проверить |
| `scripts/run_local.py` | ❓ Актуален? | Проверить |
| `scripts/run_prod.py` | ❓ Актуален? | Проверить |
| `scripts/test_db.py` | ❓ Актуален? | Проверить |
| `scripts/update_env.py` | ❓ Актуален? | Проверить |

### План:
1. Для каждого скрипта проверить: используется ли в CI/CD, документации, render.yaml
2. Неиспользуемые — удалить
3. Оставшиеся — перенести в `backend/scripts/` (единая структура)

**Оценка:** ~1 час

---

## P4: Аудит docs/archive/

**18 файлов**, большинство устаревшие. Нужна сортировка.

### Действие:
1. Пробежать по файлам, определить:
   - `DELETE` — устаревшие отчёты, старые версии
   - `KEEP` — исторически ценные
2. Удалить ~70% архива

**Оценка:** ~30 минут

---

## P5: Стабилизация тестов

### Проблемы:
- `test_key_status_cache.py` тестирует **мок** CacheManager, не реальный API
- Нет тестов FastAPI TestClient для `frontend_routes.py`
- Нет E2E теста для `/chat`

### План:
1. Добавить `pytest-httpx` или `httpx_mock` для HTTP-моков
2. Написать тест `GET /api/v1/keys` через TestClient
3. Написать тест `PATCH /keys/{id}/set-default` через TestClient
4. Написать тест `GET /metrics/system` через TestClient (убедиться, что нет random)
5. Написать тест `GET /system/full-status` через TestClient (убедиться, что нет random)

**Оценка:** ~2-3 часа

---

## P6: Аудит pipeline.py (опционально)

**Файл:** `backend/core/pipeline.py`, ~1223 строк, 10+ этапов.

### Проблемы:
- Каждый этап обёрнут в `try/except` с `ErrorSeverity.LOW` — тихие сбои
- `vector_memory_chroma` и `smartcache_chroma` уже удалены, но код в pipeline был исправлен в P0
- 10+ последовательных `async def` внутри одной функции

### План (не срочно):
1. Разбить pipeline на отдельные модули в `backend/core/pipeline/`
2. Добавить строгую типизацию этапов
3. Заменить тихие `try/except` на логирование с контекстом

**Оценка:** ~4-6 часов, можно отложить на Фазу 3

---

## Порядок выполнения

```
P0: main.py + main_stable.py   (2-3ч)
  ↓
P1: memory/ legacy             (1ч)
  ↓
P2: requirements.txt           (0.5ч)
  ↓
P3: scripts/                   (1ч)
  ↓
P4: docs/archive/              (0.5ч)
  ↓
P5: тесты                      (2-3ч)
  ↓
P6: pipeline.py                (4-6ч, Фаза 3)
```

**Итого Фаза 2:** ~7-9 часов (без P6)
**С P6:** ~13-15 часов
