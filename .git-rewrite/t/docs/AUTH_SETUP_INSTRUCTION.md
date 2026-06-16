# 🔐 Инструкция по настройке аутентификации

## Проблема
Frontend получает 401 ошибку при запросах к API, даже если пользователь вошел в систему.

## Причина
1. Токен доступа (access_token) истек
2. Frontend не использует refresh_token для обновления токена
3. Миграция RLS не была применена к базе данных

## Решение

### Шаг 1: Применить миграцию RLS (ОБЯЗАТЕЛЬНО!)

1. Откройте Supabase Dashboard: https://app.supabase.com
2. Выберите ваш проект (hgjbjccpeirwrabbcjhr)
3. Перейдите в **SQL Editor**
4. Скопируйте и выполните содержимое файла:
   ```
   backend/database/migrations/006_fix_rls_and_auth.sql
   ```

**Важно:** Без этого шага аутентификация не будет работать корректно!

### Шаг 2: Очистить localStorage и перезайти

1. Откройте браузер
2. Нажмите F12 → Application → Local Storage → http://localhost:5174
3. Удалите все ключи:
   - `access_token`
   - `refresh_token`
   - `user`
4. Обновите страницу
5. Зарегистрируйте нового пользователя или войдите

### Шаг 3: Проверить работу API

После входа откройте консоль разработчика (F12) и выполните:

```javascript
// Проверка токена
const token = localStorage.getItem('access_token');
console.log('Token:', token ? '✅ Токен есть' : '❌ Токена нет');

// Тестовый запрос
fetch('/api/v1/auth/me', {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(r => r.json())
.then(d => console.log('✅ Профиль:', d))
.catch(e => console.error('❌ Ошибка:', e));
```

### Шаг 4: Обновить frontend (опционально, для поддержки refresh_token)

Создайте файл `frontend/src/utils/auth.js`:

```javascript
/**
 * Утилита для управления аутентификацией
 * Автоматически обновляет токен через refresh_token
 */

export async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  
  if (!refreshToken) {
    console.warn('❌ Refresh token не найден');
    return false;
  }
  
  try {
    const response = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      headers: {
        'X-Refresh-Token': refreshToken,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      console.error('❌ Не удалось обновить токен:', response.status);
      return false;
    }
    
    const data = await response.json();
    
    // Сохраняем новые токены
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    
    console.log('✅ Токен успешно обновлен');
    return true;
    
  } catch (error) {
    console.error('❌ Ошибка при обновлении токена:', error);
    return false;
  }
}

export async function fetchWithAuth(url, options = {}) {
  let token = localStorage.getItem('access_token');
  
  if (!token) {
    throw new Error('Требуется аутентификация');
  }
  
  // Пробуем выполнить запрос
  let response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    }
  });
  
  // Если токен истек (401), пробуем обновить
  if (response.status === 401) {
    const refreshed = await refreshAccessToken();
    
    if (refreshed) {
      // Повторяем запрос с новым токеном
      token = localStorage.getItem('access_token');
      response = await fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          'Authorization': `Bearer ${token}`
        }
      });
    } else {
      // Не удалось обновить - выходим
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      window.location.reload();
    }
  }
  
  return response;
}
```

Затем обновите `frontend/src/App.jsx`:

```javascript
// Замените обычный fetch на fetchWithAuth
import { fetchWithAuth } from './utils/auth';

// В функции fetchKeys:
const response = await fetchWithAuth('/api/v1/keys?offset=0&limit=100');
```

### Шаг 5: Проверить логи backend

Запустите backend с подробным логированием:

```bash
# Остановите текущий backend
# Запустите с отладкой
python -m uvicorn backend.main:app --reload --port 8080 --log-level debug
```

Смотрите логи при попытке аутентификации.

## Быстрая проверка работоспособности

### 1. Проверьте подключение к Supabase

```bash
# Создайте тестовый скрипт check_auth.py
python -c "
from backend.core.supabase_client import get_supabase
supabase = get_supabase()
if supabase:
    print('✅ Supabase подключен')
    # Проверка таблиц
    try:
        result = supabase.table('users').select('count').limit(1).execute()
        print('✅ Таблица users доступна')
    except Exception as e:
        print(f'❌ Ошибка доступа к users: {e}')
else:
    print('❌ Supabase не подключен')
"
```

### 2. Создайте тестового пользователя через скрипт

```bash
python scripts/seed_data.py
```

### 3. Войдите через curl

```bash
# Регистрация (если еще не зарегистрированы)
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@padplus.ai", "password": "TestPassword123!"}'

# Вход
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@padplus.ai", "password": "TestPassword123!"}'

# Скопируйте access_token из ответа
# Проверьте профиль
curl -X GET http://localhost:8080/api/v1/auth/me \
  -H "Authorization: Bearer <ваш_токен>"
```

## Часто задаваемые вопросы

### Q: Почему 401 ошибка возникает сразу после входа?
A: Скорее всего, не применена миграция RLS (шаг 1). Без неё запросы к базе данных блокируются.

### Q: Как проверить, что миграция применена?
A: В Supabase Dashboard → SQL Editor выполните:
```sql
SELECT * FROM check_tables_exist();
```
Должны вернуться все таблицы со статусом `true`.

### Q: Токен быстро истекает, что делать?
A: Используйте refresh_token для автоматического обновления (шаг 4).

### Q: Можно ли увеличить время жизни токена?
A: Да, в Supabase Dashboard → Authentication → Settings → Token Settings.

## Контакты для помощи

Если проблемы остались:
1. Проверьте логи backend (должны быть подробные ошибки)
2. Проверьте консоль браузера (F12)
3. Убедитесь, что все шаги выполнены по порядку

## Важные файлы

- `backend/core/auth_manager.py` - Логика аутентификации
- `backend/api/frontend_routes.py` - API endpoints
- `backend/database/migrations/006_fix_rls_and_auth.sql` - Миграция RLS
- `scripts/seed_data.py` - Скрипт создания тестовых данных