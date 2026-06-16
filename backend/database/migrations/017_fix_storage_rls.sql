-- ==========================================================
-- Fix Storage RLS policy для загрузки документов
-- Ошибка: new row violates row-level security policy
-- Supabase Storage bucket "documents" не имеет политики INSERT
--
-- ВАЖНО: Выполнять в Supabase Dashboard → SQL Editor!
--        Только там есть права владельца (owner) на storage.objects.
--        Не выполнять через анонимного пользователя или клиентский код.
-- ==========================================================

-- 1. Убедимся, что RLS включён (в Supabase уже включён по умолчанию)
--    ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY; — пропускаем,
--    т.к. требует прав владельца таблицы, а в Supabase RLS уже активен.

-- 2. Удаляем старые политики (если есть), чтобы не было конфликта
DROP POLICY IF EXISTS "Users can upload to their own folder" ON storage.objects;
DROP POLICY IF EXISTS "Users can read their own files" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete their own files" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can manage documents" ON storage.objects;
DROP POLICY IF EXISTS "Give users authenticated access to folder 1" ON storage.objects;
DROP POLICY IF EXISTS "Give users authenticated access to folder" ON storage.objects;

-- 3. Политика: пользователь загружает в свою папку (user_id/filename)
--    auth.uid() — из JWT-токена, проверяет, что путь начинается с ID пользователя
CREATE POLICY "Users can upload to their own folder"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'documents'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

-- 4. Политика: пользователь читает только свои файлы
CREATE POLICY "Users can read their own files"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'documents'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

-- 5. Политика: пользователь удаляет свои файлы
CREATE POLICY "Users can delete their own files"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'documents'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

-- ==========================================================
-- АЛЬТЕРНАТИВА (если политики по user_id не сработают):
-- Раскомментируйте блок ниже и закомментируйте блоки 3-5
-- ВНИМАНИЕ: Это разрешит ВСЕМ авторизованным пользователям
-- читать/писать/удалять любые файлы в bucket documents.
-- Подходит ТОЛЬКО для разработки.
-- ==========================================================
-- DROP POLICY IF EXISTS "Users can upload to their own folder" ON storage.objects;
-- DROP POLICY IF EXISTS "Users can read their own files" ON storage.objects;
-- DROP POLICY IF EXISTS "Users can delete their own files" ON storage.objects;
-- 
-- CREATE POLICY "Authenticated users can manage documents"
-- ON storage.objects FOR ALL
-- TO authenticated
-- USING (bucket_id = 'documents')
-- WITH CHECK (bucket_id = 'documents');