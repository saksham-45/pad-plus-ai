# 🆘 СРОЧНОЕ РЕШЕНИЕ: SQL без приведения типов

Копируйте этот SQL и выполните в Supabase SQL Editor:

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

CREATE POLICY "Users can view own keys" ON public.user_api_keys FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own keys" ON public.user_api_keys FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own keys" ON public.user_api_keys FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can delete own keys" ON public.user_api_keys FOR DELETE USING (auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_api_keys TO authenticated;
```

## Что это делает

- Удаляет **ВСЕ** старые политики (включая с приведением типов)
- Создает новые политики **БЕЗ** ::text приведения
- Даёт права authenticated пользователям

## Как выполнить

1. Откройте Supabase Dashboard → SQL Editor → New query
2. **Очистите редактор**
3. Скопируйте весь SQL выше
4. Нажмите **Run**
5. Дождитесь зелёной галки ✅

## Потом

1. **Перезагрузите интерфейс** (F5)
2. **Перезапустите backend** (`python backend/main.py`)
3. **Попробуйте добавить ключ**

---

## Если и это не поможет

Выполните этот SQL для отключения RLS (для диагностики):

```sql
ALTER TABLE public.user_api_keys DISABLE ROW LEVEL SECURITY;
```

И попробуйте добавить ключ. Если сработает - проблема в RLS политиках, нужны другие варианты. Если не сработает - проблема в backend коде.

Сообщите результат!
