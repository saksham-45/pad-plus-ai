# 🚀 Деплой с Supabase Vector

## 📋 Предварительные требования

- ✅ PostgreSQL с поддержкой pgvector (Supabase)
- ✅ Python 3.11+
- ✅ Node.js 20+

---

## 🔧 Шаг 1: Настройка Supabase

### 1.1. Включите pgvector

1. Откройте панель Supabase
2. Перейдите в **SQL Editor**
3. Выполните скрипт из `scripts/init_supabase_vector.sql`

```bash
# Или выполните SQL напрямую:
psql "postgresql://user:pass@host:5432/dbname" -f scripts/init_supabase_vector.sql
```

### 1.2. Проверка установки

```sql
-- Проверить наличие расширения
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Проверить таблицы
SELECT * FROM pg_tables WHERE tablename IN ('rag_embeddings', 'memory_facts');

-- Проверить индексы
SELECT * FROM pg_indexes WHERE tablename = 'rag_embeddings';
```

---

## 🔑 Шаг 2: Настройка переменных окружения

### Для локальной разработки:

```bash
# .env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
USE_SUPABASE_VECTOR=true
LOG_LEVEL=debug
```

### Для Render (через панель):

```
USE_SUPABASE_VECTOR=true
LOG_LEVEL=info
```

`DATABASE_URL` автоматически подтягивается из базы данных Render.

---

## 🧪 Шаг 3: Тестирование локально

```bash
# 1. Инициализировать Supabase Vector
psql "your-database-url" -f scripts/init_supabase_vector.sql

# 2. Протестировать RAG
python -c "
from memory.rag_supabase import get_rag
rag = get_rag()
print('Backend:', rag.use_supabase)
print('Stats:', rag.get_stats())
"
```

Ожидаемый вывод:
```
🔄 RAG: Используем Supabase Vector
✅ Supabase Vector инициализирован
Backend: True
Stats: {'total_embeddings': 0, 'unique_users': 0, 'backend': 'supabase_vector'}
```

---

## 🚀 Шаг 4: Деплой на Render

### 4.1. Убедитесь что `render.yaml` обновлен

```yaml
envVars:
  - key: USE_SUPABASE_VECTOR
    value: "true"
```

### 4.2. Закоммитьте изменения

```bash
git add .
git commit -m "feat: add Supabase Vector support for RAG memory"
git push origin main
```

### 4.3. Дождитесь деплоя

Render автоматически запустит новый деплой.

---

## 🔍 Шаг 5: Проверка работы

### 5.1. Проверьте логи

В панели Render → Logs:

```
🔄 RAG: Используем Supabase Vector
✅ Supabase Vector инициализирован
```

### 5.2. Проверьте через API

```bash
# Health check
curl https://your-app.onrender.com/health

# Проверка RAG статистики
curl https://your-app.onrender.com/api/v1/memory/stats
```

### 5.3. Проверьте в Supabase

```sql
-- Посмотреть embeddings
SELECT COUNT(*) FROM rag_embeddings;

-- Посмотреть статистику
SELECT * FROM rag_stats;
```

---

## 🔄 Шаг 6: Миграция данных (опционально)

Если у вас уже есть данные в локальном RAG:

```python
# scripts/migrate_rag_to_supabase.py
from memory.rag import get_rag as get_local_rag
from memory.rag_supabase import get_rag as get_supabase_rag

# 1. Получить данные из локального RAG
local_rag = get_local_rag()
local_results = local_rag.collection.get(include=["embeddings", "documents", "metadatas"])

# 2. Импорт в Supabase
supabase = get_supabase_rag()
for i, doc in enumerate(local_results["documents"]):
    supabase.add_embedding(
        text=doc,
        embedding=local_results["embeddings"][i],
        metadata=local_results["metadatas"][i] if local_results["metadatas"] else None
    )

print(f"✅ Мигрировано {len(local_results['documents'])} embeddings")
```

---

## ⚙️ Откат изменений

Если что-то пошло не так:

### Через переменную окружения

```bash
# В панели Render удалите или установите:
USE_SUPABASE_VECTOR=false
```

---

## 📊 Мониторинг

### Метрики производительности

```sql
-- Среднее время поиска (пример)
EXPLAIN ANALYZE
SELECT * FROM search_rag_embeddings(
    '[0.1, 0.2, ...]'::vector,  -- ваш embedding
    5,
    NULL
);
```

### Ожидается:
- **Supabase Vector**: 50-100ms (через сеть)

---

## 🐛 Устранение проблем

### Проблема: "pgvector расширение не найдено"

**Решение:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Проблема: "connection refused"

**Решение:**
1. Проверьте `DATABASE_URL`
2. Убедитесь что PostgreSQL доступен

### Проблема: медленный поиск

**Решение:**
```sql
-- Перестроить индекс
REINDEX INDEX idx_rag_embeddings_embedding;

-- Увеличить количество lists (для > 1M записей)
DROP INDEX idx_rag_embeddings_embedding;
CREATE INDEX idx_rag_embeddings_embedding 
ON rag_embeddings USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 1000);
```

---

## ✅ Чеклист перед продакшеном

- [ ] pgvector расширение установлено
- [ ] Таблицы созданы
- [ ] Индексы созданы
- [ ] RLS политики настроены (если нужно)
- [ ] Переменная `USE_SUPABASE_VECTOR=true` установлена
- [ ] Логи показывают "Supabase Vector инициализирован"
- [ ] Поиск работает через API
- [ ] Статистика отображается корректно

---

## 📞 Поддержка

При проблемах проверьте:
1. Logs на Render
2. SQL логи в Supabase
3. Переменные окружения
4. Актуальность кода

---

**Готово!** Ваша система теперь использует Supabase Vector.