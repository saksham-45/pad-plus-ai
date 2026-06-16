# 🚀 Развёртывание PAD+ AI

**Последнее обновление:** 10.06.2026

---

## 🚨 КРИТИЧЕСКИЕ ШАГИ ПЕРЕД ДЕПЛОЕМ

### 1. Ротация ключей

```bash
# Генерация новых ключей шифрования
python -c "import base64, os; print('ENCRYPTION_KEY=' + base64.urlsafe_b64encode(os.urandom(32)).decode())"
python -c "import base64, os; print('ENCRYPTION_SALT=' + base64.urlsafe_b64encode(os.urandom(32)).decode())"
python -c "import secrets; print('CSRF_SECRET_KEY=' + secrets.token_urlsafe(32))"
```

### 2. Удалить .env из git истории

```bash
# BFG Repo-Cleaner
bfg --delete-files .env
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force-with-lease origin main
```

---

## Render (облако)

### Backend

1. **Создайте Web Service**:
   - Подключите GitHub репозиторий
   - Branch: `main`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --worker-class uvicorn.workers.UvicornWorker --workers 1 --bind 0.0.0.0:$PORT backend.main:app`

2. **Environment Variables**:
   ```
   SUPABASE_URL=https://ваш-проект.supabase.co
   SUPABASE_KEY=sb_publishable_...
   SUPABASE_SERVICE_KEY=sb_secret_...
   ENCRYPTION_KEY=<сгенерированный>
   ENCRYPTION_SALT=<сгенерированный>
   CSRF_SECRET_KEY=<сгенерированный>
   FRONTEND_URL=https://ваш-frontend.onrender.com
   DATABASE_URL=postgresql://...
   REDIS_URL=rediss://...
   ```

### Frontend

1. **Создайте Static Site**:
   - Build Command: `cd frontend && npm install && npm run build`
   - Publish Directory: `frontend/dist`

2. **Environment Variable**:
   ```
   VITE_API_URL=https://ваш-backend.onrender.com
   ```

---

## Docker

### Сборка

```bash
# Backend
docker build -t padplus-backend .

# Frontend
cd frontend && docker build -t padplus-frontend .
```

### Запуск

```bash
docker run -d --name padplus-backend -p 8080:8080 --env-file .env padplus-backend
```

---

## Локальный production

### Backend

```bash
cd backend
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8080
```

### Frontend

```bash
cd frontend
npm run build
# Раздавайте через nginx
```

---

## Переменные окружения

| Переменная | Описание | Обязательно |
|-----------|----------|:-----------:|
| `SUPABASE_URL` | URL проекта Supabase | ✅ |
| `SUPABASE_KEY` | Публичный ключ | ✅ |
| `SUPABASE_SERVICE_KEY` | Сервисный ключ | ✅ |
| `ENCRYPTION_KEY` | Ключ шифрования | ✅ |
| `ENCRYPTION_SALT` | Соль для шифрования | ✅ |
| `CSRF_SECRET_KEY` | CSRF секрет | ✅ |
| `FRONTEND_URL` | URL фронтенда (CORS) | ✅ |
| `DATABASE_URL` | PostgreSQL URL | ✅ |
| `REDIS_URL` | Redis URL | ❌ |
| `BACKEND_PORT` | Порт backend | ❌ (8080) |

---

## Проверка работоспособности

### Health check

```bash
curl https://your-app.onrender.com/health
```

Ожидаемый ответ:
```json
{
  "status": "healthy",
  "anti_directive": true,
  "database": true,
  "cache": true,
  "timestamp": "2026-06-10T..."
}
```

### Swagger UI

Откройте `https://your-app.onrender.com/docs`

---

## ✅ Чеклист production

- [ ] .env удален из git истории
- [ ] Все ключи ротированы
- [ ] Environment Variables установлены на Render
- [ ] FRONTEND_URL точный (без wildcards)
- [ ] HTTPS работает
- [ ] Health check возвращает "healthy"
- [ ] Логи не содержат критических ошибок
- [ ] Rate limiting работает
- [ ] CORS настроен правильно

---

## 🐛 Частые проблемы

### Build Timeout
Уменьшите количество npm зависимостей, используйте `npm ci`

### Out of Memory
Render free tier: 512MB RAM. Используйте 1 worker.

### Database Connection
Проверьте DATABASE_URL format и Supabase проект active.

### CORS Error
FRONTEND_URL должен точно совпадать (https://, без wildcards).
