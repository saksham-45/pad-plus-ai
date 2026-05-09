-- Включаем RLS для всех таблиц пользователей
-- Запустить в Supabase SQL Editor

-- 1. user_api_keys
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

-- 2. dialogs
ALTER TABLE public.dialogs ENABLE ROW LEVEL SECURITY;

-- 3. messages
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- 4. users (если есть)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Политики для user_api_keys
DROP POLICY IF EXISTS "Пользователи могут просматривать собственные ключи" ON public.user_api_keys;
CREATE POLICY "Пользователи могут просматривать собственные ключи"
ON public.user_api_keys FOR SELECT
USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Пользователи могут вставлять собственные ключи" ON public.user_api_keys;
CREATE POLICY "Пользователи могут вставлять собственные ключи"
ON public.user_api_keys FOR INSERT
WITH CHECK (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Пользователи могут обновлять собственные ключи" ON public.user_api_keys;
CREATE POLICY "Пользователи могут обновлять собственные ключи"
ON public.user_api_keys FOR UPDATE
USING (auth.uid()::text = user_id)
WITH CHECK (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Пользователи могут удалять собственные ключи" ON public.user_api_keys;
CREATE POLICY "Пользователи могут удалять собственные ключи"
ON public.user_api_keys FOR DELETE
USING (auth.uid()::text = user_id);

-- Политики для dialogs
DROP POLICY IF EXISTS "Пользователи могут просматривать собственные диалоги" ON public.dialogs;
CREATE POLICY "Пользователи могут просматривать собственные диалоги"
ON public.dialogs FOR SELECT
USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Пользователи могут создавать собственные диалоги" ON public.dialogs;
CREATE POLICY "Пользователи могут создавать собственные диалоги"
ON public.dialogs FOR INSERT
WITH CHECK (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Пользователи могут обновлять собственные диалоги" ON public.dialogs;
CREATE POLICY "Пользователи могут обновлять собственные диалоги"
ON public.dialogs FOR UPDATE
USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Пользователи могут удалять собственные диалоги" ON public.dialogs;
CREATE POLICY "Пользователи могут удалять собственные диалоги"
ON public.dialogs FOR DELETE
USING (auth.uid()::text = user_id);

-- Политики для messages
DROP POLICY IF EXISTS "Пользователи могут просматривать собственные сообщения" ON public.messages;
CREATE POLICY "Пользователи могут просматривать собственные сообщения"
ON public.messages FOR SELECT
USING (EXISTS (
    SELECT 1 FROM public.dialogs 
    WHERE dialogs.id = messages.dialog_id 
    AND dialogs.user_id = auth.uid()
));

DROP POLICY IF EXISTS "Пользователи могут вставлять собственные сообщения" ON public.messages;
CREATE POLICY "Пользователи могут вставлять собственные сообщения"
ON public.messages FOR INSERT
WITH CHECK (EXISTS (
    SELECT 1 FROM public.dialogs 
    WHERE dialogs.id = messages.dialog_id 
    AND dialogs.user_id = auth.uid()
));

-- Проверка
SELECT 
    schemaname,
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables 
WHERE tablename IN ('user_api_keys', 'dialogs', 'messages', 'users')
ORDER BY tablename;
