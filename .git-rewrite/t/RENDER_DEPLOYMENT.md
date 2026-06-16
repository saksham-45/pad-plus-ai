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

## ✅ Что было исправлено

### 1. Скрипт миграций базы данных
**Проблема:** Скрипт `apply_migrations.py` только выводил инструкции, но не применял миграции.

**Решение:** Переписан скрипт с использованием `psycopg2` для прямого выполнения SQL через `DATABASE_URL`.

### 2. Production конфигурация
**Проблема:** Backend не был оптимизирован для production.

**Решение:** 
- Используется `gunicorn` с `uvicorn.workers.UvicornWorker`
- Порт берётся из переменной `$PORT` (стандарт Render)
- Отключён `reload` в production
- Настроен CORS для динамических доменов Render

### 3. Frontend сборка
**Решение:** 
- Настроен `base: '/'` в `vite.config.js`
- Оптимизирована сборка с `manualChunks`

## 🚀 Шаги деплоя

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

## 📞 Поддержка

При проблемах проверьте:
1. Logs на Render (Build + Runtime)
2. Переменные окружения
3. Актуальность кода на GitHub
