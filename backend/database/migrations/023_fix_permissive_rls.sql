-- ============================================================================
-- PAD+ AI — Security fix #7: remove permissive RLS policies (cross-user exposure)
-- ============================================================================
-- Run in the Supabase SQL Editor (or via scripts/apply_migrations.py).
--
-- Several earlier migrations enabled RLS but paired it with catch-all policies
-- (`USING (true)` with no `TO` clause, or `FOR SELECT TO anon USING (true)`).
-- Because RLS policies are OR-combined, those catch-alls override the correctly
-- scoped `auth.uid()` policies sitting next to them and expose every user's row
-- to any client holding the public anon key (and, for `users`, to writes too).
--
-- This migration drops the permissive policies and, where a table is read
-- directly through PostgREST, replaces them with owner-scoped policies.
--
-- Note: the `service_role` key BYPASSES RLS in Supabase, and the backend also
-- connects via DATABASE_URL as the table owner — so removing these public/anon
-- policies does NOT affect backend access. It only closes the anon/authenticated
-- REST surface.
--
-- Idempotent: safe to run more than once.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- users — remove full public read/write and "any authenticated reads all"
-- ----------------------------------------------------------------------------
-- `users_service_all` = FOR ALL USING(true) WITH CHECK(true) with no TO clause
--   -> role `public` (incl. anon): anyone could SELECT/INSERT/UPDATE/DELETE any row.
-- `users_view_all_authenticated` = FOR SELECT TO authenticated USING(true)
--   -> any logged-in user could read every user's profile.
DROP POLICY IF EXISTS "users_service_all" ON users;
DROP POLICY IF EXISTS "users_view_all_authenticated" ON users;

-- Keep backend access explicit and least-privilege (service_role only).
-- (service_role already bypasses RLS; this policy documents intent.)
DROP POLICY IF EXISTS "users_service_role" ON users;
CREATE POLICY "users_service_role"
    ON users FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- The owner-scoped self policies from 003/006
-- (users_view_own / users_update_own / users_insert_own / *_fixed) remain in
-- place, so a user can still read and update their own row.

-- ----------------------------------------------------------------------------
-- user_personas — per-user table; remove anonymous read of every persona
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Anon read user_personas" ON user_personas;

DROP POLICY IF EXISTS "Users read own persona" ON user_personas;
CREATE POLICY "Users read own persona"
    ON user_personas FOR SELECT
    TO authenticated
    USING (user_id = auth.uid()::text);

-- ----------------------------------------------------------------------------
-- episodes — remove anon read-all AND world-writable insert/update
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Anon read episodes" ON episodes;
DROP POLICY IF EXISTS "Сервис может вставлять эпизоды" ON episodes;   -- FOR INSERT WITH CHECK (true)
DROP POLICY IF EXISTS "Сервис может обновлять эпизоды" ON episodes;   -- FOR UPDATE USING (true)

DROP POLICY IF EXISTS "Users insert own episodes" ON episodes;
CREATE POLICY "Users insert own episodes"
    ON episodes FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid()::text);

DROP POLICY IF EXISTS "Users update own episodes" ON episodes;
CREATE POLICY "Users update own episodes"
    ON episodes FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid()::text);

-- The owner-scoped SELECT ("Пользователи видят свои эпизоды") and the
-- "Service role full access episodes" policy remain.

-- ----------------------------------------------------------------------------
-- episode_relations — remove anon read-all and world-writable insert
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Anon read episode_relations" ON episode_relations;
DROP POLICY IF EXISTS "Сервис может вставлять связи эпизодов" ON episode_relations;  -- FOR INSERT WITH CHECK (true)
-- Scoped SELECT ("Пользователи видят связи своих эпизодов") and the
-- "Service role full access episode_relations" policy remain.

-- ----------------------------------------------------------------------------
-- experiences — remove anonymous read of all interaction records
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Anon read experiences" ON experiences;
-- "Service role full access experiences" remains; the backend reads these
-- through service_role / DATABASE_URL, not through the anon REST surface.

-- ============================================================================
-- Verification (optional): list surviving policies for the affected tables.
-- Expect only owner-scoped (auth.uid()) and service_role policies below.
-- ============================================================================
-- SELECT tablename, policyname, roles, cmd, qual, with_check
-- FROM pg_policies
-- WHERE tablename IN ('users','user_personas','episodes','episode_relations','experiences')
-- ORDER BY tablename, policyname;
