# 🔧 Быстрое исправление ошибок RLS и обновления ключей

## Ошибки в логах

```
ERROR - Failed to update key: 'new row violates row-level security policy'
ERROR - Failed to insert key: 'new row violates row-level security policy'
```

## Причина проблемы

Политика UPDATE для таблицы `user_api_keys` **не имела WITH CHECK условия**, что привело к ошибкам при обновлении ключей.

## Решение (2 шага)

### Шаг 1: Исправить RLS политики в Supabase

1. Откройте [Supabase Dashboard](https://supabase.com/dashboard)
2. Перейдите в **SQL Editor**
3. Скопируйте и выполните этот SQL (или используйте автоматический скрипт):

```sql
-- Исправление RLS политик для user_api_keys
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can insert own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can view own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can update own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can delete own keys" ON public.user_api_keys;

-- SELECT: Пользователи могут видеть только свои ключи
CREATE POLICY "Users can view own keys"
ON public.user_api_keys
FOR SELECT
USING (auth.uid() = user_id);

-- INSERT: Пользователи могут добавлять свои ключи
CREATE POLICY "Users can insert own keys"
ON public.user_api_keys
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- UPDATE: Пользователи могут обновлять свои ключи (WITH CHECK ВАЖЕН!)
CREATE POLICY "Users can update own keys"
ON public.user_api_keys
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- DELETE: Пользователи могут удалять свои ключи
CREATE POLICY "Users can delete own keys"
ON public.user_api_keys
FOR DELETE
USING (auth.uid() = user_id);

-- Убедитесь, что authenticated пользователи имеют права
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_api_keys TO authenticated;
```

### Шаг 2: Перезапустить backend

```bash
python backend/main.py
```

## Проверка

1. Попробуйте добавить или обновить API ключ через интерфейс
2. Ошибка `new row violates row-level security policy` должна исчезнуть
3. Ошибка 403 `Доступ запрещён. Проверьте RLS политики` должна исчезнуть

## Что было исправлено в коде

### 1. Модель `APIKeyUpdate` (backend/api/frontend_routes.py)

**До:**
```python
class APIKeyUpdate(BaseModel):
    name: Optional[str] = None
    model_preference: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
```

**После:**
```python
class APIKeyUpdate(BaseModel):
    api_key: Optional[str] = None  # ← Добавлено!
    name: Optional[str] = None
    model_preference: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
```

### 2. Эндпоинт `PATCH /api/v1/keys/{key_id}`

**Раньше** мог обновлять только: name, model_preference, is_default, is_active  
**Теперь** может обновлять и сам ключ (api_key) с автоматическим шифрованием

### 3. RLS политики в Supabase

**Проблема:** UPDATE политика не имела WITH CHECK  
**Исправление:** Добавлен WITH CHECK для гарантии, что обновленная строка остается в области видимости пользователя

```sql
CREATE POLICY "Users can update own keys"
ON public.user_api_keys
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);  -- ← Добавлено!
```

## Автоматическое применение (PowerShell)

```powershell
cd scripts
.\fix_rls_policies.ps1
```

## Полная документация

Смотрите [RLS_FIX_GUIDE.md](./docs/RLS_FIX_GUIDE.md) для подробной информации о RLS политиках.
