-- 020_experiences_postgres.sql
-- PostgreSQL таблица для Experience Layer
-- Замена JSON-файлов на персистентное хранение в БД

CREATE TABLE IF NOT EXISTS experiences (
    id BIGSERIAL PRIMARY KEY,
    dialog_id TEXT NOT NULL,
    user_message TEXT NOT NULL,
    ai_response TEXT,
    interaction_type TEXT NOT NULL,
    signals JSONB DEFAULT '{}',
    significance REAL DEFAULT 0.0,
    expectation TEXT DEFAULT '',
    reality TEXT DEFAULT '',
    delta TEXT DEFAULT '',
    lessons JSONB DEFAULT '[]',
    strategy_success REAL DEFAULT 0.0,
    impulse_before JSONB DEFAULT '{}',
    emotion_before JSONB DEFAULT '{}',
    persona_before JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_experiences_dialog_id ON experiences(dialog_id);
CREATE INDEX IF NOT EXISTS idx_experiences_interaction_type ON experiences(interaction_type);
CREATE INDEX IF NOT EXISTS idx_experiences_significance ON experiences(significance DESC);
CREATE INDEX IF NOT EXISTS idx_experiences_created_at ON experiences(created_at DESC);

ALTER TABLE experiences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access experiences" ON experiences TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Anon read experiences" ON experiences FOR SELECT TO anon USING (true);
