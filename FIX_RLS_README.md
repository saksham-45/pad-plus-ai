# 🔧 Быстрое исправление ошибок RLS и обновления ключей

## Ошибки в логах

```
ERROR - Failed to insert key: 'new row violates row-level security policy'
ERROR - Failed to insert key: 'HTTP/2 401 Unauthorized'
```

## Причина проблемы

1. **Политики RLS не применены** или применены без приведения типов
2. **Несоответствие типов:** auth.uid() возвращает UUID, user_id тоже UUID, но в некоторых версиях Supabase нужно явно привести оба к text

## Решение (2 шага)

### Шаг 1: Исправить RLS политики в Supabase

**ВАЖНО:** Используется приведение типов `(auth.uid())::text = (user_id)::text`

1. Откройте [Supabase Dashboard](https://supabase.com/dashboard)
2. Перейдите в **SQL Editor** → **New query**
3. **Очистите редактор полностью** (удалите всё, что было)
4. Скопируйте этот SQL (без маркдаун-блоков):

```sql
ALTER TABLE public.user_api_keys DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can insert own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can update own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can delete own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут просматривать свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут вставлять свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут обновлять свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут удалять свои ключи" ON public.user_api_keys;

ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own keys"
ON public.user_api_keys
FOR SELECT
USING ((auth.uid())::text = (user_id)::text);

CREATE POLICY "Users can insert own keys"
ON public.user_api_keys
FOR INSERT
WITH CHECK ((auth.uid())::text = (user_id)::text);

CREATE POLICY "Users can update own keys"
ON public.user_api_keys
FOR UPDATE
USING ((auth.uid())::text = (user_id)::text)
WITH CHECK ((auth.uid())::text = (user_id)::text);

CREATE POLICY "Users can delete own keys"
ON public.user_api_keys
FOR DELETE
USING ((auth.uid())::text = (user_id)::text);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_api_keys TO authenticated;
```

5. Нажмите **Run** (или Ctrl+Enter)
6. Ожидайте зелёную галку "Success" ✅

### Шаг 2: Перезапустить backend

```bash
python backend/main.py
```

## Проверка

1. Попробуйте добавить API ключ через интерфейс
2. Ошибка `401 Unauthorized` должна исчезнуть
3. Ошибка `new row violates row-level security policy` должна исчезнуть

## Что было исправлено в коде

### 1. Модель `APIKeyUpdate`

**Добавлено:** поле `api_key` для обновления самого ключа
```python
class APIKeyUpdate(BaseModel):
    api_key: Optional[str] = None  # ← Новое поле
    name: Optional[str] = None
    model_preference: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
```

### 2. Эндпоинт `PATCH /api/v1/keys/{key_id}`

**Улучшение:** теперь обрабатывает обновление ключа с шифрованием
```python
if data.api_key is not None:
    encrypted_key = encryptor.encrypt(data.api_key)
    update_data["api_key_encrypted"] = encrypted_key
```

### 3. RLS политики в Supabase

**Критическое исправление:** добавлено приведение типов `::text`

**Было (неработающее):**
```sql
USING (auth.uid() = user_id)
```

**Стало (рабочее):**
```sql
USING ((auth.uid())::text = (user_id)::text)
WITH CHECK ((auth.uid())::text = (user_id)::text)
```

Приведение типов гарантирует, что UUID из auth.uid() сравнивается с UUID из user_id корректно в Supabase.

## Автоматическое применение (PowerShell)

```powershell
cd scripts
.\fix_rls_policies.ps1
```

## Полная документация

Смотрите [APPLY_RLS_FIX.md](./APPLY_RLS_FIX.md) для пошагового применения.
Смотрите [RLS_FIX_GUIDE.md](./docs/RLS_FIX_GUIDE.md) для технических деталей.
