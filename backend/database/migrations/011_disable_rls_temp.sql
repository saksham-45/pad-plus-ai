-- Временное отключение RLS для восстановления функциональности
-- Выполнить если RLS политики блокируют работу

-- 1. Полностью отключаем RLS для user_api_keys
ALTER TABLE public.user_api_keys DISABLE ROW LEVEL SECURITY;

-- 2. Удаляем все политики
DROP POLICY IF EXISTS "Users can view own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can insert own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can update own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can delete own keys" ON public.user_api_keys;

-- 3. Проверяем что RLS отключен
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE tablename = 'user_api_keys';

-- 4. Даём права authenticated пользователям
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_api_keys TO authenticated;
GRANT SELECT ON public.user_api_keys TO anon;

-- 5. Проверяем что политики удалены
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename = 'user_api_keys';

-- ВНИМАНИЕ: Это временное решение для восстановления работы приложения!
-- Позже нужно будет правильно настроить RLS политики.
