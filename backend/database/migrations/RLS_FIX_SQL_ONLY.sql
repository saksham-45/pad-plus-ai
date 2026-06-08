-- ИСПРАВЛЕННЫЙ SQL ДЛЯ RLS - БЕЗ КИРИЛЛИЦЫ
-- Скопируйте и выполните этот код в Supabase SQL Editor

-- 1. Включаем RLS для таблицы user_api_keys
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

-- 2. Удаляем старые политики если они есть с кириллицей
DROP POLICY IF EXISTS "Пользователи могут просматривать свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут вставлять свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут обновлять свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут удалять свои ключи" ON public.user_api_keys;

-- 3. Создаем политики с английскими названиями
CREATE POLICY "Users can view own keys" ON public.user_api_keys
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own keys" ON public.user_api_keys
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own keys" ON public.user_api_keys
    FOR UPDATE USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can delete own keys" ON public.user_api_keys
    FOR DELETE USING (auth.uid()::text = user_id::text);

-- 4. Устанавливаем права доступа
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_api_keys TO authenticated;
GRANT SELECT ON public.user_api_keys TO anon;

-- 5. Проверка результатов
SELECT 'RLS Status:' as info;
SELECT 
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables 
WHERE tablename = 'user_api_keys';

SELECT count(*) as policy_count 
FROM pg_policies 
WHERE tablename = 'user_api_keys';

SELECT 'Policies created successfully!' as result;
