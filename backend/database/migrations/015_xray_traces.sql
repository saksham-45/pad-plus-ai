-- ============================================================================
-- PAD+ AI v4.0 — X-Ray Traces Table
-- Self-Healing: персистентность трейсов для MetaLearner и диагностики
-- ============================================================================

-- Таблица трейсов X-Ray
CREATE TABLE IF NOT EXISTS xray_traces (
    trace_id        UUID PRIMARY KEY,
    user_message    TEXT NOT NULL,
    response        TEXT,
    strategy        TEXT NOT NULL DEFAULT 'simple',
    intent          TEXT,
    provider        TEXT,
    model           TEXT,
    total_ms        FLOAT NOT NULL DEFAULT 0,
    success         BOOLEAN NOT NULL DEFAULT TRUE,
    confidence      FLOAT DEFAULT 0.0,
    health_score    FLOAT DEFAULT 0.0,
    spans_json      JSONB DEFAULT '[]'::jsonb,
    events_json     JSONB DEFAULT '[]'::jsonb,
    metadata_json   JSONB DEFAULT '{}'::jsonb,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_xray_traces_created_at ON xray_traces(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_xray_traces_user_id ON xray_traces(user_id);
CREATE INDEX IF NOT EXISTS idx_xray_traces_success ON xray_traces(success);
CREATE INDEX IF NOT EXISTS idx_xray_traces_strategy ON xray_traces(strategy);
CREATE INDEX IF NOT EXISTS idx_xray_traces_provider ON xray_traces(provider);

-- RLS
ALTER TABLE xray_traces ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Пользователи видят свои трейсы"
    ON xray_traces FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Сервис может вставлять трейсы"
    ON xray_traces FOR INSERT
    WITH CHECK (true);

-- Авто-очистка: удаляем трейсы старше 90 дней
CREATE OR REPLACE FUNCTION cleanup_old_xray_traces()
RETURNS void AS $$
BEGIN
    DELETE FROM xray_traces
    WHERE created_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;
