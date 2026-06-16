# 🔒 RLS Политики PAD+ AI

**Версия:** 1.0  
**Дата:** Декабрь 2024  
**Статус:** ✅ Актуально

---

## Обзор

**RLS (Row Level Security)** — механизм безопасности PostgreSQL/Supabase, ограничивающий доступ к данным на уровне строк.

В PAD+ AI RLS гарантирует, что каждый пользователь видит **только свои данные**:
- API ключи
- Диалоги
- Сообщения
- X-Ray трейсы
- Эпизоды
- Документы

---

## Критические миграции

### ✅ Рабочие миграции (применять)

| № | Файл | Описание | Таблицы |
|---|------|----------|---------|
| 001 | `001_initial_schema.sql` | Начальная схема | Все основные таблицы |
| 009 | `009_fix_user_api_keys_rls.sql` | **РАБОЧАЯ** RLS для API ключей | `user_api_keys` |
| 015 | `015_xray_traces.sql` | X-Ray трейсы | `xray_traces` |
| 016 | `016_enable_rls_memory_tables.sql` | RLS для memory-таблиц | `episodes`, `episode_relations`, `semantic_knowledge`, `procedure_applications` |
| 017 | `017_fix_storage_rls.sql` | RLS для Storage (документы) | `storage.objects` (bucket: documents) |

---

## Детали миграций

### 009 — user_api_keys (КРИТИЧНО)

**Проблема:** RLS блокировал вставку/обновление API ключей.

**Решение:** 4 политики с приведением типов `::text`:

```sql
-- SELECT: просмотр своих ключей
CREATE POLICY "Users can view own keys"
    ON user_api_keys FOR SELECT
    USING (auth.uid()::text = user_id::text);

-- INSERT: вставка своих ключей
CREATE POLICY "Users can insert own keys"
    ON user_api_keys FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);

-- UPDATE: обновление своих ключей
CREATE POLICY "Users can update own keys"
    ON user_api_keys FOR UPDATE
    USING (auth.uid()::text = user_id::text);

-- DELETE: удаление своих ключей
CREATE POLICY "Users can delete own keys"
    ON user_api_keys FOR DELETE
    USING (auth.uid()::text = user_id::text);
```

**Важно:** Приведение `::text` критично! Без него сравнение `uuid = uuid` не работает корректно.

---

### 015 — xray_traces

**Таблица:** `xray_traces`

**Политики:**
```sql
-- Пользователи видят свои трейсы
CREATE POLICY "Пользователи видят свои трейсы"
    ON xray_traces FOR SELECT
    USING (user_id = auth.uid());

-- Сервис может вставлять трейсы
CREATE POLICY "Сервис может вставлять трейсы"
    ON xray_traces FOR INSERT
    WITH CHECK (true);
```

**Авто-очистка:** Трейсы старше 90 дней удаляются функцией `cleanup_old_xray_traces()`.

---

### 016 — Memory Tables

**Таблицы:**
- `episodes` — эпизоды
- `episode_relations` — связи эпизодов
- `semantic_knowledge` — семантические знания
- `procedure_applications` — применения процедур

**Политики:**
| Таблица | SELECT | INSERT | UPDATE |
|---------|--------|--------|--------|
| `episodes` | user_id = auth.uid() | true | true |
| `episode_relations` | EXISTS (episodes.user_id) | true | — |
| `semantic_knowledge` | true (общая база) | true | true |
| `procedure_applications` | true (общая база) | true | — |

---

### 017 — Storage (документы)

**Bucket:** `documents`

**Политики:**
```sql
-- Загрузка в свою папку (user_id/filename)
CREATE POLICY "Users can upload to their own folder"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

-- Чтение своих файлов
CREATE POLICY "Users can read their own files"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

-- Удаление своих файлов
CREATE POLICY "Users can delete their own files"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );
```

**Важно:** Выполнять **только в Supabase Dashboard → SQL Editor** (требуются права владельца).

---

## ❌ Удалённые дубликаты

Следующие файлы **удалены** как конфликтующие дубликаты:

### 007_* (7 файлов)
- `007_fix_api_keys_rls.sql`
- `007_fix_real_rls.sql`
- `007_fix_rls_final.sql`
- `007_fix_rls_policies.sql`
- `007_fix_rls_policies_correct.sql`
- `007_fix_rls_policies_final.sql`
- `007_fix_rls_policies_fixed.sql`

### 008_* (6 файлов)
- `008_fix_dialog_stats_security.sql`
- `008_fix_dialog_stats_security_simple.sql`
- `008_force_remove_security_definer.sql`
- `008_remove_security_definer.sql`
- `008_remove_view_completely.sql`
- `008_replace_view_with_table.sql`

