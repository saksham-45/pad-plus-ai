-- ============================================================================
-- PAD+ AI v3.5 — Documents Trash (Soft Delete)
-- ============================================================================

-- Добавляем поля soft-delete в таблицу documents
ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;

-- Индекс для быстрого поиска в корзине
CREATE INDEX IF NOT EXISTS idx_documents_is_deleted
    ON documents(is_deleted)
    WHERE is_deleted = TRUE;

-- Индекс для фильтрации активных документов
CREATE INDEX IF NOT EXISTS idx_documents_active
    ON documents(user_id, is_deleted, created_at DESC)
    WHERE is_deleted = FALSE;

-- Обновляем политику RLS на DELETE
DROP POLICY IF EXISTS "Users can delete own documents" ON documents;

-- Вместо DELETE разрешаем UPDATE (soft-delete через обновление)
CREATE POLICY "Users can soft-delete own documents"
    ON documents FOR UPDATE
    USING (auth.uid()::text = user_id::text);
