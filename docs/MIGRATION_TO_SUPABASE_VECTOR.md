# 🔄 Миграция на Supabase Vector

## 📋 План миграции

### Этап 1: Подготовка Supabase (15 минут)

1. Включить расширение pgvector
2. Создать таблицы для векторного поиска
3. Создать индексы для производительности

### Этап 2: Изменение кода RAG (1 час)

1. Добавить поддержку PostgreSQL в `memory/rag.py`
2. Реализовать fallback на SQLite RAG
3. Обновить методы вставки и поиска

### Этап 3: Миграция данных (30 минут)

1. Экспорт данных из текущего хранилища
2. Импорт в PostgreSQL
3. Верификация данных

### Этап 4: Деплой (15 минут)

1. Обновить переменные окружения
2. Перезапустить сервис
3. Протестировать работу

---

## 🗄️ SQL скрипты для Supabase

```sql
-- Включить расширение pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Таблица для RAG embeddings
CREATE TABLE IF NOT EXISTS rag_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text TEXT NOT NULL,
    embedding vector(384),  -- all-MiniLM-L6-v2 = 384 измерения
    user_id UUID,
    collection_name TEXT DEFAULT 'default',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Индекс для быстрого поиска (IVFFlat)
CREATE INDEX IF NOT EXISTS idx_rag_embeddings_embedding 
ON rag_embeddings USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Таблица для фактической памяти
CREATE TABLE IF NOT EXISTS memory_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fact TEXT NOT NULL,
    embedding vector(384),
    user_id UUID,
    category TEXT,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Индекс для фактов
CREATE INDEX IF NOT EXISTS idx_memory_facts_embedding 
ON memory_facts USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- RLS политики (если нужно)
ALTER TABLE rag_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_facts ENABLE ROW LEVEL SECURITY;

-- Политика: пользователь видит только свои данные
CREATE POLICY "Users can view own data" ON rag_embeddings
    FOR SELECT USING (auth.uid() = user_id);
    
CREATE POLICY "Users can insert own data" ON rag_embeddings
    FOR INSERT WITH CHECK (auth.uid() = user_id);
```

---

## 🔧 Изменения в коде

### Переменные окружения

```bash
# Добавить в Render/локально:
USE_SUPABASE_VECTOR=true
SUPABASE_URL=ваша_url
SUPABASE_KEY=ваш_key
DATABASE_URL=ваш_connection_string
```

### Новая реализация `memory/rag.py`

См. файл `memory/rag_supabase.py`

---

## 📊 Сравнение производительности

| Метрика | SQLite (локально) | Supabase Vector |
|---------|-------------------|-----------------|
| RAM | ~200-400MB | ~20MB |
| Диск | ~100-500MB | 0MB |
| Скорость поиска | ~10-50ms | ~50-100ms |
| Надёжность | Файлы на диске | PostgreSQL ACID |
| Масштабируемость | Ограничена | Неограниченно |

---

## 🚀 Откат изменений

Если что-то пошло не так:

```bash
# 1. Отключить Supabase Vector
# В панели Render удалить переменную USE_SUPABASE_VECTOR

# 2. Перезапустить сервис

# 3. SQLite RAG автоматически подхватится
```