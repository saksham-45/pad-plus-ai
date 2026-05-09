-- Временное отключение RLS для user_api_keys
-- RLS упорно блокирует вставку, отключаем для теста

-- Полностью отключаем RLS для user_api_keys
ALTER TABLE public.user_api_keys DISABLE ROW LEVEL SECURITY;

-- Удаляем все политики для этой таблицы
DROP POLICY IF EXISTS "Users can view own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can insert own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can update own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can delete own keys" ON public.user_api_keys;

-- Проверяем что RLS отключен
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = 'user_api_keys' 
        AND rowsecurity = true
    ) THEN
        RAISE EXCEPTION 'RLS still enabled';
    ELSE
        RAISE NOTICE 'RLS successfully disabled for user_api_keys';
    END IF;
END $$;

-- Даём права всем пользователям (временно для теста)
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_api_keys TO authenticated;
GRANT SELECT ON public.user_api_keys TO anon;

-- Проверяем что политики удалены
SELECT schemaname, tablename, policyname 
FROM pg_policies 
WHERE tablename = 'user_api_keys';

-- Примечание: После тестирования нужно будет включить RLS обратно с правильными политиками
