# Исправление RLS Policy Violation для API Keys

## Проблема

При создании API ключа возникает ошибка:
```
ERROR - Failed to insert key: {'message': 'new row violates row-level security policy for table "user_api_keys"', 'code': '42501', 'hint': None, 'details': None}
```

Также может быть ошибка:
```
ERROR - Ошибка получения статистики RAG: No module named 'psycopg2'
```

## Причина

1. **RLS Policy Violation**: Политика безопасности Supabase блокирует вставку новых записей в таблицу `user_api_keys` из-за несоответствия типов при сравнении `auth.uid()` (uuid) и `user_id` (UUID).

2. **Отсутствует psycopg2**: Модуль `psycopg2` не установлен в окружении, что вызывает ошибки при попытке получить статистику RAG.

## Решение

### Шаг 1: Исправление RLS политик в Supabase

1. Откройте [Supabase Dashboard](https://supabase.com/dashboard)
2. Перейдите в **SQL Editor**
3. Выполните следующий SQL:

```sql
-- ============================================================================
-- Исправление RLS политик для user_api_keys
-- ============================================================================

-- Включаем RLS если отключен
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

-- Очищаем старые политики
DROP POLICY IF EXISTS "Users can insert own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can view own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can update own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can delete own keys" ON public.user_api_keys;

-- Создаем новые политики с явным приведением типов
CREATE POLICY "Users can insert own keys"
    ON public.user_api_keys FOR INSERT
    WITH CHECK ((auth.uid())::text = (user_id)::text);

CREATE POLICY "Users can view own keys"
    ON public.user_api_keys FOR SELECT
    USING ((auth.uid())::text = (user_id)::text);

CREATE POLICY "Users can update own keys"
    ON public.user_api_keys FOR UPDATE
    USING ((auth.uid())::text = (user_id)::text);

CREATE POLICY "Users can delete own keys"
    ON public.user_api_keys FOR DELETE
    USING ((auth.uid())::text = (user_id)::text);
```

4. Нажмите **Run** и убедитесь, что SQL выполнен без ошибок

### Альтернатива: Применение миграции через скрипт

Если у вас есть доступ к базе данных через `DATABASE_URL`, можно применить миграцию автоматически:

```bash
# Установите psycopg2-binary если еще не установлен
pip install psycopg2-binary

# Примените миграции
python scripts/apply_migrations.py
```

Миграция находится в `backend/database/migrations/007_fix_api_keys_rls.sql`

### Шаг 2: Установка psycopg2 (локальная разработка)

Для локальной разработки установите `psycopg2-binary`:

```bash
pip install psycopg2-binary
```

**Примечание**: В production (Render) `psycopg2-binary` уже указан в `requirements.txt` и будет установлен автоматически при деплое.

### Шаг 3: Перезапуск backend

После применения SQL миграции и установки psycopg2:

```bash
# Локально
python backend/main.py

# Или через Docker
docker-compose up -d
```

## Проверка

1. Откройте frontend и попробуйте добавить API ключ
2. Проверьте логи backend — ошибка `42501` больше не должна появляться
3. Проверьте статистику RAG — ошибка `No module named 'psycopg2'` должна исчезнуть

## Дополнительные проверки

### Проверка RLS политик

Выполните в Supabase SQL Editor:

```sql
-- Проверить все политики для user_api_keys
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
```

Ожидаемый результат: 4 политики (SELECT, INSERT, UPDATE, DELETE)

### Проверка типа колонки user_id

```sql
-- Проверить тип колонки user_id
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_name = 'user_api_keys' AND column_name = 'user_id';
```

Ожидаемый результат: `user_id` должен быть типа `uuid`

### Проверка подключения к базе

В логах backend должно быть:

```
✅ KeyEncryptor инициализирован
🔑 Creating key: provider=..., model=...
✅ Key saved successfully
```

Без ошибки `Failed to insert key`.

## Если проблема сохраняется

### Вариант 1: Временно отключить RLS (ТОЛЬКО для диагностики!)

```sql
-- ВНИМАНИЕ: Только для диагностики! Не оставляйте RLS отключенным!
ALTER TABLE public.user_api_keys DISABLE ROW LEVEL SECURITY;

-- Попробуйте добавить ключ
-- Если работает — проблема точно в политике

-- Включите RLS обратно
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;
```

### Вариант 2: Использовать service_role ключ

Убедитесь, что в `.env` или переменных окружения Render настроен `SUPABASE_SERVICE_KEY`:

```bash
SUPABASE_SERVICE_KEY=your_service_role_key_here
```

Этот ключ игнорирует RLS политики и используется только на backend.

### Вариант 3: Проверить auth.uid()

Убедитесь, что пользователь авторизован:

```sql
-- Выполните как authenticated пользователь
SELECT auth.uid();
```

Должен вернуть UUID пользователя, а не `NULL`.

## См. также

- [SECURITY_AUDIT_REPORT.md](./archive/SECURITY_AUDIT_REPORT.md) — Отчёт по безопасности (архив)
- [API.md](./API.md) — Документация API
- [QUICK_DEPLOY_GUIDE.md](./QUICK_DEPLOY_GUIDE.md) — Инструкция по деплою
