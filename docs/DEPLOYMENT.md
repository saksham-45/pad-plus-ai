# 🚀 Развёртывание PAD+ AI

## Render (облако)

### Подготовка

1. Создайте аккаунт на https://render.com
2. Создайте проект на https://supabase.com (если ещё нет)

### Развёртывание backend

1. Подключите репозиторий к Render
2. Создайте **Web Service**:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`

3. Добавьте **Environment Variables**:
   ```
   SUPABASE_URL=https://ваш-проект.supabase.co
   SUPABASE_KEY=sb_publishable_...
   SUPABASE_SERVICE_KEY=sb_secret_...
   ENCRYPTION_KEY=<ваш ключ>
   ENCRYPTION_SALT=<ваша соль>
   FRONTEND_URL=https://ваш-frontend.onrender.com
   ```

### Развёртывание frontend

1. Создайте **Static Site**:
   - **Build Command:** `cd frontend && npm install && npm run build`
   - **Publish Directory:** `frontend/dist`

2. Добавьте **Environment Variable**:
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
cd frontend
docker build -t padplus-frontend .
cd ..
```

### Запуск

```bash
docker run -d \
  --name padplus-backend \
  -p 8080:8080 \
  --env-file .env \
  padplus-backend

cd frontend
docker run -d \
  --name padplus-frontend \
  -p 80:80 \
  -e VITE_API_URL=http://localhost:8080 \
  padplus-frontend
```

---

## Локальный сервер (production)

### Backend

```bash
cd backend
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8080
```

### Frontend

```bash
cd frontend
npm run build
# Раздавайте через nginx или другой веб-сервер
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
| `FRONTEND_URL` | URL фронтенда (CORS) | ✅ |
| `BACKEND_PORT` | Порт backend | ❌ (по умолч. 8080) |
| `GIGACHAT_AUTH_KEY` | Ключ GigaChat | ❌ |
| `DEBUG` | Режим отладки | ❌ (по умолч. false) |

---

## Проверка работоспособности

### Health check

```bash
curl http://localhost:8080/health
```

Ожидаемый ответ:
```json
{
  "status": "healthy",
  "anti_directive": true,
  "timestamp": "2026-04-07T..."
}
```

### Swagger UI

Откройте `http://localhost:8080/docs` для просмотра всех эндпоинтов.
