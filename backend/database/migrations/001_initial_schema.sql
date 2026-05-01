-- ============================================================================
-- PAD+ AI v4.0 — Database Schema
-- PostgreSQL + Supabase
-- ============================================================================

-- ============================================================================
-- USERS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    email_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- Индексы для ускорения поиска
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- ============================================================================
-- USER API KEYS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    provider_display_name TEXT,
    name TEXT,
    api_key_encrypted TEXT NOT NULL,
    model_preference TEXT DEFAULT 'auto',
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- Ограничения
    CONSTRAINT check_provider CHECK (provider IN (
        'openrouter', 'google', 'openai', 'anthropic', 
        'groq', 'ollama', 'gemini', 'gigachat'
    ))
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_keys_user_id ON user_api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_keys_provider ON user_api_keys(provider);
CREATE INDEX IF NOT EXISTS idx_keys_active ON user_api_keys(is_active);

-- ============================================================================
-- CHAT SESSIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    model_used TEXT,
    provider_used TEXT,
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON chat_sessions(created_at);

-- ============================================================================
-- CHAT MESSAGES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    token_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Индекс для быстрого поиска по сессии
    CONSTRAINT fk_session FOREIGN KEY (session_id) 
        REFERENCES chat_sessions(id) ON DELETE CASCADE
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_role ON chat_messages(role);

-- ============================================================================
-- PROVIDER CONFIGS TABLE (опционально, для системных ключей)
-- ============================================================================

CREATE TABLE IF NOT EXISTS provider_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    api_key_encrypted TEXT,
    model_default TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- SYSTEM PROVIDER DEFAULTS (удалено - теперь только пользовательские ключи)
-- ============================================================================

-- ============================================================================
-- TRIGGERS (автоматическое обновление updated_at)
-- ============================================================================

-- Функция для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггеры для таблиц
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_api_keys_updated_at
    BEFORE UPDATE ON user_api_keys
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_sessions_updated_at
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) — Supabase specific
-- ============================================================================

-- Включаем RLS для таблиц
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- Policies для users
CREATE POLICY "Users can view own data"
    ON users FOR SELECT
    USING (auth.uid()::text = id::text);

CREATE POLICY "Users can insert own data"
    ON users FOR INSERT
    WITH CHECK (auth.uid()::text = id::text);

CREATE POLICY "Users can update own data"
    ON users FOR UPDATE
    USING (auth.uid()::text = id::text);

-- Policies для api_keys
CREATE POLICY "Users can view own keys"
    ON user_api_keys FOR SELECT
    USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own keys"
    ON user_api_keys FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own keys"
    ON user_api_keys FOR UPDATE
    USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can delete own keys"
    ON user_api_keys FOR DELETE
    USING (auth.uid()::text = user_id::text);

-- Policies для chat_sessions
CREATE POLICY "Users can view own sessions"
    ON chat_sessions FOR SELECT
    USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own sessions"
    ON chat_sessions FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own sessions"
    ON chat_sessions FOR UPDATE
    USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can delete own sessions"
    ON chat_sessions FOR DELETE
    USING (auth.uid()::text = user_id::text);

-- Policies для chat_messages
CREATE POLICY "Users can view own messages"
    ON chat_messages FOR SELECT
    USING (
        session_id IN (
            SELECT id FROM chat_sessions 
            WHERE user_id::text = auth.uid()::text
        )
    );

CREATE POLICY "Users can insert own messages"
    ON chat_messages FOR INSERT
    WITH CHECK (
        session_id IN (
            SELECT id FROM chat_sessions 
            WHERE user_id::text = auth.uid()::text
        )
    );

-- ============================================================================
-- VIEW для статистики пользователя
-- ============================================================================

CREATE OR REPLACE VIEW user_stats AS
SELECT 
    u.id,
    u.email,
    COUNT(DISTINCT s.id) as total_sessions,
    COUNT(DISTINCT m.id) as total_messages,
    COUNT(DISTINCT k.id) as total_keys,
    MAX(s.last_message_at) as last_activity
FROM users u
LEFT JOIN chat_sessions s ON u.id = s.user_id
LEFT JOIN chat_messages m ON s.id = m.session_id
LEFT JOIN user_api_keys k ON u.id = k.user_id
GROUP BY u.id, u.email;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
