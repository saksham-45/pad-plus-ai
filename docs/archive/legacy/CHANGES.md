# ✅ Исправление: Обновление ключей провайдеров

## Проблема

Пользователи **не могли изменять ключи провайдеров** через интерфейс. Возникала ошибка RLS (Row Level Security):
```
ERROR - Failed to update key: 'new row violates row-level security policy'
```

## Причины

1. **Эндпоинт обновления ключа** не поддерживал обновление самого ключа (api_key_encrypted)
2. **RLS политика UPDATE** не имела WITH CHECK условия для проверки новых значений
3. **Модель данных** APIKeyUpdate не включала поле api_key

## Решение

### ✅ 1. Обновлена модель APIKeyUpdate

**Файл:** `backend/api/frontend_routes.py` (строки 70-75)

```python
class APIKeyUpdate(BaseModel):
    api_key: Optional[str] = None  # ← Добавлено для обновления ключа!
    name: Optional[str] = None
    model_preference: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
```

### ✅ 2. Улучшен эндпоинт обновления ключа

**Файл:** `backend/api/frontend_routes.py` (строка 701)

Эндпоинт `PATCH /api/v1/keys/{key_id}` теперь:
- ✅ Принимает новый ключ (api_key)
- ✅ Автоматически шифрует новый ключ перед сохранением
- ✅ Логирует операции обновления
- ✅ Обрабатывает ошибки RLS с понятными сообщениями

```python
if data.api_key is not None:
    encrypted_key = encryptor.encrypt(data.api_key)
    update_data["api_key_encrypted"] = encrypted_key
```

### ✅ 3. Исправлены RLS политики

**Файлы:**
- `backend/database/migrations/007_fix_api_keys_rls.sql`
- `scripts/fix_providers_rls.sql`

**Главное исправление:** Добавлен WITH CHECK к UPDATE политике:

```sql
CREATE POLICY "Users can update own keys"
ON public.user_api_keys
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);  -- ← Добавлено!
```

WITH CHECK гарантирует, что обновленная строка остается в области видимости пользователя (user_id не меняется).

### ✅ 4. Обновлена документация

- `FIX_RLS_README.md` - обновлены инструкции по исправлению
- `APPLY_RLS_FIX.md` - новая быстрая инструкция для применения

## Как применить исправление

### Шаг 1: Обновить RLS политики в Supabase (⚠️ Обязательно!)

1. Откройте [Supabase Dashboard](https://supabase.com/dashboard)
2. Выберите проект
3. **SQL Editor** → **New query**
4. Скопируйте содержимое `scripts/fix_providers_rls.sql`
5. Нажмите **Run**

Или используйте PowerShell:
```powershell
cd scripts
.\fix_rls_policies.ps1
```

### Шаг 2: Перезапустить backend

```bash
python backend/main.py
```

### Шаг 3: Проверить работу

1. Откройте интерфейс
2. Перейдите в "Настройки" → "API ключи"
3. Нажмите "Изменить" на любом ключе
4. Измените ключ, название или модель
5. Нажмите "Сохранить"

**Результат:** ✅ Ключ должен обновиться без ошибок

## Дополнительные изменения

- ✅ Добавлено логирование операций обновления ключей
- ✅ Улучшена обработка ошибок (различие между 403 и 500)
- ✅ Добавлены GRANT права для authenticated пользователей

## Что теперь работает

| Операция | Было | Стало |
|----------|------|-------|
| Добавить ключ | ✅ | ✅ |
| Удалить ключ | ✅ | ✅ |
| Изменить название | ✅ | ✅ |
| Изменить модель | ✅ | ✅ |
| **Изменить сам ключ** | ❌ | ✅ |
| Установить по умолчанию | ✅ | ✅ |

## Файлы, которые были изменены

1. `backend/api/frontend_routes.py` - модель и эндпоинт
2. `backend/database/migrations/007_fix_api_keys_rls.sql` - RLS политики
3. `scripts/fix_providers_rls.sql` - RLS политики (вспомогательный)
4. `FIX_RLS_README.md` - документация
5. `APPLY_RLS_FIX.md` - быстрая инструкция *(новый файл)*

---

**Статус:** ✅ Готово к применению

Для подробной информации смотрите `/APPLY_RLS_FIX.md`
