-- ============================================================================
-- ИСПРАВЛЕНИЕ RLS ПОЛИТИК ДЛЯ РЕГИСТРАЦИИ
-- Полная очистка и создание новых политик
-- ============================================================================
-- Выполнить в Supabase SQL Editor
-- ============================================================================

-- 1. Проверяем что RLS включен
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- 2. ПОЛНОЕ УДАЛЕНИЕ ВСЕХ СУЩЕСТВУЮЩИХ ПОЛИТИК
-- Удаляем ВСЕ возможные варианты названий
DROP POLICY IF EXISTS "Users can view own data" ON users;
DROP POLICY IF EXISTS "Users can update own data" ON users;
DROP POLICY IF EXISTS "Users can insert own data" ON users;
DROP POLICY IF EXISTS "Enable insert for authenticated users only" ON users;
DROP POLICY IF EXISTS "Enable users to view their own data only" ON users;
DROP POLICY IF EXISTS "Enable users to update their own data only" ON users;
DROP POLICY IF EXISTS "Authenticated users can view any profile" ON users;
DROP POLICY IF EXISTS "Service role can do anything" ON users;
DROP POLICY IF EXISTS "users_view_own" ON users;
DROP POLICY IF EXISTS "users_update_own" ON users;
DROP POLICY IF EXISTS "users_insert_own" ON users;
DROP POLICY IF EXISTS "users_view_all_authenticated" ON users;
DROP POLICY IF EXISTS "users_service_all" ON users;

-- Также удаляем политики на других языках (если есть)
DROP POLICY IF EXISTS "Аутентифицированные пользователи могут просматривать любой профиль" ON users;
DROP POLICY IF EXISTS "Пользователи могут просматривать свои данные" ON users;
DROP POLICY IF EXISTS "Пользователи могут обновлять свои данные" ON users;
DROP POLICY IF EXISTS "Пользователи могут вставлять свои данные" ON users;

-- 3. Создаём НОВЫЕ правильные политики

-- ПОЛИТИКА 1: Любой аутентифицированный пользователь может читать СВОИ данные
CREATE POLICY "users_view_own"
    ON users FOR SELECT
    USING (auth.uid() = id);

-- ПОЛИТИКА 2: Любой аутентифицированный пользователь может обновлять СВОИ данные
CREATE POLICY "users_update_own"
    ON users FOR UPDATE
    USING (auth.uid() = id);

-- ПОЛИТИКА 3: ЛЮБОЙ аутентифицированный пользователь может создавать СВОЙ профиль
-- Это ключевая политика для регистрации!
CREATE POLICY "users_insert_own"
    ON users FOR INSERT
    WITH CHECK (auth.uid() = id);

-- ПОЛИТИКА 4: Разрешаем всем аутентифицированным пользователям читать профили
-- (нужно для работы системы)
CREATE POLICY "users_view_all_authenticated"
    ON users FOR SELECT
    TO authenticated
    USING (true);

-- ПОЛИТИКА 5: Разрешаем сервисному ключу делать всё (для бэкенда)
-- Это нужно если бэкенд использует service_role key
CREATE POLICY "users_service_all"
    ON users FOR ALL
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- ПРОВЕРКА
-- ============================================================================

-- Показываем все политики для таблицы users
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
WHERE tablename = 'users'
ORDER BY policyname;

-- ============================================================================
-- ГОТОВО!
-- ============================================================================
