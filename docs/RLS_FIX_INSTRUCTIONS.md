# 🔧 ИНСТРУКЦИЯ ПО ИСПРАВЛЕНИЮ RLS

## 🎯 **ПРОБЛЕМА:**
Backend запущен с `main.py` и пытается сохранить API ключи в Supabase, но RLS политики блокируют доступ:
```
❌ 'new row violates row-level security policy for table "user_api_keys"'
❌ The read operation timed out
```

## ✅ **РЕШЕНИЕ:**

### **ШАГ 1: Откройте Supabase SQL Editor**
1. Зайдите в [Supabase Dashboard](https://supabase.com/dashboard)
2. Выберите ваш проект `hgjbjccpeirwrabbcjhr`
3. Перейдите в `SQL Editor`
4. Создайте новый запрос

### **ШАГ 2: Выполните SQL код**
Скопируйте и выполните этот SQL код:

```sql
-- СРОЧНОЕ ИСПРАВЛЕНИЕ RLS - ВЫПОЛНИТЬ НЕМЕДЛЕННО В SUPABASE
-- Проблема: RLS политики существуют но RLS отключен для таблицы

-- 1. Включаем RLS для таблицы user_api_keys
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

-- 2. Если политики отсутствуют, создаем их
CREATE POLICY IF NOT EXISTS "Users can view own keys" ON public.user_api_keys
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY IF NOT EXISTS "Users can insert own keys" ON public.user_api_keys
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY IF NOT EXISTS "Users can update own keys" ON public.user_api_keys
    FOR UPDATE USING (auth.uid()::text = user_id::text);

CREATE POLICY IF NOT EXISTS "Users can delete own keys" ON public.user_api_keys
    FOR DELETE USING (auth.uid()::text = user_id::text);

-- 3. Убеждаемся что права установлены правильно
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_api_keys TO authenticated;
GRANT SELECT ON public.user_api_keys TO anon;

-- 4. Финальная проверка
SELECT 'RLS Status:' as info;
SELECT 
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables 
WHERE tablename = 'user_api_keys';

SELECT count(*) as policy_count 
FROM pg_policies 
WHERE tablename = 'user_api_keys';
```

### **ШАГ 3: Проверьте результат**
После выполнения SQL вы должны увидеть:
- `rls_enabled = true`
- `policy_count = 4` (или больше)

### **ШАГ 4: Перезапустите backend**
```bash
# Остановите текущий backend (Ctrl+C)
# Перезапустите
cd "c:\пад ал датабаз а  чистый\PAD+ AI чистый"
$env:PORT="8080"
C:\Python314\python.exe backend/main.py
```

---

## 🔄 **ЧЕК-ЛИСТ ПОСЛЕ ИСПРАВЛЕНИЯ:**

- [ ] SQL выполнен без ошибок
- [ ] RLS включен для таблицы `user_api_keys`
- [ ] 4 политики созданы (SELECT, INSERT, UPDATE, DELETE)
- [ ] Backend перезапущен
- [ ] API ключи создаются без ошибок
- [ ] Список ключей загружается

---

## 🚨 **ЕСЛИ ПРОБЛЕМА ОСТАЕТСЯ:**

### **Вариант 1: Временное отключение RLS**
```sql
-- Временно отключаем RLS для тестирования
ALTER TABLE public.user_api_keys DISABLE ROW LEVEL SECURITY;
```

### **Вариант 2: Используйте main_stable.py**
```bash
# Используйте стабильную версию без Supabase
C:\Python314\python.exe backend/main_stable.py
```

---

## 📊 **ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:**

После исправления RLS:
- ✅ API ключи будут сохраняться в Supabase
- ✅ Список ключей будет загружаться
- ✅ Авторизация будет работать полностью
- ✅ Backend не будет падать с ошибками

---

**ВЫПОЛНИТЕ SQL И ПЕРЕЗАПУСТИТЕ BACKEND!**
