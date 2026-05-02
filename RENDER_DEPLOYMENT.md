Web Service
pad-plus-ai
Python 3
Free
Upgrade your instance

Connect

Manual Deploy
Service ID:
srv-d7qgile8bjmc73epstj0

Ovladimirovich / PAD-AI-v3.5
main
https://pad-ai-v3-5.onrender.com

Your free instance will spin down with inactivity, which can delay requests by 50 seconds or more.
Upgrade now

Filter events31
Deploy started for 8b56ca3: fix: nonlocal declaration order in safety step
Manually triggered by you via Dashboard
May 2, 2026 at 6:41 AM# 📋 Руководство по развертыванию на Render

## ⚠️ КРИТИЧЕСКИЕ ПРОБЛЕМЫ И ИХ РЕШЕНИЯ

### Проблема 1: "Port scan timeout reached, no open ports detected"

**Симптом:**
```
==> Port scan timeout reached, no open ports detected. Bind your service to at least one port.
```

**Причина:**
В `render.yaml` команда запуска использует `$PORT`, но YAML не подставляет переменные окружения автоматически.

**Решение:**
Использовать shell-обёртку для правильной подстановки переменной:

```yaml
startCommand: sh -c 'gunicorn --worker-class uvicorn.workers.UvicornWorker --workers 1 --bind 0.0.0.0:${PORT} backend.main:app'
```

**Дополнительные проверки:**
1. Убедитесь что `backend/main.py` читает PORT: `port = int(os.getenv("PORT", backend_port))`
2. Проверьте логи: должен быть лог `🚀 Starting server on port XXXX`
3. Убедитесь что gunicorn установлен в `requirements.txt`

---

### Проблема 2: Неправильный синтаксис EXPOSE в Dockerfile

**Симптом:**
Docker некорректно обрабатывает `EXPOSE $PORT`

**Решение:**
Использовать фиксированный порт:
```dockerfile
EXPOSE 8000
```

---

## ✅ Что было исправлено

### 1. Скрипт миграций базы данных
**Проблема:** Скрипт `apply_migrations.py` только выводил инструкции, но не применял миграции.

**Решение:** Переписан скрипт с использованием `psycopg2` для прямого выполнения SQL через `DATABASE_URL`.

### 2. Production конфигурация
**Проблема:** Backend не был оптимизирован для production и не привязывался к порту.

**Решение:** 
- Используется `gunicorn` с `uvicorn.workers.UvicornWorker` в production
- Порт берётся из переменной `$PORT` (стандарт Render)
- Отключён `reload` в production
- Настроен CORS для динамических доменов Render
- Исправлен `start_server.py` для автоматического определения production среды
- Обновлен `render.yaml` для использования gunicorn напрямую

### 3. Frontend сборка
**Решение:** 
- Настроен `base: '/'` в `vite.config.js`
- Оптимизирована сборка с `manualChunks`

## 🚀 Шаги деплоя

### Шаг 0: Исправление конфигурации Render

**ВАЖНО:** В `render.yaml` команда запуска должна использовать shell-подстановку для PORT:

```yaml
startCommand: sh -c 'gunicorn --worker-class uvicorn.workers.UvicornWorker --workers 1 --bind 0.0.0.0:${PORT} backend.main:app'
```

Это гарантирует, что переменная окружения `$PORT` будет правильно подставлена при запуске.

### Шаг 1: Убедитесь, что переменные окружения настроены

В панели Render добавьте следующие переменные:

```
SUPABASE_URL=ваша_supabase_url
SUPABASE_KEY=ваш_supabase_key
CSRF_SECRET_KEY=сгенерированный_ключ (python -c "import secrets; print(secrets.token_urlsafe(32))")
ENCRYPTION_KEY=сгенерированный_ключ (python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_SALT=сгенерированный_ключ (python -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())")
LOG_LEVEL=info
```

### Шаг 2: Push изменений на GitHub

```bash
git add .
git commit -m "fix: render deployment fixes"
git push origin main
```

### Шаг 3: Перезапуск сервиса на Render

1. Зайдите в панель Render
2. Выберите ваш сервис
3. Нажмите **"Manual Deploy"** → **"Deploy latest commit"**

### Шаг 4: Проверка логов

Следите за логами build и runtime:
- Build logs: покажут успешное применение миграций
- Runtime logs: покажут запуск backend

## 🔍 Проверка работы

### Health check
```bash
curl https://your-app.onrender.com/health
```

### Проверка миграций
В логах build должно быть:
```
✅ Миграция успешно применена: 001_initial_schema.sql
✅ Миграция успешно применена: 002_rls_policies.sql
...
ГОТОВО! Применено миграций: 6/6
```

### Проверка базы данных
В логах запуска должно быть:
```
✅ Подключение к PostgreSQL успешно
✅ ANTI_DIRECTIVE проверена
🚀 PAD+ AI готов к работе!
```

## ⚠️ Важные замечания

