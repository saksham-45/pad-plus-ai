# 🚀 Применение исправления RLS для обновления ключей

## Что было исправлено

1. **Модель API** - добавлена поддержка обновления самого ключа (api_key)
2. **Эндпоинт** - теперь может обновлять ключи с автоматическим шифрованием
3. **RLS политики** - добавлены политики с правильным приведением типов (::text)

## Применение исправления (2 минуты)

### ⚠️ ВАЖНО: Используется приведение типов (::text)

Это критически важно для совместимости UUID в Supabase!

### 🎯 Способ 1: Через Supabase Dashboard (Рекомендуется)

1. Откройте [Supabase Dashboard](https://supabase.com/dashboard) и войдите
2. Выберите ваш проект
3. Перейдите в **SQL Editor** → **New query**
4. **Очистите редактор полностью** (удалите всё, что там было)
5. Скопируйте этот точный SQL и вставьте:

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

6. Нажмите **Run** (или Ctrl+Enter)
7. Должна появиться зелёная галка "Success"

### 🎯 Способ 2: Через командную строку (PowerShell)

```powershell
cd scripts
.\fix_rls_policies.ps1
```

## Проверка

После применения исправления:

1. **Откройте интерфейс**
   - Перейдите в "Настройки" → "API ключи"
2. **Добавьте новый ключ:**
   - Нажмите "Добавить ключ"
   - Введите данные (провайдер, ключ, название)
   - Нажмите "Сохранить"
   
   **Результат:** ✅ Ключ должен добавиться без ошибок 500

3. **Обновите существующий ключ:**
   - Нажмите на три точки рядом с ключом
   - Выберите "Изменить"
   - Обновите ключ, название или модель
   - Нажмите "Сохранить"
   
   **Результат:** ✅ Ключ должен обновиться без ошибок

4. **Проверьте логи backend:**
   ```
   ✅ Key updated successfully: key_id=...
   ✅ Creating key: provider=...
   ```

## Что если ошибка `401 Unauthorized` сохраняется?

**Проблема:** Это означает, что RLS политики не были применены или неправильно применены.

**Решение:**

1. **Проверьте, что вы используете правильный SQL** - должно быть приведение типов `(auth.uid())::text = (user_id)::text`

2. **Проверьте в Supabase, что политики созданы:**
   - Откройте **SQL Editor**
   - Выполните проверку:
   ```sql
   SELECT policyname, cmd FROM pg_policies WHERE tablename = 'user_api_keys' ORDER BY policyname;
   ```
   - Должны быть 4 политики:
     - Users can delete own keys
     - Users can insert own keys
     - Users can update own keys
     - Users can view own keys

3. **Если политик нет или они неправильные:**
   - Удалите их все заново через Dashboard
   - Повторите SQL еще раз
   - Убедитесь, что нет ошибок (ищите `ERROR` в результатах)

4. **Если по-прежнему не работает:**
   - Попробуйте отключить RLS полностью для тестирования:
     ```sql
     ALTER TABLE public.user_api_keys DISABLE ROW LEVEL SECURITY;
     ```
   - Проверьте, работает ли добавление ключа
   - Если работает - проблема в RLS политиках
   - Затем включите RLS и примените политики снова

## Что находится в файлах

- **`scripts/fix_providers_rls.sql`** - основной SQL с политиками и приведением типов
- **`backend/database/migrations/007_fix_api_keys_rls.sql`** - миграция для git
- **`backend/api/frontend_routes.py`** - обновленный эндпоинт с поддержкой обновления ключа

## Готово! ✅

После успешного применения SQL исправления backend вы сможете:
- ✅ Добавлять новые API ключи
- ✅ Обновлять существующие ключи (сам ключ, название, модель)
- ✅ Удалять ключи
- ✅ Устанавливать ключ по умолчанию

---

**Если остались вопросы:**
- Смотрите `/FIX_RLS_README.md` для подробной информации
- Смотрите `/docs/RLS_FIX_GUIDE.md` для технических деталей
- Проверьте логи backend на ошибки RLS (ищите "42501" в ошибке)
