-- Исправление RLS для реально существующих таблиц в Supabase
-- Удаляем существующие политики и создаём новые

-- Удаляем существующие политики
DROP POLICY IF EXISTS "Аутентифицированные пользователи могут просматривать provider_configs" ON public.provider_configs;
DROP POLICY IF EXISTS "Authenticated users can view provider_configs" ON public.provider_configs;
DROP POLICY IF EXISTS "Superusers can manage provider_configs" ON public.provider_configs;

-- Включаем RLS для всех существующих таблиц
ALTER TABLE public.rag_dialogs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public._migrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.provider_configs ENABLE ROW LEVEL SECURITY;

-- Политики для rag_dialogs
CREATE POLICY "Users can view own rag_dialogs" ON public.rag_dialogs
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own rag_dialogs" ON public.rag_dialogs
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own rag_dialogs" ON public.rag_dialogs
    FOR UPDATE USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can delete own rag_dialogs" ON public.rag_dialogs
    FOR DELETE USING (auth.uid()::text = user_id::text);

-- Политики для _migrations
CREATE POLICY "Authenticated users can view migrations" ON public._migrations
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Superusers can manage migrations" ON public._migrations
    FOR ALL USING (auth.role() = 'authenticated' AND current_setting('app.supabase_role', true) = 'service_role');

-- Политики для provider_configs
CREATE POLICY "Authenticated users can view provider_configs" ON public.provider_configs
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Superusers can manage provider_configs" ON public.provider_configs
    FOR ALL USING (auth.role() = 'authenticated' AND current_setting('app.supabase_role', true) = 'service_role');

-- Исправление SECURITY DEFINER для dialog_stats
DROP VIEW IF EXISTS public.dialog_stats;

CREATE OR REPLACE VIEW public.dialog_stats AS
SELECT 
    d.id,
    d.user_id,
    d.title,
    d.created_at,
    d.updated_at,
    COUNT(dm.id) as message_count,
    MAX(dm.created_at) as last_message_at,
    EXTRACT(EPOCH FROM (MAX(dm.created_at) - d.created_at)) as duration_seconds
FROM public.dialogs d
LEFT JOIN public.messages dm ON d.id = dm.dialog_id
GROUP BY d.id, d.user_id, d.title, d.created_at, d.updated_at
ORDER BY d.updated_at DESC;

-- GRANT permissions
GRANT SELECT ON public.dialog_stats TO authenticated;
GRANT SELECT ON public.dialog_stats TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.rag_dialogs TO authenticated;
GRANT SELECT ON public._migrations TO authenticated;
GRANT SELECT ON public.provider_configs TO authenticated;
