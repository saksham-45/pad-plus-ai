-- ============================================================================
-- PAD+ AI v4.0 — Исправление RLS для user_api_keys
-- ============================================================================
-- Исправляет проблему: "new row violates row-level security policy"
-- Причина: UPDATE политика требует WITH CHECK для проверки новых значений
-- Решение: добавить WITH CHECK условие для UPDATE политики
-- ============================================================================

-- Включаем RLS если отключен
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

-- Очищаем старые политики
DROP POLICY IF EXISTS "Users can insert own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can view own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can update own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can delete own keys" ON public.user_api_keys;

-- Создаем новые политики с WITH CHECK для UPDATE
-- Это гарантирует, что обновленная строка соответствует условиям доступа
CREATE POLICY "Users can insert own keys"
    ON public.user_api_keys FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own keys"
    ON public.user_api_keys FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own keys"
    ON public.user_api_keys FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own keys"
    ON public.user_api_keys FOR DELETE
    USING (auth.uid() = user_id);

-- Убеждаемся, что authenticated пользователи имеют нужные права
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_api_keys TO authenticated;

-- Примечание:
-- auth.uid() возвращает UUID текущего аутентифицированного пользователя
-- USING - проверяется доступность строк для операции
-- WITH CHECK - проверяется, что результат операции соответствует условиям RLS
