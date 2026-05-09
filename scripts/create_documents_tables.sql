-- Создание таблицы документов с RLS

-- 1. Создаём таблицу documents
DROP TABLE IF EXISTS public.documents CASCADE;

CREATE TABLE public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    file_url TEXT,
    file_path TEXT,
    collection_id UUID,
    status TEXT DEFAULT 'pending',
    summary TEXT,
    tags TEXT[],
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Включаем RLS
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

-- 3. Создаём политики для documents
-- Полная доступность для владельца
DROP POLICY IF EXISTS "Users can view own documents" ON public.documents;
CREATE POLICY "Users can view own documents"
ON public.documents FOR SELECT
USING ((auth.uid())::text = (user_id)::text);

DROP POLICY IF EXISTS "Users can insert own documents" ON public.documents;
CREATE POLICY "Users can insert own documents"
ON public.documents FOR INSERT
WITH CHECK ((auth.uid())::text = (user_id)::text);

DROP POLICY IF EXISTS "Users can update own documents" ON public.documents;
CREATE POLICY "Users can update own documents"
ON public.documents FOR UPDATE
USING ((auth.uid())::text = (user_id)::text);

DROP POLICY IF EXISTS "Users can delete own documents" ON public.documents;
CREATE POLICY "Users can delete own documents"
ON public.documents FOR DELETE
USING ((auth.uid())::text = (user_id)::text);

-- 4. Создаём таблицу collections если нет
DROP TABLE IF EXISTS public.document_collections CASCADE;

CREATE TABLE public.document_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Включаем RLS для collections
ALTER TABLE public.document_collections ENABLE ROW LEVEL SECURITY;

-- 6. Политики для collections
DROP POLICY IF EXISTS "Users can view own collections" ON public.document_collections;
CREATE POLICY "Users can view own collections"
ON public.document_collections FOR SELECT
USING ((auth.uid())::text = (user_id)::text);

DROP POLICY IF EXISTS "Users can insert own collections" ON public.document_collections;
CREATE POLICY "Users can insert own collections"
ON public.document_collections FOR INSERT
WITH CHECK ((auth.uid())::text = (user_id)::text);

DROP POLICY IF EXISTS "Users can update own collections" ON public.document_collections;
CREATE POLICY "Users can update own collections"
ON public.document_collections FOR UPDATE
USING ((auth.uid())::text = (user_id)::text);

DROP POLICY IF EXISTS "Users can delete own collections" ON public.document_collections;
CREATE POLICY "Users can delete own collections"
ON public.document_collections FOR DELETE
USING ((auth.uid())::text = (user_id)::text);

-- 7. Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON public.documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_collection_id ON public.documents(collection_id);
CREATE INDEX IF NOT EXISTS idx_collections_user_id ON public.document_collections(user_id);

-- 8. Проверяем создание
SELECT 'Tables created successfully!' as status;
