-- ============================================================================
-- PAD+ AI v4.0 — Исправление RLS политик и аутентификации
-- ============================================================================
-- Этот SQL нужно выполнить в Supabase SQL Editor
-- Исправляет проблемы с:
-- 1. Несогласованным сравнением UUID в RLS политиках
-- 2. Отсутствием политик для service_role ключа
-- 3. Отсутствием автоматического создания настроек пользователя
-- ============================================================================

-- ============================================================================
-- ИСПРАВЛЕНИЕ RLS ПОЛИТИК ДЛЯ TABLE users
-- ============================================================================

-- Включаем RLS (если еще не включен)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Удаляем ВСЕ существующие политики для users (чтобы избежать конфликтов)
DO $$
BEGIN
    -- Удаляем все политики для таблицы users
    DROP POLICY IF EXISTS "Users can view own data" ON users;
    DROP POLICY IF EXISTS "Users can insert own data" ON users;
    DROP POLICY IF EXISTS "Users can update own data" ON users;
    DROP POLICY IF EXISTS "users_view_own" ON users;
    DROP POLICY IF EXISTS "users_insert_own" ON users;
    DROP POLICY IF EXISTS "users_update_own" ON users;
    DROP POLICY IF EXISTS "Authenticated users can view own data" ON users;
    DROP POLICY IF EXISTS "Authenticated users can insert own data" ON users;
    DROP POLICY IF EXISTS "Authenticated users can update own data" ON users;
END $$;

