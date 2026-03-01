# 🌍 Environment Variables для Render

## 📋 Список переменных для копирования

Скопируйте этот блок и вставьте в Render Dashboard в раздел "Environment Variables":

```
# База данных Supabase
DATABASE_URL=postgresql://postgres:TiMuPom13Q5OfKBi@db.hgjbjccpeirwrabbcjhr.supabase.co:5432/postgres

# LLM провайдер (обязательно заменить на свой ключ!)
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

## 🔑 Как получить OPENROUTER_API_KEY

1. Перейдите на https://openrouter.ai
2. Зарегистрируйтесь или войдите в аккаунт
3. Перейдите в раздел "API Keys" (https://openrouter.ai/keys)
4. Нажмите "Create new key"
5. Скопируйте ключ и вставьте в переменную `OPENROUTER_API_KEY`

## ⚠️ Важные замечания

### OpenRouter API Key
- **Обязательная переменная** для работы LLM
- Ключ должен начинаться с `sk-`
- Без ключа чат не будет работать

### Supabase DATABASE_URL
- **Уже настроен** с правильным паролем
- URL: `postgresql://postgres:TiMuPom13Q5OfKBi@db.hgjbjccpeirwrabbcjhr.supabase.co:5432/postgres`
- Пароль: `TiMuPom13Q5OfKBi`

### VITE_API_URL
- Автоматически подставится после деплоя
- Формат: `https://padplus-ai-backend.onrender.com`
- Можно оставить как есть, Render подставит правильный URL

## 📝 Формат ввода в Render

В Render Dashboard:
1. Перейдите в настройки Blueprint
2. Раздел "Environment Variables"
3. Добавьте переменные по одной:
   - Key: `DATABASE_URL`
   - Value: `postgresql://postgres:TiMuPom13Q5OfKBi@db.hgjbjccpeirwrabbcjhr.supabase.co:5432/postgres`
   - Sync: `false` (для секретных переменных)

4. Для `OPENROUTER_API_KEY` установите `Sync: false`

## 🔒 Безопасность

- **Никогда не публикуйте** `OPENROUTER_API_KEY` в открытых репозиториях
- Используйте `Sync: false` для секретных переменных
- Регулярно обновляйте API ключи

## 🧪 Проверка переменных

После деплоя проверьте:
1. Backend запускается без ошибок
2. Подключение к Supabase работает
3. LLM ответы приходят
4. Health check `/health` возвращает `healthy`

## 📞 Если что-то не работает

1. Проверьте логи в Render Dashboard
2. Убедитесь что все переменные настроены
3. Проверьте формат `OPENROUTER_API_KEY`
4. Убедитесь что `DATABASE_URL` содержит правильный пароль