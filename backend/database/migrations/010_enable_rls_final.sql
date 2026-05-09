-- Финальное включение RLS политик с исправлениями
-- Включаем обратно RLS для user_api_keys с правильными политиками

-- 1. Включаем RLS для user_api_keys
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

-- 2. Удаляем старые политики если есть
DROP POLICY IF EXISTS "Users can view own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can insert own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can update own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can delete own keys" ON public.user_api_keys;

-- 3. Создаем новые RLS политики с правильным сравнением UUID
CREATE POLICY "Users can view own keys" ON public.user_api_keys
    FOR SELECT USING (auth.uid() = user_id::uuid);

CREATE POLICY "Users can insert own keys" ON public.user_api_keys
    FOR INSERT WITH CHECK (auth.uid() = user_id::uuid);

CREATE POLICY "Users can update own keys" ON public.user_api_keys
    FOR UPDATE USING (auth.uid() = user_id::uuid);

CREATE POLICY "Users can delete own keys" ON public.user_api_keys
    FOR DELETE USING (auth.uid() = user_id::uuid);

-- 4. Проверяем что политики созданы
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename = 'user_api_keys';

-- 5. Проверяем что RLS включен
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE tablename = 'user_api_keys';

-- 6. Даём права
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_api_keys TO authenticated;
GRANT SELECT ON public.user_api_keys TO anon;

-- 7. Тестовая проверка
DO $$
BEGIN
    RAISE NOTICE 'RLS policies enabled for user_api_keys';
    RAISE NOTICE 'Total policies: %', (
        SELECT COUNT(*) FROM pg_policies WHERE tablename = 'user_api_keys'
    );
END $$;
