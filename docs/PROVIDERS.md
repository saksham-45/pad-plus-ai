# Управление провайдерами LLM

Этот документ описывает систему управления провайдерами LLM в PAD+ AI.

## Обзор

PAD+ AI поддерживает несколько провайдеров языковых моделей:

- **GigaChat** (по умолчанию)
- **OpenRouter**
- **OpenAI**
- **Anthropic**
- **Google Gemini**

## Конфигурация провайдеров

### .env.example

```env
# GigaChat
GIGACHAT_CREDENTIALS=your_credentials_here
GIGACHAT_SCOPE=GIGACHAT_API_PERS

# OpenRouter
OPENROUTER_API_KEY=your_openrouter_api_key

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key

# Google Gemini
GOOGLE_GEMINI_API_KEY=your_gemini_api_key
```

### Добавление нового провайдера

1. Создайте класс провайдера в `backend/llm/providers/`
2. Реализуйте интерфейс `BaseProvider`
3. Добавьте провайдер в `provider_manager.py`
4. Обновите `.env.example`

## API Endpoints

### Получение списка провайдеров

```http
GET /api/v1/providers
```

**Ответ:**
```json
{
  "providers": [
    {
      "name": "gigachat",
      "display_name": "GigaChat",
      "is_active": true,
      "is_configured": true,
      "model": "GigaChat",
      "priority": 1
    }
  ]
}
```

### Получение активного провайдера

```http
GET /api/v1/providers/active
```

**Ответ:**
```json
{
  "name": "gigachat",
  "display_name": "GigaChat",
  "model": "GigaChat",
  "priority": 1
}
```

### Переключение провайдера

```http
POST /api/v1/providers/switch
Content-Type: application/json

{
  "provider_name": "openrouter"
}
```

**Ответ:**
```json
{
  "message": "Provider switched to openrouter",
  "provider": {
    "name": "openrouter",
    "display_name": "OpenRouter",
    "model": "openrouter/auto",
    "priority": 2
  }
}
```

### Проверка конфигурации провайдера

```http
POST /api/v1/providers/check
Content-Type: application/json

{
  "provider_name": "openrouter"
}
```

**Ответ:**
```json
{
  "provider_name": "openrouter",
  "is_configured": true,
  "can_connect": true,
  "model": "openrouter/auto"
}
```

## WebSocket события

### События провайдеров

```javascript
// Подписка на события
ws.send(JSON.stringify({
  type: 'subscribe',
  channels: ['provider']
}))

// Получение событий
{
  "type": "provider_event",
  "event": "provider_switched",
  "data": {
    "old_provider": "gigachat",
    "new_provider": "openrouter",
    "timestamp": "2024-02-25T10:30:00Z"
  }
}
```

## Компонент настроек

### Функции

- Просмотр списка доступных провайдеров
- Проверка статуса конфигурации
- Переключение активного провайдера
- Отображение информации о моделях

### Использование

```javascript
import Settings from './Settings';

// В компоненте App
<Settings onClose={() => setShowSettings(false)} />
```

### Стили

Компонент использует модальное окно с затемненным фоном и анимацией появления.

## Безопасность

- API ключи не передаются клиенту
- Проверка конфигурации происходит на сервере
- WebSocket соединение защищено CORS

## Ошибки

### Коды ошибок

- `400`: Неверный запрос
- `404`: Провайдер не найден
- `500`: Ошибка сервера
- `503`: Провайдер не настроен

### Обработка ошибок

```javascript
try {
  const response = await fetch('/api/v1/providers/switch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider_name: 'openrouter' })
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  
  const data = await response.json();
  console.log('Provider switched:', data);
} catch (error) {
  console.error('Failed to switch provider:', error);
}