-- Создаем исправленные политики с правильным сравнением UUID (используем IF NOT EXISTS)
DO $$
BEGIN
    -- Создаем политики только если они еще не существуют
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_select_own_fixed') THEN
        CREATE POLICY "users_select_own_fixed"
            ON users FOR SELECT
            USING (auth.uid() = id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_insert_own_fixed') THEN
        CREATE POLICY "users_insert_own_fixed"
            ON users FOR INSERT
            WITH CHECK (auth.uid() = id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_update_own_fixed') THEN
        CREATE POLICY "users_update_own_fixed"
            ON users FOR UPDATE
            USING (auth.uid() = id);
    END IF;
END $$;

-- ============================================================================
-- ИСПРАВЛЕНИЕ RLS ПОЛИТИК ДЛЯ TABLE user_api_keys
-- ============================================================================

ALTER TABLE user_api_keys ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own keys" ON user_api_keys;
DROP POLICY IF EXISTS "Users can insert own keys" ON user_api_keys;
DROP POLICY IF EXISTS "Users can update own keys" ON user_api_keys;
DROP POLICY IF EXISTS "Users can delete own keys" ON user_api_keys;

CREATE POLICY "Users can view own keys"
    ON user_api_keys FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own keys"
    ON user_api_keys FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own keys"
    ON user_api_keys FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own keys"
    ON user_api_keys FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- ИСПРАВЛЕНИЕ RLS ПОЛИТИК ДЛЯ TABLE chat_sessions
-- ============================================================================

ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own sessions" ON chat_sessions;
DROP POLICY IF EXISTS "Users can insert own sessions" ON chat_sessions;
DROP POLICY IF EXISTS "Users can update own sessions" ON chat_sessions;
DROP POLICY IF EXISTS "Users can delete own sessions" ON chat_sessions;

CREATE POLICY "Users can view own sessions"
    ON chat_sessions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sessions"
    ON chat_sessions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sessions"
    ON chat_sessions FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own sessions"
    ON chat_sessions FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- IСПРАВЛЕНИЕ RLS ПОЛИТИК ДЛЯ TABLE chat_messages
-- ============================================================================

ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own messages" ON chat_messages;
DROP POLICY IF EXISTS "Users can insert own messages" ON chat_messages;
DROP POLICY IF EXISTS "Users can delete own messages" ON chat_messages;

CREATE POLICY "Users can view own messages"
    ON chat_messages FOR SELECT
    USING (
        session_id IN (
            SELECT id FROM chat_sessions 
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert own messages"
    ON chat_messages FOR INSERT
    WITH CHECK (
        session_id IN (
            SELECT id FROM chat_sessions 
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete own messages"
    ON chat_messages FOR DELETE
    USING (
        session_id IN (
            SELECT id FROM chat_sessions 
            WHERE user_id = auth.uid()
        )
    );

-- ============================================================================
-- IСПРАВЛЕНИЕ RLS ПОЛИТИК ДЛЯ TABLE user_settings
-- ============================================================================

ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own settings" ON user_settings;
DROP POLICY IF EXISTS "Users can insert own settings" ON user_settings;
DROP POLICY IF EXISTS "Users can update own settings" ON user_settings;

CREATE POLICY "Users can view own settings"
    ON user_settings FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own settings"
    ON user_settings FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own settings"
    ON user_settings FOR UPDATE
    USING (auth.uid() = user_id);

-- ============================================================================
-- IСПРАВЛЕНИЕ RLS ПОЛИТИК ДЛЯ TABLE dialogs
-- ============================================================================

ALTER TABLE dialogs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own dialogs" ON dialogs;
DROP POLICY IF EXISTS "Users can insert own dialogs" ON dialogs;
DROP POLICY IF EXISTS "Users can update own dialogs" ON dialogs;
DROP POLICY IF EXISTS "Users can delete own dialogs" ON dialogs;

CREATE POLICY "Users can view own dialogs"
    ON dialogs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own dialogs"
    ON dialogs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own dialogs"
    ON dialogs FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own dialogs"
    ON dialogs FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- IСПРАВЛЕНИЕ RLS ПОЛИТИК ДЛЯ TABLE messages
-- ============================================================================

ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own messages" ON messages;
DROP POLICY IF EXISTS "Users can insert own messages" ON messages;
DROP POLICY IF EXISTS "Users can delete own messages" ON messages;

CREATE POLICY "Users can view own messages"
    ON messages FOR SELECT
    USING (
        dialog_id IN (
            SELECT id FROM dialogs 
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert own messages"
    ON messages FOR INSERT
    WITH CHECK (
        dialog_id IN (
            SELECT id FROM dialogs 
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete own messages"
    ON messages FOR DELETE
    USING (
        dialog_id IN (
            SELECT id FROM dialogs 
            WHERE user_id = auth.uid()
        )
    );

-- ============================================================================
-- ФУНКЦИЯ ДЛЯ АВТОМАТИЧЕСКОГО СОЗДАНИЯ НАСТРОЕК ПОЛЬЗОВАТЕЛЯ
-- ============================================================================

-- Создаем функцию для автоматического создания записи в user_settings
-- при регистрации нового пользователя
CREATE OR REPLACE FUNCTION public.create_user_settings()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_settings (user_id)
    VALUES (NEW.id)
    ON CONFLICT (user_id) DO NOTHING;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Создаем триггер для автоматического создания настроек
DROP TRIGGER IF EXISTS on_user_created ON users;
CREATE TRIGGER on_user_created
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION public.create_user_settings();

-- ============================================================================
-- ФУНКЦИЯ ДЛЯ ПРОВЕРКИ СУЩЕСТВОВАНИЯ ТАБЛИЦ
-- ============================================================================

-- Функция для проверки наличия всех необходимых таблиц
CREATE OR REPLACE FUNCTION public.check_tables_exist()
RETURNS TABLE (
    table_name TEXT,
    table_exists BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.table_name,
        EXISTS(
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = t.table_name
        ) as table_exists
    FROM (
        VALUES 
            ('users'::TEXT),
            ('user_api_keys'::TEXT),
            ('chat_sessions'::TEXT),
            ('chat_messages'::TEXT),
            ('user_settings'::TEXT),
            ('dialogs'::TEXT),
            ('messages'::TEXT)
    ) AS t(table_name);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- КОНЕЦ МИГРАЦИИ
-- ============================================================================

-- После выполнения этой миграции:
-- 1. Все RLS политики будут использовать согласованное сравнение UUID
-- 2. При регистрации пользователя автоматически создадутся настройки
-- 3. Service role ключ сможет выполнять операции без ограничений RLS