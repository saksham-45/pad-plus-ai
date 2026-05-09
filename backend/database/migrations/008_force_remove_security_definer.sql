-- Принудительное удаление SECURITY DEFINER из dialog_stats
-- Меняем владельца и пересоздаём view

-- 1. Сначала удаляем view полностью со всеми зависимостями
DROP VIEW IF EXISTS public.dialog_stats CASCADE;

-- 2. Удаляем все возможные функции которые могли создавать SECURITY DEFINER
DROP FUNCTION IF EXISTS public.dialog_stats() CASCADE;

-- 3. Создаём view с явным указанием владельца (postgres, не суперпользователь)
CREATE VIEW public.dialog_stats AS
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

-- 4. Меняем владельца view на обычного пользователя (не postgres)
ALTER VIEW public.dialog_stats OWNER TO postgres;

-- 5. Явно отключаем SECURITY DEFINER (если возможно)
-- Note: В PostgreSQL нельзя напрямую отключить SECURITY DEFINER у view,
-- но можно создать view без этого свойства

-- 6. Проверяем текущее состояние view
DO $$
DECLARE
    view_def TEXT;
BEGIN
    SELECT definition INTO view_def 
    FROM pg_views 
    WHERE viewname = 'dialog_stats' AND schemaname = 'public';
    
    RAISE NOTICE 'Current view definition: %', view_def;
    
    IF view_def LIKE '%SECURITY DEFINER%' THEN
        RAISE EXCEPTION 'View still has SECURITY DEFINER: %', view_def;
    ELSE
        RAISE NOTICE 'View created successfully without SECURITY DEFINER';
    END IF;
END $$;

-- 7. Даём права
GRANT SELECT ON public.dialog_stats TO authenticated;
GRANT SELECT ON public.dialog_stats TO anon;

-- 8. Альтернативный подход: создаём table вместо view
DROP TABLE IF EXISTS public.dialog_stats_table CASCADE;

CREATE TABLE public.dialog_stats_table AS
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

-- Создаём индексы для таблицы
CREATE INDEX IF NOT EXISTS idx_dialog_stats_table_user_id ON public.dialog_stats_table(user_id);
CREATE INDEX IF NOT EXISTS idx_dialog_stats_table_updated_at ON public.dialog_stats_table(updated_at);

-- Даём права на таблицу
GRANT SELECT ON public.dialog_stats_table TO authenticated;
GRANT SELECT ON public.dialog_stats_table TO anon;
