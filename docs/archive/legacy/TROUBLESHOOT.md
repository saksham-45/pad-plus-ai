# 🔍 ТЕСТ: Отключение RLS для диагностики

Если RLS политики действительно применены, но не работают, нужно понять причину.

## Шаг 1: Проверьте, какие политики есть в Supabase

**Выполните этот SQL в Supabase:**

```sql
SELECT policyname, cmd, qual, with_check 
FROM pg_policies 
WHERE tablename = 'user_api_keys'
ORDER BY policyname;
```

Покажите результат.

## Шаг 2: Если политик нет - создайте ИХ ПРАВИЛЬНО

Проблема может быть в том, что политики с приведением типов не работают в вашей версии Supabase.

**Попробуйте эти политики БЕЗ приведения типов:**

```sql
ALTER TABLE public.user_api_keys DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can insert own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can update own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can delete own keys" ON public.user_api_keys;

ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

-- ВАРИАНТ 1: БЕЗ приведения типов (классический)
CREATE POLICY "Users can view own keys" ON public.user_api_keys FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own keys" ON public.user_api_keys FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own keys" ON public.user_api_keys FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can delete own keys" ON public.user_api_keys FOR DELETE USING (auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_api_keys TO authenticated;
```

## Шаг 3: Если и это не поможет - отключите RLS полностью

Это для диагностики, чтобы понять, в RLS ли проблема:

```sql
ALTER TABLE public.user_api_keys DISABLE ROW LEVEL SECURITY;
```

После этого попробуйте добавить ключ в интерфейсе.

**Если работает:**
- Проблема ТОЧНО в RLS политиках
- Нужно переделать политики правильно

**Если не работает:**
- Проблема в коде backend
- Нужно проверить, правильно ли передаётся user_id

---

## Что нужно проверить

1. **В Supabase:** какие именно политики есть сейчас?
2. **Попробуйте вариант БЕЗ приведения типов**
3. **Если не сработает** - отключите RLS и сообщите результат

Покажите: результат SELECT policyname запроса и логи при попытке добавить ключ.
