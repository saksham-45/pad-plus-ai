-- ============================================================================
-- PAD+ AI v4.0 — RLS Policies для Supabase Auth
-- ============================================================================
-- Этот SQL нужно выполнить в Supabase SQL Editor
-- ============================================================================

-- Включаем RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- USERS TABLE POLICIES
-- ============================================================================

-- Разрешаем пользователям читать свои данные
DROP POLICY IF EXISTS "Users can view own data" ON users;
CREATE POLICY "Users can view own data"
    ON users FOR SELECT
    USING (auth.uid() = id);

-- Разрешаем пользователям обновлять свои данные
DROP POLICY IF EXISTS "Users can update own data" ON users;
CREATE POLICY "Users can update own data"
    ON users FOR UPDATE
    USING (auth.uid() = id);

-- Разрешаем вставку (для регистрации)
DROP POLICY IF EXISTS "Users can insert own data" ON users;
CREATE POLICY "Users can insert own data"
    ON users FOR INSERT
    WITH CHECK (auth.uid() = id);

-- ============================================================================
-- USER API KEYS TABLE POLICIES
-- ============================================================================

-- Просмотр своих ключей
DROP POLICY IF EXISTS "Users can view own keys" ON user_api_keys;
CREATE POLICY "Users can view own keys"
    ON user_api_keys FOR SELECT
    USING (auth.uid() = user_id);

-- Вставка своих ключей
DROP POLICY IF EXISTS "Users can insert own keys" ON user_api_keys;
CREATE POLICY "Users can insert own keys"
    ON user_api_keys FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Обновление своих ключей
DROP POLICY IF EXISTS "Users can update own keys" ON user_api_keys;
CREATE POLICY "Users can update own keys"
    ON user_api_keys FOR UPDATE
    USING (auth.uid() = user_id);

-- Удаление своих ключей
DROP POLICY IF EXISTS "Users can delete own keys" ON user_api_keys;
CREATE POLICY "Users can delete own keys"
    ON user_api_keys FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- CHAT SESSIONS TABLE POLICIES
-- ============================================================================

-- Просмотр своих сессий
DROP POLICY IF EXISTS "Users can view own sessions" ON chat_sessions;
CREATE POLICY "Users can view own sessions"
    ON chat_sessions FOR SELECT
    USING (auth.uid() = user_id);

-- Вставка своих сессий
DROP POLICY IF EXISTS "Users can insert own sessions" ON chat_sessions;
CREATE POLICY "Users can insert own sessions"
    ON chat_sessions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Обновление своих сессий
DROP POLICY IF EXISTS "Users can update own sessions" ON chat_sessions;
CREATE POLICY "Users can update own sessions"
    ON chat_sessions FOR UPDATE
    USING (auth.uid() = user_id);

-- Удаление своих сессий
DROP POLICY IF EXISTS "Users can delete own sessions" ON chat_sessions;
CREATE POLICY "Users can delete own sessions"
    ON chat_sessions FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- CHAT MESSAGES TABLE POLICIES
-- ============================================================================

-- Просмотр своих сообщений
DROP POLICY IF EXISTS "Users can view own messages" ON chat_messages;
CREATE POLICY "Users can view own messages"
    ON chat_messages FOR SELECT
    USING (
        session_id IN (
            SELECT id FROM chat_sessions 
            WHERE user_id = auth.uid()
        )
    );

-- Вставка своих сообщений
DROP POLICY IF EXISTS "Users can insert own messages" ON chat_messages;
CREATE POLICY "Users can insert own messages"
    ON chat_messages FOR INSERT
    WITH CHECK (
        session_id IN (
            SELECT id FROM chat_sessions 
            WHERE user_id = auth.uid()
        )
    );

-- Удаление своих сообщений
DROP POLICY IF EXISTS "Users can delete own messages" ON chat_messages;
CREATE POLICY "Users can delete own messages"
    ON chat_messages FOR DELETE
    USING (
        session_id IN (
            SELECT id FROM chat_sessions 
            WHERE user_id = auth.uid()
        )
    );

-- ============================================================================
-- SERVICE ROLE POLICY (для админских операций)
-- ============================================================================

-- Эта политика позволяет service_role ключу делать всё
-- (используется только на бэкенде)

-- ============================================================================
-- END OF RLS POLICIES
-- ============================================================================
