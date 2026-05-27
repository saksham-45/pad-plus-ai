-- ============================================================================
-- FIX: RLS Политики для user_api_keys
-- ============================================================================
-- Запустить в Supabase SQL Editor
-- https://hgjbjccpeirwrabbcjhr.supabase.co/dashboard/project/hgjbjccpeirwrabbcjhr/sql/new
-- ============================================================================

-- 1. Отключаем RLS временно для очистки
ALTER TABLE public.user_api_keys DISABLE ROW LEVEL SECURITY;

-- 2. Удаляем старые политики если есть
DROP POLICY IF EXISTS "Users can view own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can insert own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can update own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can delete own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут просматривать свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут вставлять свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут обновлять свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут удалять свои ключи" ON public.user_api_keys;

-- 3. Включаем RLS обратно
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

-- 4. Создаем новые политики с WITH CHECK для UPDATE (важно!)
-- SELECT: Пользователи могут видеть только свои ключи
CREATE POLICY "Users can view own keys"
ON public.user_api_keys
FOR SELECT
USING (auth.uid() = user_id);

-- INSERT: Пользователи могут добавлять свои ключи
CREATE POLICY "Users can insert own keys"
ON public.user_api_keys
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- UPDATE: Пользователи могут обновлять свои ключи
-- WITH CHECK гарантирует, что обновленная строка остается в области видимости пользователя
CREATE POLICY "Users can update own keys"
ON public.user_api_keys
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- DELETE: Пользователи могут удалять свои ключи
CREATE POLICY "Users can delete own keys"
ON public.user_api_keys
FOR DELETE
USING (auth.uid() = user_id);

-- 5. Устанавливаем права доступа
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_api_keys TO authenticated;

-- 6. Проверка: показать текущее состояние RLS
SELECT 
    schemaname,
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables 
WHERE tablename = 'user_api_keys';

-- 7. Показать созданные политики
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies 
WHERE tablename = 'user_api_keys';

-- Готово! RLS политики исправлены.
-- Теперь можно обновлять API ключи через интерфейс.
