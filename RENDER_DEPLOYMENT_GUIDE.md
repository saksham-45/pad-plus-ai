# 🚀 Инструкция по развертыванию PAD+ AI на Render

## 📋 Обзор

PAD+ AI v3.5 - это когнитивный слой с эмоциями и самосознанием, готовый к развертыванию на Render с использованием Supabase PostgreSQL.

## 🎯 Что будет развернуто

- **Backend**: FastAPI сервер на Python 3.11
- **Frontend**: React приложение на TypeScript
- **База данных**: PostgreSQL через Supabase
- **WebSocket**: Real-time обновления
- **Health checks**: Мониторинг состояния

## 📦 Требования

- [x] GitHub репозиторий: `https://github.com/Ovladimirovich/PAD-AI-v3.5`
- [x] Supabase проект: `padplus-ai-db`
- [x] Render аккаунт

## 🚀 Пошаговая инструкция

### Шаг 1: Подготовка GitHub репозитория

Репозиторий уже создан и содержит:
- ✅ Render конфигурацию в `render.yaml`
- ✅ Backend на FastAPI
- ✅ Frontend на React
- ✅ Тесты и документация

### Шаг 2: Настройка Render

1. **Зайти в Render Dashboard**
   - Перейдите на https://dashboard.render.com
   - Авторизуйтесь через GitHub

2. **Создать Blueprint**
   - Нажмите "New" → "Blueprint"
   - Выберите репозиторий `Ovladimirovich/PAD-AI-v3.5`

3. **Настроить Environment Variables**

   В разделе "Environment Variables" добавьте:

   ```
   # База данных Supabase
   DATABASE_URL=postgresql://postgres:TiMuPom13Q5OfKBi@db.hgjbjccpeirwrabbcjhr.supabase.co:5432/postgres
   
   # LLM провайдер
   OPENROUTER_API_KEY=ваш_ключ_от_OpenRouter
   OPENROUTER_ENABLED=true
   OPENROUTER_MODEL=google/gemma-7b-it
   
   # Режим работы
   DEBUG=false
   RENDER=true
   LOG_LEVEL=info
   
   # Frontend
   VITE_API_URL=https://padplus-ai-backend.onrender.com
   ```

   **Важно**: Замените `ваш_ключ_от_OpenRouter` на реальный API ключ от OpenRouter.

### Шаг 3: Настройка сервисов

#### Backend Service
- **Name**: `padplus-ai-backend`
- **Type**: Web Service
- **Runtime**: Python
- **Region**: Frankfurt
- **Plan**: Free
- **Build Command**: `python -m pip install --upgrade pip && pip install -r requirements.txt`
- **Start Command**: `cd backend && python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/health`

#### Frontend Service
- **Name**: `padplus-ai-frontend`
- **Type**: Static Site
- **Plan**: Free
- **Build Command**: `cd frontend && npm install && npm run build`

### Шаг 4: Запуск деплоя

1. Нажмите "Create Blueprint"
2. Дождитесь завершения сборки (~5-10 минут)
3. Render автоматически создаст два сервиса

## 🔍 Проверка после деплоя

### Backend проверка
Откройте: `https://padplus-ai-backend.onrender.com/health`

Ожидаемый ответ:
```json
{
  "status": "healthy",
  "anti_directive": true,
  "timestamp": "2026-03-01T08:25:00"
}
```

### Frontend проверка
Откройте: `https://padplus-ai-frontend.onrender.com`

Должен загрузиться React интерфейс с чатом.

### Тестирование функциональности

1. Отправьте сообщение в чат
2. Проверьте что ответ приходит
3. Убедитесь что RAG работает (появляется метка 📚 RAG)
4. Проверьте WebSocket соединение (иконка 📵 должна стать 📡)

## 📊 Ожидаемые URL

После успешного деплоя:
- **Backend**: `https://padplus-ai-backend.onrender.com`
- **Frontend**: `https://padplus-ai-frontend.onrender.com`
- **API Docs**: `https://padplus-ai-backend.onrender.com/docs`
- **WebSocket**: `wss://padplus-ai-backend.onrender.com/ws`

## ⚠️ Важные моменты

### OpenRouter API Key
Для работы LLM нужно получить API ключ:
1. Зарегистрируйтесь на https://openrouter.ai
2. Получите API ключ в настройках
3. Добавьте в Environment Variables

### Supabase доступ
База данных уже настроена:
- **URL**: `postgresql://postgres:TiMuPom13Q5OfKBi@db.hgjbjccpeirwrabbcjhr.supabase.co:5432/postgres`
- **Пароль**: `TiMuPom13Q5OfKBi`

### Render ограничения (Free план)
- **Backend**: 750 часов/месяц
- **Frontend**: Неограниченно
- **Disk**: 1GB для данных
- **Sleep**: После 15 минут неактивности
- **Cold start**: ~30 секунд

## 🔧 Troubleshooting

### Проблемы с подключением к БД
Проверьте:
1. Правильность DATABASE_URL
2. Доступность Supabase
3. Пароль `TiMuPom13Q5OfKBi`

### Проблемы с LLM
Проверьте:
1. OPENROUTER_API_KEY
2. OPENROUTER_ENABLED=true
3. Доступ к OpenRouter

### Health check не проходит
Проверьте:
1. Backend запущен
2. Endpoint `/health` доступен
3. Нет ошибок в логах

## 🎉 Готово!

После выполнения этих шагов ваш PAD+ AI будет доступен онлайн с полной функциональностью:

- 🧠 Когнитивный слой с эмоциями
- 📚 RAG память на PostgreSQL
- 🔄 Автономные процессы
- 📊 Аналитика и мониторинг
- 🛡️ Безопасность и ANTI_DIRECTIVE

## 📞 Поддержка

Если возникнут вопросы:
1. Проверьте логи в Render Dashboard
2. Убедитесь что все Environment Variables настроены
3. Проверьте подключение к Supabase
4. Обратитесь за помощью в issues репозитория

---

**Время развертывания**: ~15 минут
**Готовность**: 100%
**Статус**: Production-ready ✅