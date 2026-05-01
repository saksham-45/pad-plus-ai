# 🔐 Исправление ошибок 401 Unauthorized и 500 Internal Server Error

## Дата: 2026-04-08

## Проблемы

### 1. Ошибки 401 Unauthorized
**Симптомы:**
- Пользователи не могут войти в систему
- Токены не валидируются корректно
- Отсутствует обработка истекших токенов

**Корневые причины:**
- Функция `get_current_user()` не поддерживала refresh_token
- Все исключения оборачивались в 401, скрывая реальные проблемы
- Отсутствовала валидация формата JWT токена

### 2. Ошибки 500 Internal Server Error
**Симптомы:**
- Сервер возвращает 500 при запросах к базе данных
- Таблицы созданы, но не содержат данных
- RLS политики блокируют запросы

**Корневые причины:**
- Несогласованное сравнение UUID в RLS политиках (`::text` vs прямой UUID)
- Отсутствовали настройки пользователя по умолчанию
- При регистрации не создавались автоматически `user_settings`

## Реализованные исправления

### 1. Улучшенный модуль аутентификации (`backend/core/auth_manager.py`)

**Новые возможности:**
- ✅ Валидация формата JWT токена перед отправкой в Supabase
- ✅ Автоматическое обновление токена через refresh_session()
- ✅ Разделение ошибок аутентификации (401) и сервера (500)
- ✅ Детальное логирование ошибок
- ✅ Поддержка заголовка `X-Refresh-Token`

**Ключевые функции:**
```python
# Валидация формата JWT
auth_manager.validate_token_format(token)

# Валидация с автоматическим обновлением
auth_data, new_token, error = await auth_manager.validate_and_refresh(
    supabase, token, refresh_token
)

# Безопасное получение текущего пользователя
current_user = await get_current_user_safe(authorization, x_refresh_token)
```

### 2. Обновленные маршруты аутентификации

**Изменения в `backend/api/frontend_routes.py` и `backend/api/user_routes.py`:**
```python
async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_refresh_token: Optional[str] = Header(None, alias="X-Refresh-Token")
) -> dict:
    """Улучшенная версия с поддержкой refresh_token"""
    from core.auth_manager import get_current_user_safe
    return await get_current_user_safe(authorization, x_refresh_token)
```

### 3. Исправление RLS политик (`backend/database/migrations/006_fix_rls_and_auth.sql`)

**Изменения:**
- ✅ Удалены старые политики с несогласованным сравнением `::text`
- ✅ Созданы новые политики с прямым сравнением UUID: `auth.uid() = id`
- ✅ Добавлен триггер для автоматического создания `user_settings` при регистрации
- ✅ Добавлена функция `check_tables_exist()` for проверки состояния БД

**Пример исправленной политики:**
```sql
-- Было (неправильно):
USING (auth.uid()::text = id::text)

-- Стало (правильно):
USING (auth.uid() = id)
```

### 4. Скрипт для создания тестовых данных (`scripts/seed_data.py`)

**Функциональность:**
- ✅ Создание тестового пользователя
- ✅ Автоматическое создание настроек пользователя
- ✅ Создание тестового API ключа (опционально)
- ✅ Проверка подключения к Supabase
- ✅ Проверка наличия всех необходимых таблиц

**Использование:**
```bash
python scripts/seed_data.py
```

## Инструкция по применению исправлений

### Шаг 1: Применить миграцию RLS

1. Откройте Supabase Dashboard: https://app.supabase.com
2. Перейдите в SQL Editor
3. Скопируйте и выполните содержимое файла:
   ```
   backend/database/migrations/006_fix_rls_and_auth.sql
   ```

### Шаг 2: Создать тестовые данные (опционально)

```bash
# Убедитесь, что .env файл настроен
cp .env.example .env
# Отредактируйте .env, указав SUPABASE_URL и SUPABASE_KEY

# Запустите скрипт
python scripts/seed_data.py
```

### Шаг 3: Перезапустить backend

```bash
# Остановите текущий сервер
# Запустите заново
python -m uvicorn backend.main:app --reload --port 8080
```

### Шаг 4: Протестировать аутентификацию

**Регистрация:**
```bash
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPassword123!"}'
```

**Вход:**
```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPassword123!"}'
```

**Получение профиля (с токеном):**
```bash
curl -X GET http://localhost:8080/api/v1/auth/me \
  -H "Authorization: Bearer <ваш_access_token>"
```

## Ожидаемые результаты

После применения исправлений:

1. **Аутентификация работает корректно:**
   - Пользователи могут регистрироваться и входить
   - Токены валидируются правильно
   - Истекшие токены автоматически обновляются (при наличии refresh_token)

2. **Ошибки 500 устранены:**
   - RLS политики не блокируют запросы
   - Настройки пользователя создаются автоматически
   - Запросы к базе данных выполняются успешно

3. **Улучшенное логирование:**
   - Ошибки аутентификации детально логируются
   - Легко определить причину проблемы

## Переменные окружения

Убедитесь, что в `.env` файле настроены:

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anonymous-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Шифрование
ENCRYPTION_KEY=your-encryption-key
ENCRYPTION_SALT=your-encryption-salt

# CSRF защита
CSRF_SECRET_KEY=your-csrf-secret-key
```

## Тестовые сценарии

### Сценарий 1: Регистрация и вход
1. Зарегистрируйте нового пользователя
2. Войдите с теми же credentials
3. Получите профиль пользователя
4. ✅ Все запросы должны вернуть 200 OK

### Сценарий 2: Истекший токен
1. Войдите в систему
2. Дождитесь истечения access_token (по умолчанию 1 час)
3. Отправьте запрос с истекшим токеном и refresh_token
4. ✅ Система должна автоматически обновить токен

### Сценарий 3: Настройки пользователя
1. Войдите как новый пользователь
2. Запросите настройки (`GET /api/v1/user/settings`)
3. ✅ Должны вернуться настройки по умолчанию

## Примечания

- При использовании service_role ключа RLS политики не применяются
- Для production среды обязательно настройте HTTPS
- Регулярно обновляйте ключи шифрования
- Храните refresh_token в безопасном месте (httpOnly cookies)

## Связанные файлы

- `backend/core/auth_manager.py` - Новый модуль аутентификации
- `backend/api/frontend_routes.py` - Обновленные маршруты
- `backend/api/user_routes.py` - Обновленные маршруты
- `backend/database/migrations/006_fix_rls_and_auth.sql` - Исправление RLS
- `scripts/seed_data.py` - Скрипт для seed данных