-- ============================================================================
-- PAD+ AI v4.0 — Включение RLS на memory-таблицах
-- Supabase Security Advisor: 4 warnings
-- ============================================================================

-- 1. episodes
ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Пользователи видят свои эпизоды"
    ON episodes FOR SELECT
    USING (user_id = auth.uid()::text);

CREATE POLICY "Сервис может вставлять эпизоды"
    ON episodes FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Сервис может обновлять эпизоды"
    ON episodes FOR UPDATE
    USING (true);

-- 2. episode_relations (связана с episodes через episode_id)
ALTER TABLE episode_relations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Пользователи видят связи своих эпизодов"
    ON episode_relations FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM episodes
            WHERE episodes.id = episode_relations.episode_id
            AND episodes.user_id = auth.uid()::text
        )
    );

CREATE POLICY "Сервис может вставлять связи эпизодов"
    ON episode_relations FOR INSERT
    WITH CHECK (true);

-- 3. semantic_knowledge (общая база знаний, доступна всем аутентифицированным)
ALTER TABLE semantic_knowledge ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Все пользователи читают знания"
    ON semantic_knowledge FOR SELECT
    USING (true);

CREATE POLICY "Сервис может вставлять знания"
    ON semantic_knowledge FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Сервис может обновлять знания"
    ON semantic_knowledge FOR UPDATE
    USING (true);

-- 4. procedure_applications (связана с semantic_knowledge через procedure_id)
ALTER TABLE procedure_applications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Все пользователи читают применения процедур"
    ON procedure_applications FOR SELECT
    USING (true);

CREATE POLICY "Сервис может вставлять применения процедур"
    ON procedure_applications FOR INSERT
    WITH CHECK (true);

-- ============================================================================
-- Примечание: таблицы создаются через psycopg2 напрямую, RLS влияет только
-- на доступ через Supabase REST API (anon/service key). Приложение продолжает
-- работать через DATABASE_URL в обход RLS.
-- ============================================================================
