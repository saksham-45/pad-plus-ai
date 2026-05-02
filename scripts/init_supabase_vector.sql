-- ============================================================================
-- SUPABASE VECTOR INITIALIZATION SCRIPT
-- ============================================================================
-- Этот скрипт настраивает PostgreSQL для векторного поиска с pgvector
-- Выполните его в SQL Editor панели Supabase
-- ============================================================================

-- 1. Включить расширение pgvector
-- ----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Создать таблицу для RAG embeddings
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rag_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text TEXT NOT NULL,
    embedding vector(384),  -- all-MiniLM-L6-v2 = 384 измерения
    user_id UUID,
    collection_name TEXT DEFAULT 'default',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Создать индекс для быстрого векторного поиска
-- ----------------------------------------------------------------------------
-- IVFFlat индекс - хороший баланс скорости и точности
-- lists = 100 рекомендуется для < 1M записей
CREATE INDEX IF NOT EXISTS idx_rag_embeddings_embedding 
ON rag_embeddings USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- 4. Создать обычную таблицу для фактической памяти
-- ----------------------------------------------------------------------------
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

-- 5. Индекс для фактов памяти
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_memory_facts_embedding 
ON memory_facts USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- 6. Включить RLS (Row Level Security)
-- ----------------------------------------------------------------------------
ALTER TABLE rag_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_facts ENABLE ROW LEVEL SECURITY;

-- 7. Создать политики безопасности (если используете Supabase Auth)
-- ----------------------------------------------------------------------------

-- Политика для RAG embeddings
DO $$
BEGIN
    -- Policy: Users can view own data
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'rag_embeddings' 
        AND policyname = 'Users can view own rag data'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can view own rag data" ON rag_embeddings
            FOR SELECT USING (auth.uid() = user_id)';
    END IF;
    
    -- Policy: Users can insert own data
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'rag_embeddings' 
        AND policyname = 'Users can insert own rag data'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can insert own rag data" ON rag_embeddings
            FOR INSERT WITH CHECK (auth.uid() = user_id)';
    END IF;
    
    -- Policy: Users can update own data
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'rag_embeddings' 
        AND policyname = 'Users can update own rag data'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can update own rag data" ON rag_embeddings
            FOR UPDATE USING (auth.uid() = user_id)';
    END IF;
    
    -- Policy: Users can delete own data
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'rag_embeddings' 
        AND policyname = 'Users can delete own rag data'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can delete own rag data" ON rag_embeddings
            FOR DELETE USING (auth.uid() = user_id)';
    END IF;
END $$;

-- 8. Создать функции для упрощения работы
-- ----------------------------------------------------------------------------

-- Функция для поиска с векторным сходством
CREATE OR REPLACE FUNCTION search_rag_embeddings(
    query_embedding vector(384),
    match_count int DEFAULT 5,
    filter_user_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    text TEXT,
    user_id UUID,
    collection_name TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
#variable_conflict use_column
BEGIN
    RETURN QUERY
    SELECT
        id,
        text,
        user_id,
        collection_name,
        metadata,
        1 - (embedding <=> query_embedding) AS similarity
    FROM rag_embeddings
    WHERE filter_user_id IS NULL OR user_id = filter_user_id
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Функция для вставки нового embedding
CREATE OR REPLACE FUNCTION insert_rag_embedding(
    p_text TEXT,
    p_embedding vector(384),
    p_user_id UUID DEFAULT NULL,
    p_collection_name TEXT DEFAULT 'default',
    p_metadata JSONB DEFAULT '{}'
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    v_id UUID;
BEGIN
    INSERT INTO rag_embeddings (text, embedding, user_id, collection_name, metadata)
    VALUES (p_text, p_embedding, p_user_id, p_collection_name, p_metadata)
    RETURNING id INTO v_id;
    
    RETURN v_id;
END;
$$;

-- 9. Создать view для статистики
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW rag_stats AS
SELECT 
    COUNT(*) as total_embeddings,
    COUNT(DISTINCT user_id) as unique_users,
    collection_name,
    COUNT(*) as embeddings_per_collection
FROM rag_embeddings
GROUP BY collection_name;

-- 10. Создать триггер для автоматического обновления updated_at
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_memory_facts_updated_at
    BEFORE UPDATE ON memory_facts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ЗАВЕРШЕНИЕ
-- ============================================================================

-- Проверка успешного создания
DO $$
BEGIN
    RAISE NOTICE '✅ Supabase Vector успешно инициализирован!';
    RAISE NOTICE '📊 Таблицы: rag_embeddings, memory_facts';
    RAISE NOTICE '🔍 Индексы: ivfflat (cosine distance)';
    RAISE NOTICE '🔒 RLS политики созданы';
    RAISE NOTICE '⚡ Функции: search_rag_embeddings(), insert_rag_embedding()';
END $$;

-- Показать статистику
SELECT 
    schemaname,
    tablename,
    indexname
FROM pg_indexes
WHERE tablename IN ('rag_embeddings', 'memory_facts')
ORDER BY tablename, indexname;