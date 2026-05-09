-- ПРИНУДИТЕЛЬНОЕ УДАЛЕНИЕ ВСЕХ ПОЛИТИК И СОЗДАНИЕ НОВЫХ
-- Этот SQL удалит ВСЕ политики для user_api_keys и создаст новые

-- 1. Полностью удаляем ВСЕ политики для таблицы user_api_keys
DROP POLICY IF EXISTS "Пользователи могут просматривать свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут вставлять свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут обновлять свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут удалять свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can view own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can insert own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can update own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can delete own keys" ON public.user_api_keys;

-- 2. Отключаем и снова включаем RLS для очистки
ALTER TABLE public.user_api_keys DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

-- 3. Создаем новые политики с английскими названиями
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
SELECT '=== RLS FIX RESULTS ===' as info;
SELECT 
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables 
WHERE tablename = 'user_api_keys';

SELECT 
    policyname,
    cmd,
    permissive
FROM pg_policies 
WHERE tablename = 'user_api_keys';

SELECT 'Total policies created:' as result;
SELECT count(*) as total_policies 
FROM pg_policies 
WHERE tablename = 'user_api_keys';

SELECT 'SUCCESS: RLS policies fixed!' as status;