1. **DATABASE_URL** на Render автоматически создаётся из PostgreSQL сервиса
2. **FRONTEND_URL** - опционально, если не указано - CORS работает с любыми onrender.com доменами
3. **Миграции** применяются только при сборке (build), не при каждом запуске
4. **Redis** автоматически подключается через `REDIS_URL`
5. **ChromaDB модель** предзагружается во время build чтобы избежать задержек при первом запросе
6. **Бесплатный тариф** имеет ограничения:
   - 1GB диск
   - Сервис засыпает после 15 минут бездействия
   - Первый запрос после сна ~50 секунд

## 🚀 Оптимизация производительности

### Проблема: Медленный первый чат

**Причина:** ChromaDB загружает embedding модель (79MB) при первом использовании

**Решение:** Модель предзагружается в `buildCommand` через `preload_chroma_model.py`

### Проблема: Сервис засыпает

**Решение A - Upgrade на платный тариф ($7/месяц):**
- Сервис не засыпает
- Больше ресурсов (RAM, CPU)
- Нет задержек при первом запросе

**Решение B - Бесплатный пинг (обновление):**
- Используйте внешний сервис для ping (например, UptimeRobot)
- Настройте cron job каждые 15 минут

### Проблема: Ошибки при загрузке модели

Если в логах build видите:
```
/opt/render/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz: 0%|...
```

Это **нормально** - модель скачивается во время build. Дождитесь окончания:
```
✅ Модель успешно загружена!
```

Если процесс прерывается:
1. Увеличьте timeout build в настройках Render
2. Проверьте стабильность интернет-соединения на Render
3. Попробуйте Manual Deploy ещё раз

## 🆘 Устранение проблем

### Ошибка миграций
Если миграции не применяются:
1. Проверьте `DATABASE_URL` в переменных окружения
2. Убедитесь, что `psycopg2-binary` в `requirements.txt`
3. Посмотрите логи build на Render

### Ошибка CORS
Если фронтенд не может подключиться к бэкенду:
1. Проверьте `FRONTEND_URL` в переменных
2. Убедитесь, что frontend отправляет запросы на правильный домен

### Ошибка подключения к БД
1. Проверьте `SUPABASE_URL` и `SUPABASE_KEY`
2. Убедитесь, что таблицы созданы (смотрите логи миграций)

### Ошибка "Port scan timeout reached"
Если видите эту ошибку:

**Причина:** Render не может найти открытые порты, потому что сервис не привязывается к порту или привязывается к неверному порту.

**Решения:**

1. **Проверьте `render.yaml`:**
   ```yaml
   startCommand: sh -c 'gunicorn --worker-class uvicorn.workers.UvicornWorker --workers 1 --bind 0.0.0.0:${PORT} backend.main:app'
   ```
   Важно использовать `${PORT}` внутри shell-команды `sh -c '...'`

2. **Проверьте логи запуска:**
   В runtime logs должно быть:
   ```
   🚀 Starting server on port XXXX (production: true)
   ```
   
3. **Убедитесь что PORT определён:**
   В `backend/main.py` проверка:
   ```python
   backend_port = int(os.getenv("PORT", os.getenv("BACKEND_PORT", "8000")))
   ```
   
4. **Проверьте gunicorn workers:**
   Если gunicorn не запускается, проверьте логи build на наличие ошибок установки зависимостей

5. **Альтернативный вариант - использовать startCommand без shell:**
   ```yaml
   startCommand: gunicorn --worker-class uvicorn.workers.UvicornWorker --workers 1 --bind 0.0.0.0:8000 backend.main:app
   ```
   Render автоматически пробрасывает трафик на порт 8000 если PORT не определён

6. **Проверьте health check:**
   ```bash
   curl https://your-app.onrender.com/health
   ```

7. **Убедитесь что frontend/dist собран:**
   Если frontend не собран, приложение может упасть при старте

## 🧪 Тестирование конфигурации

### Локальное тестирование перед деплоем

```bash
# 1. Проверка переменных окружения
python -c "import os; print('PORT:', os.getenv('PORT', 'not set'))"

# 2. Тестирование start_server.py
python start_server.py

# 3. Проверка gunicorn команды
gunicorn --worker-class uvicorn.workers.UvicornWorker --workers 1 --bind 0.0.0.0:8000 backend.main:app

# 4. Health check
curl http://localhost:8000/health
```

### Проверка render.yaml

Убедитесь что в `render.yaml`:
- `startCommand` использует gunicorn с правильным путем к модулю
- Нет дублирования секций databases
- Все переменные окружения настроены

### Мониторинг деплоя

1. **Build Phase**: Следите за установкой зависимостей и миграциями
2. **Start Phase**: Ищите сообщение `🚀 Starting server on port XXXX`
3. **Health Check**: Render автоматически проверяет доступность порта

## 📞 Поддержка

При проблемах проверьте:
1. Logs на Render (Build + Runtime)
2. Переменные окружения
3. Актуальность кода на GitHub
4. Правильность команды запуска в render.yaml