### 009_* (2 файла)
- `009_disable_rls_user_api_keys.sql` ❌ **ОПАСНО** (отключает RLS)
- `009_fix_dialog_stats_trigger.sql`

### 010_* (2 файла)
- `010_enable_rls_final.sql`
- `010_enable_rls_final_fixed.sql`

### 011_* — 014_* (4 файла)
- `011_disable_rls_temp.sql` ❌ **ОПАСНО**
- `012_fix_rls_policies.sql`
- `013_disable_rls_completely.sql` ❌ **ОПАСНО**
- `014_fix_rls_immediate.sql`

### RLS_*.sql (3 файла)
- `RLS_FIX_FINAL.sql`
- `RLS_FIX_SQL_ONLY.sql`
- `RLS_FORCE_DELETE.sql`

**Причина удаления:**
- Дублирование функционала
- Конфликтующие определения политик
- Миграции с отключением RLS (безопасность!)
- Неприменяемые миграции

---

## ⚠️ Устаревшие миграции (сохранены для истории)

Эти файлы **сохранены**, но не применяются:

| Файл | Причина устаревания |
|------|---------------------|
| `002_rls_policies.sql` | Политики без `::text` приведения (не работают) |
| `003_fix_rls_policies.sql` | Устаревшие политики для `users` |
| `004_user_settings_and_dialogs.sql` | Устаревшая схема |
| `005_documents_and_collections.sql` | Заменено на `017_fix_storage_rls.sql` |
| `006_fix_rls_and_auth.sql` | Устаревшие политики для `users` |

**Используйте только:** 001, 009, 015, 016, 017

---

## Проверка состояния

### 1. Проверить RLS политики для user_api_keys

```sql
SELECT policyname, cmd, qual, with_check
FROM pg_policies
WHERE tablename = 'user_api_keys'
ORDER BY policyname;
```

**Ожидаемый результат:** 4 политики (SELECT, INSERT, UPDATE, DELETE)

---

### 2. Проверить включение RLS

```sql
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE tablename IN ('user_api_keys', 'xray_traces', 'episodes', 'semantic_knowledge');
```

**Ожидаемый результат:** `rowsecurity = true` для всех таблиц

---

### 3. Проверить Storage политики

```sql
-- Выполнить в Supabase Dashboard (требуются права владельца)
SELECT policyname, cmd
FROM pg_policies
WHERE tablename = 'objects'
  AND schemaname = 'storage';
```

**Ожидаемый результат:** 3 политики (INSERT, SELECT, DELETE)

---

## Применение миграций

### Через Supabase Dashboard (рекомендуется)

1. Откройте [Supabase Dashboard](https://supabase.com/dashboard)
2. Выберите проект
3. **SQL Editor** → **New query**
4. Скопируйте содержимое файла миграции
5. Нажмите **Run**

### Через скрипт

```bash
cd scripts
python apply_migrations.py
```

---

## Безопасность

### ⚠️ НИКОГДА не применяйте

- Миграции с `DISABLE ROW LEVEL SECURITY`
- Миграции с `_disable_rls_` в названии
- Миграции из архива `docs/archive/legacy/`

### ✅ Всегда применяйте

- Только файлы из `backend/database/migrations/` с номерами 001, 009, 015, 016, 017
- Миграции в порядке возрастания номеров

---

## Troubleshooting

### Ошибка: `42501 permission denied for table`

**Причина:** RLS политика блокирует доступ.

**Решение:**
1. Проверьте, что пользователь аутентифицирован
2. Проверьте, что `user_id` совпадает с `auth.uid()`
3. Примените миграцию `009_fix_user_api_keys_rls.sql`

---

### Ошибка: `new row violates row-level security policy`

**Причина:** Новая запись не проходит проверку RLS.

**Решение:**
1. Проверьте, что `user_id` установлен в `auth.uid()`
2. Убедитесь, что используется приведение `::text`
3. Проверьте политику через `SELECT * FROM pg_policies`

---

### Ошибка: `policy "..." already exists`

**Причина:** Политика уже создана.

**Решение:**
```sql
-- Удалить существующую политику
DROP POLICY IF EXISTS "policy_name" ON table_name;

-- Создать заново
CREATE POLICY "policy_name" ON table_name ...;
```

---

## Ссылки

- [Supabase RLS Documentation](https://supabase.com/docs/guides/auth/row-level-security)
- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — общая архитектура
- [docs/DEPLOYMENT.md](DEPLOYMENT.md) — развёртывание

---

## История изменений

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | Декабрь 2024 | Первая версия документа |
