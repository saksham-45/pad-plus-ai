-- Включаем RLS для таблиц пользователей
-- Запустить в Supabase SQL Editor

-- 1. Включаем RLS для user_api_keys
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

-- 2. Создаем политику для SELECT (просмотр только своих ключей)
CREATE POLICY "Пользователи могут просматривать собственные ключи"
ON public.user_api_keys
FOR SELECT
USING (auth.uid()::text = user_id);

-- 3. Создаем политику для INSERT (вставка только своих ключей)
CREATE POLICY "Пользователи могут вставлять собственные ключи"
ON public.user_api_keys
FOR INSERT
WITH CHECK (auth.uid()::text = user_id);

-- 4. Создаем политику для UPDATE (обновление только своих ключей)
CREATE POLICY "Пользователи могут обновлять собственные ключи"
ON public.user_api_keys
FOR UPDATE
USING (auth.uid()::text = user_id)
WITH CHECK (auth.uid()::text = user_id);

-- 5. Создаем политику для DELETE (удаление только своих ключей)
CREATE POLICY "Пользователи могут удалять собственные ключи"
ON public.user_api_keys
FOR DELETE
USING (auth.uid()::text = user_id);

-- 6. Проверяем что RLS включен
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE tablename = 'user_api_keys';
