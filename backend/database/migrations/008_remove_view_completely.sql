-- Простое решение: удаляем view и оставляем только table
-- Полностью избавляемся от SECURITY DEFINER

-- 1. Удаляем view полностью
DROP VIEW IF EXISTS public.dialog_stats CASCADE;

-- 2. Удаляем все связанные функции
DROP FUNCTION IF EXISTS public.dialog_stats() CASCADE;

-- 3. Удаляем старую table если существует
DROP TABLE IF EXISTS public.dialog_stats_table CASCADE;

-- 4. Создаём обычную TABLE (гарантированно без SECURITY DEFINER)
CREATE TABLE public.dialog_stats_table (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message_count BIGINT DEFAULT 0,
    last_message_at TIMESTAMP WITH TIME ZONE,
    duration_seconds DOUBLE PRECISION DEFAULT 0
);

-- 5. Создаём индексы
CREATE INDEX IF NOT EXISTS idx_dialog_stats_table_user_id ON public.dialog_stats_table(user_id);
CREATE INDEX IF NOT EXISTS idx_dialog_stats_table_updated_at ON public.dialog_stats_table(updated_at);

-- 6. Заполняем данными
INSERT INTO public.dialog_stats_table (
    id, user_id, title, created_at, updated_at, 
    message_count, last_message_at, duration_seconds
)
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

-- 7. Включаем RLS
ALTER TABLE public.dialog_stats_table ENABLE ROW LEVEL SECURITY;

-- 8. Политики безопасности
CREATE POLICY "Users can view own dialog stats" ON public.dialog_stats_table
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- 9. Даём права
GRANT SELECT ON public.dialog_stats_table TO authenticated;
GRANT SELECT ON public.dialog_stats_table TO anon;

-- 10. Проверяем что view удалён
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_views WHERE viewname = 'dialog_stats' AND schemaname = 'public') THEN
        RAISE EXCEPTION 'dialog_stats view still exists!';
    ELSE
        RAISE NOTICE 'dialog_stats view successfully removed';
    END IF;
END $$;

-- Примечание: frontend нужно будет обновить для использования dialog_stats_table вместо dialog_stats
-- или создать синоним: CREATE SYNONYM public.dialog_stats FOR public.dialog_stats_table;
