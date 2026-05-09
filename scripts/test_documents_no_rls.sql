-- Drop all existing policies first
DROP POLICY IF EXISTS "Users can view own documents" ON public.documents;
DROP POLICY IF EXISTS "Users can insert own documents" ON public.documents;
DROP POLICY IF EXISTS "Users can update own documents" ON public.documents;
DROP POLICY IF EXISTS "Users can delete own documents" ON public.documents;

-- Enable RLS
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

-- Create permissive policies
CREATE POLICY "allow_authenticated_view_documents" ON public.documents FOR SELECT TO authenticated USING (true);
CREATE POLICY "allow_authenticated_insert_documents" ON public.documents FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "allow_authenticated_update_documents" ON public.documents FOR UPDATE TO authenticated USING (true);
CREATE POLICY "allow_authenticated_delete_documents" ON public.documents FOR DELETE TO authenticated USING (true);

-- Same for collections
DROP POLICY IF EXISTS "Users can view own collections" ON public.document_collections;
DROP POLICY IF EXISTS "Users can insert own collections" ON public.document_collections;
DROP POLICY IF EXISTS "Users can update own collections" ON public.document_collections;
DROP POLICY IF EXISTS "Users can delete own collections" ON public.document_collections;

ALTER TABLE public.document_collections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow_authenticated_view_collections" ON public.document_collections FOR SELECT TO authenticated USING (true);
CREATE POLICY "allow_authenticated_insert_collections" ON public.document_collections FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "allow_authenticated_update_collections" ON public.document_collections FOR UPDATE TO authenticated USING (true);
CREATE POLICY "allow_authenticated_delete_collections" ON public.document_collections FOR DELETE TO authenticated USING (true);