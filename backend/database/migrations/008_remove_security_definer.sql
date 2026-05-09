-- Полное удаление и пересоздание dialog_stats без SECURITY DEFINER
-- Решение проблемы с SECURITY DEFINER

-- Сначала удаляем view полностью
DROP VIEW IF EXISTS public.dialog_stats CASCADE;

-- Проверяем что view удалён
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_views WHERE viewname = 'dialog_stats' AND schemaname = 'public') THEN
        RAISE EXCEPTION 'View still exists after DROP';
    END IF;
END $$;

-- Создаём новый view БЕЗ SECURITY DEFINER
-- Важно: обычный CREATE VIEW не создаёт SECURITY DEFINER
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

-- Проверяем что view создан БЕЗ SECURITY DEFINER
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_views 
        WHERE viewname = 'dialog_stats' 
        AND schemaname = 'public'
        AND definition LIKE '%SECURITY DEFINER%'
    ) THEN
        RAISE EXCEPTION 'View still has SECURITY DEFINER';
    END IF;
END $$;

-- Даём права пользователям
GRANT SELECT ON public.dialog_stats TO authenticated;
GRANT SELECT ON public.dialog_stats TO anon;

-- Альтернатива: создаём материализованное представление (тоже без SECURITY DEFINER)
DROP MATERIALIZED VIEW IF EXISTS public.dialog_stats_mat CASCADE;

CREATE MATERIALIZED VIEW public.dialog_stats_mat AS
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

-- Даём права на материализованное представление
GRANT SELECT ON public.dialog_stats_mat TO authenticated;
GRANT SELECT ON public.dialog_stats_mat TO anon;
