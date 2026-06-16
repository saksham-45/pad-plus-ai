-- ============================================================================
-- PAD+ AI v3.5 — User Settings and Dialog History Migration
-- ============================================================================

-- ============================================================================
-- USER SETTINGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    -- Persona Settings
    persona_tone VARCHAR(50) DEFAULT 'friendly',
    persona_detail_level VARCHAR(50) DEFAULT 'moderate',
    persona_emotion_level VARCHAR(50) DEFAULT 'balanced',
    persona_specialization VARCHAR(50) DEFAULT 'general',
    
    -- Notification Settings
    notification_email BOOLEAN DEFAULT true,
    notification_push BOOLEAN DEFAULT false,
    notification_sound BOOLEAN DEFAULT true,
    notification_frequency VARCHAR(20) DEFAULT 'immediate',
    
    -- Appearance Settings
    theme VARCHAR(20) DEFAULT 'dark',
    font_size VARCHAR(10) DEFAULT 'medium',
    compact_mode BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);

-- ============================================================================
-- DIALOGS TABLE (для истории диалогов)
-- ============================================================================

CREATE TABLE IF NOT EXISTS dialogs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message_count INTEGER DEFAULT 0,
    is_favorite BOOLEAN DEFAULT false,
    last_message_at TIMESTAMP WITH TIME ZONE
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_dialogs_user_id ON dialogs(user_id);
CREATE INDEX IF NOT EXISTS idx_dialogs_created_at ON dialogs(created_at);
CREATE INDEX IF NOT EXISTS idx_dialogs_updated_at ON dialogs(updated_at);
CREATE INDEX IF NOT EXISTS idx_dialogs_favorite ON dialogs(is_favorite);

-- ============================================================================
-- MESSAGES TABLE (сообщения в диалогах)
-- ============================================================================

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dialog_id UUID REFERENCES dialogs(id) ON DELETE CASCADE,
    role VARCHAR(20) CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    model VARCHAR(100),
    provider VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    -- Индекс для быстрого поиска по диалогу
    CONSTRAINT fk_dialog FOREIGN KEY (dialog_id) 
        REFERENCES dialogs(id) ON DELETE CASCADE
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_messages_dialog_id ON messages(dialog_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);

-- Полнотекстовой поиск по сообщениям
CREATE INDEX IF NOT EXISTS idx_messages_content_fts ON messages USING gin(to_tsvector('russian', content));

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Триггер для обновления updated_at в user_settings
CREATE TRIGGER update_user_settings_updated_at
    BEFORE UPDATE ON user_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Триггер для обновления updated_at в dialogs
CREATE TRIGGER update_dialogs_updated_at
    BEFORE UPDATE ON dialogs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Триггер для обновления message_count и last_message_at в dialogs
CREATE OR REPLACE FUNCTION update_dialog_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE dialogs 
        SET message_count = message_count + 1,
            last_message_at = NEW.created_at,
            updated_at = NOW()
        WHERE id = NEW.dialog_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE dialogs 
        SET message_count = message_count - 1,
            updated_at = NOW()
        WHERE id = OLD.dialog_id;
        -- Обновляем last_message_at на последнее сообщение
        UPDATE dialogs d
        SET last_message_at = (
            SELECT MAX(m.created_at) FROM messages m WHERE m.dialog_id = d.id
        )
        WHERE d.id = NEW.dialog_id OR d.id = OLD.dialog_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_dialog_stats_after_insert
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_dialog_stats();

CREATE TRIGGER update_dialog_stats_after_delete
    AFTER DELETE ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_dialog_stats();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Включаем RLS
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE dialogs ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Policies для user_settings
CREATE POLICY "Users can view own settings"
    ON user_settings FOR SELECT
    USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own settings"
    ON user_settings FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own settings"
    ON user_settings FOR UPDATE
    USING (auth.uid()::text = user_id::text);

-- Policies для dialogs
CREATE POLICY "Users can view own dialogs"
    ON dialogs FOR SELECT
    USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own dialogs"
    ON dialogs FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own dialogs"
    ON dialogs FOR UPDATE
    USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can delete own dialogs"
    ON dialogs FOR DELETE
    USING (auth.uid()::text = user_id::text);

-- Policies для messages
CREATE POLICY "Users can view own messages"
    ON messages FOR SELECT
    USING (
        dialog_id IN (
            SELECT id FROM dialogs 
            WHERE user_id::text = auth.uid()::text
        )
    );

CREATE POLICY "Users can insert own messages"
    ON messages FOR INSERT
    WITH CHECK (
        dialog_id IN (
            SELECT id FROM dialogs 
            WHERE user_id::text = auth.uid()::text
        )
    );

CREATE POLICY "Users can delete own messages"
    ON messages FOR DELETE
    USING (
        dialog_id IN (
            SELECT id FROM dialogs 
            WHERE user_id::text = auth.uid()::text
        )
    );

-- ============================================================================
-- VIEW для статистики диалогов
-- ============================================================================

CREATE OR REPLACE VIEW dialog_stats AS
SELECT 
    d.user_id,
    COUNT(DISTINCT d.id) as total_dialogs,
    COUNT(DISTINCT CASE WHEN d.is_favorite THEN d.id END) as favorite_dialogs,
    COUNT(DISTINCT m.id) as total_messages,
    MAX(d.last_message_at) as last_activity
FROM dialogs d
LEFT JOIN messages m ON d.id = m.dialog_id
GROUP BY d.user_id;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================