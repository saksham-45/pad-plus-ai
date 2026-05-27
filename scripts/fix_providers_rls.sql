-- ============================================================================
-- FIX: RLS Политики для user_api_keys
-- ============================================================================
-- Запустить в Supabase SQL Editor
-- ВАЖНО: Используется приведение типов (::text) для совместимости UUID
-- ============================================================================

-- 1. Отключаем RLS временно для очистки
ALTER TABLE public.user_api_keys DISABLE ROW LEVEL SECURITY;

-- 2. Удаляем ВСЕ старые политики
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

-- 4. Создаем новые политики С ПРИВЕДЕНИЕМ ТИПОВ (::text)
-- Это критически важно! auth.uid() и user_id должны быть одного типа

-- SELECT: Пользователи могут видеть только свои ключи
CREATE POLICY "Users can view own keys"
ON public.user_api_keys
FOR SELECT
USING ((auth.uid())::text = (user_id)::text);

-- INSERT: Пользователи могут добавлять свои ключи
CREATE POLICY "Users can insert own keys"
ON public.user_api_keys
FOR INSERT
WITH CHECK ((auth.uid())::text = (user_id)::text);

-- UPDATE: Пользователи могут обновлять свои ключи
-- WITH CHECK гарантирует, что обновленная строка остается в области видимости пользователя
CREATE POLICY "Users can update own keys"
ON public.user_api_keys
FOR UPDATE
USING ((auth.uid())::text = (user_id)::text)
WITH CHECK ((auth.uid())::text = (user_id)::text);

-- DELETE: Пользователи могут удалять свои ключи
CREATE POLICY "Users can delete own keys"
ON public.user_api_keys
FOR DELETE
USING ((auth.uid())::text = (user_id)::text);

-- 5. Устанавливаем права доступа для authenticated пользователей
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_api_keys TO authenticated;

-- 6. Проверка: показать текущее состояние RLS
SELECT 
    schemaname,
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables 
WHERE tablename = 'user_api_keys';

-- 7. Показать созданные политики (проверьте, что их 4)
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
WHERE tablename = 'user_api_keys'
ORDER BY policyname;

-- Готово! RLS политики исправлены с приведением типов.
-- Теперь можно добавлять и обновлять API ключи через интерфейс.
