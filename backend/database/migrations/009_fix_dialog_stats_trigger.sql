-- Фикс триггера update_dialog_stats_trigger для dialogs + messages таблиц
-- Проблема: триггер на dialogs таблице обращается к NEW.dialog_id, которого нет
-- в таблице dialogs (там поле называется id).

-- Удаляем старые триггеры
DROP TRIGGER IF EXISTS trigger_dialogs_stats ON public.dialogs;
DROP TRIGGER IF EXISTS trigger_messages_stats ON public.messages;

-- Новая функция — безопасная для обоих таблиц
CREATE OR REPLACE FUNCTION public.update_dialog_stats_trigger()
RETURNS TRIGGER AS $$
DECLARE
    target_dialog_id UUID;
BEGIN
    -- Определяем dialog_id в зависимости от таблицы
    IF TG_TABLE_NAME = 'dialogs' THEN
        target_dialog_id := NEW.id;
    ELSIF TG_TABLE_NAME = 'messages' THEN
        target_dialog_id := NEW.dialog_id;
    ELSE
        RETURN NULL;
    END IF;

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
    WHERE d.id = target_dialog_id
    GROUP BY d.id, d.user_id, d.title, d.created_at, d.updated_at
    ON CONFLICT (id) DO UPDATE SET
        user_id = EXCLUDED.user_id,
        title = EXCLUDED.title,
        updated_at = EXCLUDED.updated_at,
        message_count = EXCLUDED.message_count,
        last_message_at = EXCLUDED.last_message_at,
        duration_seconds = EXCLUDED.duration_seconds;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Создаём триггеры заново
CREATE TRIGGER trigger_dialogs_stats
    AFTER INSERT OR UPDATE OR DELETE ON public.dialogs
    FOR EACH ROW EXECUTE FUNCTION public.update_dialog_stats_trigger();

CREATE TRIGGER trigger_messages_stats
    AFTER INSERT OR UPDATE OR DELETE ON public.messages
    FOR EACH ROW EXECUTE FUNCTION public.update_dialog_stats_trigger();
