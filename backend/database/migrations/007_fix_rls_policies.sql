-- Исправление RLS политик для Supabase безопасности
-- Применяется после создания таблиц

-- Включаем RLS для всех таблиц
ALTER TABLE public.rag_dialogs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public._migrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.provider_configs ENABLE ROW LEVEL SECURITY;

-- Политики для rag_dialogs
-- Пользователи могут видеть только свои диалоги
CREATE POLICY "Users can view own rag_dialogs" ON public.rag_dialogs
    FOR SELECT USING (auth.uid()::text = user_id);

-- Пользователи могут создавать только свои диалоги
CREATE POLICY "Users can insert own rag_dialogs" ON public.rag_dialogs
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

-- Пользователи могут обновлять только свои диалоги
CREATE POLICY "Users can update own rag_dialogs" ON public.rag_dialogs
    FOR UPDATE USING (auth.uid()::text = user_id);

-- Пользователи могут удалять только свои диалоги
CREATE POLICY "Users can delete own rag_dialogs" ON public.rag_dialogs
    FOR DELETE USING (auth.uid()::text = user_id);

-- Политики для provider_configs
-- Пользователи могут видеть только свои конфигурации провайдеров
CREATE POLICY "Users can view own provider_configs" ON public.provider_configs
    FOR SELECT USING (auth.uid()::text = user_id);

-- Пользователи могут создавать только свои конфигурации
CREATE POLICY "Users can insert own provider_configs" ON public.provider_configs
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

-- Пользователи могут обновлять только свои конфигурации
CREATE POLICY "Users can update own provider_configs" ON public.provider_configs
    FOR UPDATE USING (auth.uid()::text = user_id);

-- Пользователи могут удалять только свои конфигурации
CREATE POLICY "Users can delete own provider_configs" ON public.provider_configs
    FOR DELETE USING (auth.uid()::text = user_id);

-- Политики для _migrations (административная таблица)
-- Только аутентифицированные пользователи могут видеть миграции
CREATE POLICY "Authenticated users can view migrations" ON public._migrations
    FOR SELECT USING (auth.role() = 'authenticated');

-- Только суперпользователи могут изменять миграции
CREATE POLICY "Superusers can manage migrations" ON public._migrations
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
LEFT JOIN public.dialog_messages dm ON d.id = dm.dialog_id
GROUP BY d.id, d.user_id, d.title, d.created_at, d.updated_at
ORDER BY d.updated_at DESC;

-- GRANT permissions
GRANT SELECT ON public.dialog_stats TO authenticated;
GRANT SELECT ON public.dialog_stats TO anon;

-- Обновляем permissions для других таблиц
GRANT SELECT, INSERT, UPDATE, DELETE ON public.rag_dialogs TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.provider_configs TO authenticated;
GRANT SELECT ON public._migrations TO authenticated;
