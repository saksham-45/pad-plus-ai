-- ============================================================================
-- PAD+ AI v3.5 — Documents and Collections Migration
-- ============================================================================

-- ============================================================================
-- DOCUMENTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    file_url TEXT,
    file_path TEXT,
    collection_id UUID,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    tags TEXT[] DEFAULT '{}',
    summary TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_collection_id ON documents(collection_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);

-- ============================================================================
-- DOCUMENT COLLECTIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_document_collections_user_id ON document_collections(user_id);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Триггер для обновления updated_at в documents
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Триггер для обновления updated_at в document_collections
CREATE TRIGGER update_document_collections_updated_at
    BEFORE UPDATE ON document_collections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Включаем RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_collections ENABLE ROW LEVEL SECURITY;

-- Policies для documents
CREATE POLICY "Users can view own documents"
    ON documents FOR SELECT
    USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own documents"
    ON documents FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own documents"
    ON documents FOR UPDATE
    USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can delete own documents"
    ON documents FOR DELETE
    USING (auth.uid()::text = user_id::text);

-- Policies для document_collections
CREATE POLICY "Users can view own collections"
    ON document_collections FOR SELECT
    USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own collections"
    ON document_collections FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own collections"
    ON document_collections FOR UPDATE
    USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can delete own collections"
    ON document_collections FOR DELETE
    USING (auth.uid()::text = user_id::text);

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================