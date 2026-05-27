# 🚀 СРОЧНО: Как исправить ошибку 401 с RLS

## Проблема

Вы видите в логах:
```
POST https://hgjbjccpeirwrabbcjhr.supabase.co/rest/v1/user_api_keys "HTTP/2 401 Unauthorized"
ERROR - Failed to insert key: 'new row violates row-level security policy'
```

## Решение (3 шага, 2 минуты)

### Шаг 1: Откройте Supabase SQL Editor

1. Откройте https://supabase.com/dashboard (войдите)
2. Выберите ваш проект
3. Нажмите **SQL Editor** в левом меню
4. Нажмите **New query** (или синяя кнопка +)

### Шаг 2: Скопируйте ЭТОТ точный SQL

**ВАЖНО:** Скопируйте БЕЗ маркдаун-символов!

```
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

### Шаг 3: Вставьте и выполните

1. Очистите редактор (удалите всё)
2. Вставьте SQL из шага 2
3. Нажмите **Run** или Ctrl+Enter
4. Ждите результата - должна появиться **зелёная галка** ✅

## Готово!

**Теперь закройте интерфейс и откройте его заново, попробуйте добавить ключ.**

Должно работать! ✅

---

**Если по-прежнему ошибка 401:**
- Попробуйте перезагрузить страницу (F5)
- Перезапустите backend: `python backend/main.py`
- Смотрите `/FIX_RLS_README.md` для подробной диагностики
