# 🔍 ДИАГНОСТИКА: Проверка текущего состояния RLS

Запустите **ЭТО** в Supabase SQL Editor для диагностики:

## Шаг 1: Проверьте текущие политики

```sql
-- Показать ВСЕ текущие политики для user_api_keys
SELECT policyname, cmd, qual, with_check 
FROM pg_policies 
WHERE tablename = 'user_api_keys'
ORDER BY policyname;
```

**Что вы должны увидеть:**
- 4 политики (Users can view own keys, insert, update, delete)
- В колонке `qual` должно быть: `((auth.uid())::text = (user_id)::text)`

**Если политик нет или они неправильные** → идите на Шаг 2

## Шаг 2: ПОЛНОЕ исправление (выполните ВСЁ по порядку)

```sql
-- 1. Отключаем RLS временно
ALTER TABLE public.user_api_keys DISABLE ROW LEVEL SECURITY;

-- 2. УДАЛЯЕМ ВСЕ старые политики (даже если их нет)
DROP POLICY IF EXISTS "Users can view own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can insert own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can update own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Users can delete own keys" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут просматривать свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут вставлять свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут обновлять свои ключи" ON public.user_api_keys;
DROP POLICY IF EXISTS "Пользователи могут удалять свои ключи" ON public.user_api_keys;

-- 3. Включаем RLS обратно
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

-- 4. Создаем новые политики с приведением типов (::text) - ЭТО ВАЖНО!
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

-- 5. Даём права authenticated пользователям
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_api_keys TO authenticated;

-- 6. Проверяем результат
SELECT policyname, cmd 
FROM pg_policies 
WHERE tablename = 'user_api_keys'
ORDER BY policyname;
```

**Выполните ВСЕ команды выше в одном запросе!**

## Шаг 3: После SQL

1. Посмотрите результат последней команды (SELECT)
2. Должно быть 4 политики ✅
3. **Перезагрузите интерфейс** (F5)
4. **Перезапустите backend**: `python backend/main.py`
5. Попробуйте добавить ключ

---

## Если по-прежнему ошибка 500

Проверьте логи backend на наличие:
```
ERROR - Failed to insert key:
```

И покажите полную ошибку из логов.

Возможно, есть другая проблема (не RLS, а что-то в коде).
