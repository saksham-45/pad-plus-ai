-- Исправление SECURITY DEFINER для dialog_stats (простой вариант)
-- Удаляем view с SECURITY DEFINER и создаём безопасный вариант

-- Удаляем старый view
DROP VIEW IF EXISTS public.dialog_stats;

-- Создаём новый view без SECURITY DEFINER
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

-- Включаем RLS для view (PostgreSQL 15+)
-- ALTER VIEW public.dialog_stats SET (security_barrier = true);

-- Даём права authenticated пользователям
GRANT SELECT ON public.dialog_stats TO authenticated;
GRANT SELECT ON public.dialog_stats TO anon;

-- Создаём безопасную функцию для получения статистики пользователя
DROP FUNCTION IF EXISTS public.get_user_dialog_stats(uuid);

CREATE OR REPLACE FUNCTION public.get_user_dialog_stats(p_user_id UUID DEFAULT NULL)
RETURNS TABLE (
    id UUID,
    user_id UUID,
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    message_count BIGINT,
    last_message_at TIMESTAMP WITH TIME ZONE,
    duration_seconds DOUBLE PRECISION
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
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
    WHERE d.user_id = COALESCE(p_user_id, auth.uid())
      AND d.user_id = auth.uid()  -- Дополнительная проверка безопасности
    GROUP BY d.id, d.user_id, d.title, d.created_at, d.updated_at
    ORDER BY d.updated_at DESC;
$$;

-- Даём права на функцию
GRANT EXECUTE ON FUNCTION public.get_user_dialog_stats(uuid) TO authenticated;
