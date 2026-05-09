-- Исправление SECURITY DEFINER для dialog_stats
-- Создаём view без SECURITY DEFINER и добавляем RLS политики

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

-- Включаем RLS для view (если поддерживается)
-- ALTER VIEW public.dialog_stats SET (security_barrier = true);

-- Даём права authenticated пользователям
GRANT SELECT ON public.dialog_stats TO authenticated;
GRANT SELECT ON public.dialog_stats TO anon;

-- Альтернативный вариант: создаём функцию вместо view
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
SECURITY DEFINER -- Явно указываем SECURITY DEFINER с правильными проверками
LANGUAGE sql
STABLE
AS $$
BEGIN
    -- Если user_id не указан, используем текущего пользователя
    IF p_user_id IS NULL THEN
        p_user_id := auth.uid();
    END IF;
    
    -- Проверяем что пользователь имеет доступ только к своим данным
    IF auth.uid() IS DISTINCT FROM p_user_id AND 
       NOT EXISTS (SELECT 1 FROM auth.users WHERE id = auth.uid() AND raw_user_meta_data->>'is_admin' = 'true') THEN
        RAISE EXCEPTION 'Access denied';
    END IF;
    
    RETURN QUERY
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
    WHERE d.user_id = p_user_id
    GROUP BY d.id, d.user_id, d.title, d.created_at, d.updated_at
    ORDER BY d.updated_at DESC;
END;
$$;

-- Даём права на функцию
GRANT EXECUTE ON FUNCTION public.get_user_dialog_stats(uuid) TO authenticated;
