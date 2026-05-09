-- PAD+ AI — Инициализация PostgreSQL для RAG
-- Выполнить в Supabase SQL Editor

-- 1. Включить расширение pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Создать таблицу для диалогов
CREATE TABLE IF NOT EXISTS rag_dialogs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    summary TEXT,
    keywords TEXT[],
    topic TEXT DEFAULT 'общее',
    topic_confidence FLOAT DEFAULT 0.5,
    sentiment TEXT DEFAULT 'neutral',
    entities JSONB DEFAULT '[]',
    relations JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    user_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Создать векторный индекс (если нужно для future vector search)
-- Примечание: сейчас используется простой поиск, индекс не обязателен
CREATE INDEX IF NOT EXISTS idx_rag_dialogs_user_id ON rag_dialogs(user_id);
CREATE INDEX IF NOT EXISTS idx_rag_dialogs_topic ON rag_dialogs(topic);
CREATE INDEX IF NOT EXISTS idx_rag_dialogs_created_at ON rag_dialogs(created_at DESC);

-- 4. Проверка создания
SELECT '✅ Таблица rag_dialogs создана!' as status;
SELECT COUNT(*) as record_count FROM rag_dialogs;