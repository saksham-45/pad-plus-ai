# WebSocket API

Этот документ описывает WebSocket API для PAD+ AI.

## Обзор

WebSocket соединение позволяет получать реальное время обновления состояния системы, включая:

- Эмоциональное состояние
- События памяти
- Автономные процессы
- События провайдеров

## Подключение

### URL

```
ws://localhost:8080/ws
wss://your-domain.com/ws  // для production
```

### Подписка на каналы

```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onopen = () => {
  // Подписка на каналы
  ws.send(JSON.stringify({
    type: 'subscribe',
    channels: ['emotion', 'memory', 'autonomy', 'provider', 'all']
  }));
};
```

### Доступные каналы

- `emotion` - Эмоциональные обновления
- `memory` - События памяти (RAG, Facts, Knowledge)
- `autonomy` - Автономные процессы
- `provider` - События провайдеров
- `all` - Все события

## События

### Эмоциональные события

```json
{
  "type": "emotion_update",
  "state": {
    "удовольствие": 0.5,
    "возбуждение": 0.3,
    "доминирование": 0.1,
    "любопытство": 0.8,
    "уверенность": 0.9,
    "социальная_связь": 0.2,
    "style": {
      "tone": "neutral",
      "verbosity": "medium",
      "color": "blue"
    }
  },
  "timestamp": "2024-02-25T10:30:00Z"
}
```

### События памяти

```json
{
  "type": "memory_update",
  "memory_type": "rag",
  "data": {
    "total_dialogs": 150,
    "unique_keys": 89,
    "encoder": "OpenAI text-embedding-ada-002"
  },
  "timestamp": "2024-02-25T10:30:00Z"
}
```

### События автономии

```json
{
  "type": "autonomy_event",
  "event": "planner_update",
  "data": {
    "pending_tasks": 5,
    "completed_tasks": 12,
    "running": true
  },
  "timestamp": "2024-02-25T10:30:00Z"
}
```

### События провайдеров

```json
{
  "type": "provider_event",
  "event": "provider_switched",
  "data": {
    "old_provider": "gigachat",
    "new_provider": "openrouter",
    "model": "openrouter/auto"
  },
  "timestamp": "2024-02-25T10:30:00Z"
}
```

### Ответы чата

```json
{
  "type": "chat_response",
  "response": "Привет! Как я могу помочь вам сегодня?",
  "provider": "gigachat",
  "confidence": 0.95,
  "timestamp": "2024-02-25T10:30:00Z"
}
```

### События Mind State

```json
{
  "type": "mind_state",
  "state": {
    "emotion": { /* emotion data */ },
    "memory": { /* memory data */ },
    "autonomy": { /* autonomy data */ },
    "truth": { /* truth data */ },
    "safety": { /* safety data */ },
    "events": { /* events data */ }
  },
  "timestamp": "2024-02-25T10:30:00Z"
}
```

## Команды

### Ping

```javascript
ws.send(JSON.stringify({
  type: 'ping'
}));
```

**Ответ:**
```json
{
  "type": "pong",
  "timestamp": "2024-02-25T10:30:00Z"
}
```

### Подписка

```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  channels: ['emotion', 'memory']
}));
```

**Ответ:**
```json
{
  "type": "subscribed",
  "channels": ["emotion", "memory"],
  "timestamp": "2024-02-25T10:30:00Z"
}
```

### Отписка

```javascript
ws.send(JSON.stringify({
  type: 'unsubscribe',
  channels: ['emotion']
}));
```

**Ответ:**
```json
{
  "type": "unsubscribed",
  "channels": ["emotion"],
  "timestamp": "2024-02-25T10:30:00Z"
}
```

## Обработка ошибок

### Ошибки соединения

```javascript
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = (event) => {
  console.log('WebSocket closed:', event.code, event.reason);
  
  // Автоматическое переподключение
  setTimeout(() => {
    connectWebSocket();
  }, 5000);
};
```

### Ошибки сервера

```json
{
  "type": "error",
  "error": "Invalid channel",
  "code": 400,
  "timestamp": "2024-02-25T10:30:00Z"
}
```

## Пример использования

```javascript
class WebSocketClient {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.reconnectTimeout = 5000;
    this.channels = ['emotion', 'memory', 'autonomy'];
  }

  connect() {
    this.ws = new WebSocket(this.url);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.subscribe(this.channels);
    };
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket disconnected, reconnecting...');
      setTimeout(() => this.connect(), this.reconnectTimeout);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  subscribe(channels) {
    this.ws.send(JSON.stringify({
      type: 'subscribe',
      channels: channels
    }));
  }

  handleMessage(data) {
    switch (data.type) {
      case 'emotion_update':
        this.handleEmotionUpdate(data.state);
        break;
      case 'memory_update':
        this.handleMemoryUpdate(data);
        break;
      case 'autonomy_event':
        this.handleAutonomyEvent(data);
        break;
      case 'provider_event':
        this.handleProviderEvent(data);
        break;
      case 'chat_response':
        this.handleChatResponse(data);
        break;
      case 'mind_state':
        this.handleMindState(data.state);
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  }

  handleEmotionUpdate(state) {
    // Обновление UI эмоционального состояния
    console.log('Emotion update:', state);
  }

  handleMemoryUpdate(data) {
    // Обновление статистики памяти
    console.log('Memory update:', data);
  }

  handleAutonomyEvent(data) {
    // Обновление статуса автономии
    console.log('Autonomy event:', data);
  }

  handleProviderEvent(data) {
    // Обновление информации о провайдере
    console.log('Provider event:', data);
  }

  handleChatResponse(data) {
    // Добавление ответа в чат
    console.log('Chat response:', data);
  }

  handleMindState(state) {
    // Обновление общего состояния системы
    console.log('Mind state update:', state);
  }
}

// Использование
const client = new WebSocketClient('ws://localhost:8080/ws');
client.connect();
```

## Безопасность

- WebSocket соединение использует CORS
- Все сообщения проверяются на валидность
- Поддерживается только текстовый формат JSON
- Автоматическое переподключение при обрыве соединения

## Производительность

- Рекомендуется подписываться только на необходимые каналы
- Используйте `all` только для отладки
- Обрабатывайте сообщения асинхронно
- Ограничьте частоту обновлений на клиенте при необходимости