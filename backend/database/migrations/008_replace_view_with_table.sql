-- Радикальное решение: заменяем view на table + триггеры
-- Гарантированно избавляемся от SECURITY DEFINER

-- 1. Полностью удаляем view и все связанные объекты
DROP VIEW IF EXISTS public.dialog_stats CASCADE;
DROP FUNCTION IF EXISTS public.dialog_stats() CASCADE;
DROP MATERIALIZED VIEW IF EXISTS public.dialog_stats_mat CASCADE;

-- 2. Удаляем старую table если существует
DROP TABLE IF EXISTS public.dialog_stats_table CASCADE;

-- 3. Создаём обычную TABLE вместо VIEW (гарантированно без SECURITY DEFINER)
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

-- 4. Создаём индексы для производительности
CREATE INDEX IF NOT EXISTS idx_dialog_stats_table_user_id ON public.dialog_stats_table(user_id);
CREATE INDEX IF NOT EXISTS idx_dialog_stats_table_updated_at ON public.dialog_stats_table(updated_at);
CREATE INDEX IF NOT EXISTS idx_dialog_stats_table_message_count ON public.dialog_stats_table(message_count);

-- 5. Заполняем таблицу начальными данными
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

-- 6. Создаём триггерную функцию для обновления статистики
CREATE OR REPLACE FUNCTION public.update_dialog_stats_trigger()
RETURNS TRIGGER AS $$
BEGIN
    -- При вставке/обновлении диалога или сообщений
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        -- Обновляем или вставляем статистику для диалога
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
        WHERE d.id = COALESCE(NEW.id, NEW.dialog_id, NEW.id)
        GROUP BY d.id, d.user_id, d.title, d.created_at, d.updated_at
        ON CONFLICT (id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            title = EXCLUDED.title,
            updated_at = EXCLUDED.updated_at,
            message_count = EXCLUDED.message_count,
            last_message_at = EXCLUDED.last_message_at,
            duration_seconds = EXCLUDED.duration_seconds;
        
        RETURN COALESCE(NEW, OLD);
    END IF;
    
    IF TG_OP = 'DELETE' THEN
        -- Удаляем статистику при удалении диалога
        DELETE FROM public.dialog_stats_table WHERE id = OLD.id;
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 7. Создаём триггеры
DROP TRIGGER IF EXISTS trigger_dialogs_stats ON public.dialogs;
CREATE TRIGGER trigger_dialogs_stats
    AFTER INSERT OR UPDATE OR DELETE ON public.dialogs
    FOR EACH ROW EXECUTE FUNCTION public.update_dialog_stats_trigger();

DROP TRIGGER IF EXISTS trigger_messages_stats ON public.messages;
CREATE TRIGGER trigger_messages_stats
    AFTER INSERT OR UPDATE OR DELETE ON public.messages
    FOR EACH ROW EXECUTE FUNCTION public.update_dialog_stats_trigger();

-- 8. Включаем RLS для таблицы статистики
ALTER TABLE public.dialog_stats_table ENABLE ROW LEVEL SECURITY;

-- 9. Создаём RLS политики (пользователи видят только свою статистику)
CREATE POLICY "Users can view own dialog stats" ON public.dialog_stats_table
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- 10. Даём права
GRANT SELECT ON public.dialog_stats_table TO authenticated;
GRANT SELECT ON public.dialog_stats_table TO anon;
GRANT EXECUTE ON FUNCTION public.update_dialog_stats_trigger() TO authenticated;

-- 11. Создаём view для обратной совместимости (но без SECURITY DEFINER)
CREATE OR REPLACE VIEW public.dialog_stats AS
SELECT * FROM public.dialog_stats_table;

GRANT SELECT ON public.dialog_stats TO authenticated;
GRANT SELECT ON public.dialog_stats TO anon;
