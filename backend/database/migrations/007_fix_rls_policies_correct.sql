-- Исправление RLS политик для Supabase безопасности (только существующие таблицы)
-- Применяется после создания таблиц

-- Включаем RLS только для существующих таблиц
ALTER TABLE public.provider_configs ENABLE ROW LEVEL SECURITY;

-- Политики для provider_configs (системная таблица без user_id)
-- Только аутентифицированные пользователи могут видеть конфигурации
CREATE POLICY "Authenticated users can view provider_configs" ON public.provider_configs
    FOR SELECT USING (auth.role() = 'authenticated');

-- Только суперпользователи могут изменять конфигурации провайдеров
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
GRANT SELECT ON public.provider_configs TO authenticated;

-- Примечание: таблицы rag_dialogs и _migrations не существуют в схеме
-- Если они нужны, создайте их отдельной миграцией
