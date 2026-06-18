-- 018_memory_persistence.sql
-- Перенос Persona, Roots, Emotion из JSON-файлов в PostgreSQL
-- Обеспечивает сохранность состояния личности между деплоями Render

-- Persona state (одиночная запись для системной персоны)
CREATE TABLE IF NOT EXISTS persona_state (
    id TEXT PRIMARY KEY DEFAULT 'system',
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Корневые знания (Roots)
CREATE TABLE IF NOT EXISTS roots_knowledge (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    category TEXT DEFAULT 'philosophy',
    priority INTEGER DEFAULT 50,
    immutable BOOLEAN DEFAULT TRUE,
    source TEXT DEFAULT 'system',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Эмоциональное состояние (одиночная запись для системы)
CREATE TABLE IF NOT EXISTS emotion_state (
    id TEXT PRIMARY KEY DEFAULT 'system',
    data JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Включаем RLS
ALTER TABLE persona_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE roots_knowledge ENABLE ROW LEVEL SECURITY;
ALTER TABLE emotion_state ENABLE ROW LEVEL SECURITY;

-- Политики для service_role (полный доступ)
CREATE POLICY "Service role has full access to persona_state"
    ON persona_state TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "Service role has full access to roots_knowledge"
    ON roots_knowledge TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "Service role has full access to emotion_state"
    ON emotion_state TO service_role
    USING (true) WITH CHECK (true);

-- Политики для анонимных (только чтение)
CREATE POLICY "Anon can read persona_state"
    ON persona_state FOR SELECT TO anon
    USING (true);

CREATE POLICY "Anon can read roots_knowledge"
    ON roots_knowledge FOR SELECT TO anon
    USING (true);

CREATE POLICY "Anon can read emotion_state"
    ON emotion_state FOR SELECT TO anon
    USING (true);
