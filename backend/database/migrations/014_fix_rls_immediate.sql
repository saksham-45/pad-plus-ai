-- СРОЧНОЕ ИСПРАВЛЕНИЕ RLS - ВЫПОЛНИТЬ НЕМЕДЛЕННО В SUPABASE
-- Проблема: RLS политики существуют но RLS отключен для таблицы

-- 1. Включаем RLS для таблицы user_api_keys
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

-- 2. Проверяем статус RLS
SELECT 
    schemaname, 
    tablename, 
    rowsecurity,
    hasrowsecurity,
    hasrowsecurity
FROM pg_tables 
WHERE tablename = 'user_api_keys';

-- 3. Проверяем существующие политики
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies 
WHERE tablename = 'user_api_keys';

-- 4. Если политики отсутствуют, создаем их
CREATE POLICY IF NOT EXISTS "Users can view own keys" ON public.user_api_keys
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY IF NOT EXISTS "Users can insert own keys" ON public.user_api_keys
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY IF NOT EXISTS "Users can update own keys" ON public.user_api_keys
    FOR UPDATE USING (auth.uid()::text = user_id::text);

CREATE POLICY IF NOT EXISTS "Users can delete own keys" ON public.user_api_keys
    FOR DELETE USING (auth.uid()::text = user_id::text);

-- 5. Убеждаемся что права установлены правильно
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_api_keys TO authenticated;
GRANT SELECT ON public.user_api_keys TO anon;

-- 6. Финальная проверка
SELECT 'RLS Status:' as info;
SELECT 
    tablename,
    rowsecurity as rls_enabled,
    'Policies:' as policy_info
FROM pg_tables 
WHERE tablename = 'user_api_keys';

SELECT count(*) as policy_count 
FROM pg_policies 
WHERE tablename = 'user_api_keys';
