-- 019_episodic_semantic_postgres.sql
-- PostgreSQL таблицы для Episodic и Semantic памяти
-- Замена SQLite файлов для персистентности между деплоями

-- === Эпизодическая память ===

CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    user_id TEXT,
    situation TEXT DEFAULT '',
    participants JSONB DEFAULT '[]',
    location TEXT DEFAULT '',
    user_message TEXT NOT NULL,
    ai_response TEXT,
    intent TEXT DEFAULT 'unknown',
    topic TEXT DEFAULT 'общее',
    emotion_before JSONB DEFAULT '{}',
    emotion_after JSONB DEFAULT '{}',
    emotion_impact REAL DEFAULT 0.0,
    entities JSONB DEFAULT '[]',
    concepts JSONB DEFAULT '[]',
    keywords JSONB DEFAULT '[]',
    related_episodes JSONB DEFAULT '[]',
    parent_episode TEXT,
    continuation_of TEXT,
    significance REAL DEFAULT 0.5,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMPTZ,
    duration_seconds REAL DEFAULT 0.0,
    success BOOLEAN DEFAULT TRUE,
    feedback TEXT
);

-- Индексы для эпизодов
CREATE INDEX IF NOT EXISTS idx_episodes_timestamp ON episodes(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_episodes_topic ON episodes(topic);
CREATE INDEX IF NOT EXISTS idx_episodes_significance ON episodes(significance DESC);
CREATE INDEX IF NOT EXISTS idx_episodes_user_id ON episodes(user_id);
CREATE INDEX IF NOT EXISTS idx_episodes_intent ON episodes(intent);

-- Связи между эпизодами
CREATE TABLE IF NOT EXISTS episode_relations (
    id BIGSERIAL PRIMARY KEY,
    episode_id TEXT NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    related_id TEXT NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    relation_type TEXT DEFAULT 'related',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episode_relations_episode_id ON episode_relations(episode_id);
CREATE INDEX IF NOT EXISTS idx_episode_relations_related_id ON episode_relations(related_id);

-- === Семантическая память ===

CREATE TABLE IF NOT EXISTS semantic_knowledge (
    id TEXT PRIMARY KEY,
    knowledge_type TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT DEFAULT '',
    procedure_steps JSONB DEFAULT '[]',
    triggers JSONB DEFAULT '[]',
    success_rate REAL DEFAULT 0.5,
    related_concepts JSONB DEFAULT '[]',
    examples JSONB DEFAULT '[]',
    parent_knowledge TEXT,
    derived_from JSONB DEFAULT '[]',
    confidence REAL DEFAULT 0.5,
    source TEXT DEFAULT 'unknown',
    created_at TIMESTAMPTZ NOT NULL,
    last_accessed TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0,
    last_modified TIMESTAMPTZ,
    tags JSONB DEFAULT '[]',
    domain TEXT DEFAULT 'general'
);

-- Индексы для семантической памяти
CREATE INDEX IF NOT EXISTS idx_semantic_type ON semantic_knowledge(knowledge_type);
CREATE INDEX IF NOT EXISTS idx_semantic_domain ON semantic_knowledge(domain);
CREATE INDEX IF NOT EXISTS idx_semantic_confidence ON semantic_knowledge(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_semantic_created ON semantic_knowledge(created_at DESC);

-- Таблица применений процедур
CREATE TABLE IF NOT EXISTS procedure_applications (
    id BIGSERIAL PRIMARY KEY,
    procedure_id TEXT NOT NULL REFERENCES semantic_knowledge(id) ON DELETE CASCADE,
    context TEXT NOT NULL,
    success BOOLEAN DEFAULT TRUE,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    feedback TEXT
);

CREATE INDEX IF NOT EXISTS idx_procedure_applications_procedure_id ON procedure_applications(procedure_id);
CREATE INDEX IF NOT EXISTS idx_procedure_applications_applied_at ON procedure_applications(applied_at);

-- === RLS политики ===

ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE episode_relations ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic_knowledge ENABLE ROW LEVEL SECURITY;
ALTER TABLE procedure_applications ENABLE ROW LEVEL SECURITY;

-- Service role полный доступ
CREATE POLICY "Service role full access episodes" ON episodes TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access episode_relations" ON episode_relations TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access semantic_knowledge" ON semantic_knowledge TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access procedure_applications" ON procedure_applications TO service_role USING (true) WITH CHECK (true);

-- Anon read access
CREATE POLICY "Anon read episodes" ON episodes FOR SELECT TO anon USING (true);
CREATE POLICY "Anon read episode_relations" ON episode_relations FOR SELECT TO anon USING (true);
CREATE POLICY "Anon read semantic_knowledge" ON semantic_knowledge FOR SELECT TO anon USING (true);
CREATE POLICY "Anon read procedure_applications" ON procedure_applications FOR SELECT TO anon USING (true);
