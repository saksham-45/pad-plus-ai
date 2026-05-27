-- ============================================================================
-- PAD+ AI v4.0 — Исправление RLS для user_api_keys
-- ============================================================================
-- Исправляет проблему: "new row violates row-level security policy"
-- Причина: несоответствие типов auth.uid() и user_id при сравнении
-- Решение: явное приведение типов в обеих сторонах сравнения (::text)
-- ============================================================================

-- Включаем RLS если отключен
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

-- Очищаем старые политики
DROP POLICY IF EXISTS "Users can insert own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can view own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can update own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can delete own keys" ON public.user_api_keys;

-- Создаем новые политики с явным приведением типов UUID -> text
-- Это гарантирует корректное сравнение в Supabase
CREATE POLICY "Users can insert own keys"
    ON public.user_api_keys FOR INSERT
    WITH CHECK ((auth.uid())::text = (user_id)::text);

CREATE POLICY "Users can view own keys"
    ON public.user_api_keys FOR SELECT
    USING ((auth.uid())::text = (user_id)::text);

CREATE POLICY "Users can update own keys"
    ON public.user_api_keys FOR UPDATE
    USING ((auth.uid())::text = (user_id)::text)
    WITH CHECK ((auth.uid())::text = (user_id)::text);

CREATE POLICY "Users can delete own keys"
    ON public.user_api_keys FOR DELETE
    USING ((auth.uid())::text = (user_id)::text);

-- Убедимся, что authenticated пользователи имеют все нужные права
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_api_keys TO authenticated;

-- Примечание:
-- auth.uid() возвращает UUID из auth.users таблицы Supabase
-- user_id в user_api_keys имеет тип UUID
-- Приведение к text (::text) необходимо для корректной работы сравнения в Supabase
-- USING - проверяется доступность строк для операции
-- WITH CHECK - проверяется, что результат операции соответствует условиям RLS
