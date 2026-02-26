# Frontend Компоненты

Этот документ описывает frontend компоненты PAD+ AI.

## Обзор

Frontend реализован на React с использованием TypeScript и Vite. Интерфейс включает:

- Чат с эмоциональной аналитикой
- Аналитику использования
- Управление провайдерами LLM
- WebSocket соединение для реального времени
- Модальное окно настроек

## Структура проекта

```
frontend/
├── src/
│   ├── App.jsx              # Главный компонент приложения
│   ├── App.css              # Стили приложения
│   ├── Settings.jsx         # Компонент настроек провайдеров
│   ├── Settings.css         # Стили настроек
│   └── components/          # Дополнительные компоненты
├── public/                  # Статические файлы
└── package.json            # Зависимости и скрипты
```

## Главный компонент (App.jsx)

### Функции

- Управление состоянием приложения
- WebSocket соединение
- API запросы к backend
- Отображение различных вкладок
- Обработка чата и RAG контекста

### Состояния

```javascript
const [activeTab, setActiveTab] = useState('chat')
const [prompt, setPrompt] = useState('')
const [messages, setMessages] = useState([])
const [emotion, setEmotion] = useState(null)
const [knowledgeGraph, setKnowledgeGraph] = useState(null)
const [autonomy, setAutonomy] = useState(null)
const [wsConnected, setWsConnected] = useState(false)
const [showSettings, setShowSettings] = useState(false)
```

### WebSocket соединение

```javascript
const connectWebSocket = useCallback(() => {
  const ws = new WebSocket(WS_URL)
  
  ws.onopen = () => {
    setWsConnected(true)
    ws.send(JSON.stringify({
      type: 'subscribe',
      channels: ['emotion', 'memory', 'autonomy', 'all']
    }))
  }
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    handleWsMessage(data)
  }
  
  // ... обработка закрытия и ошибок
}, [])
```

### API запросы

```javascript
const sendChat = async () => {
  const response = await fetch(`${API_URL}/api/v1/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt })
  })
  
  const data = await response.json()
  // Обработка ответа
}
```

## Компонент настроек (Settings.jsx)

### Функции

- Отображение списка провайдеров
- Проверка статуса конфигурации
- Переключение активного провайдера
- Визуальная индикация состояния

### Состояния

```javascript
const [providers, setProviders] = useState([])
const [activeProvider, setActiveProvider] = useState(null)
const [loading, setLoading] = useState(false)
const [error, setError] = useState(null)
```

### API методы

```javascript
const fetchProviders = async () => {
  const response = await fetch(`${API_URL}/api/v1/providers`)
  const data = await response.json()
  setProviders(data.providers)
}

const switchProvider = async (providerName) => {
  const response = await fetch(`${API_URL}/api/v1/providers/switch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider_name: providerName })
  })
  
  const data = await response.json()
  setActiveProvider(data.provider)
}
```

## Стили (App.css)

### Цветовая схема

- **Основной фон**: Градиент от темно-синего к черному
- **Акценты**: Голубой (#00d9ff) и зеленый (#00ff88)
- **Текст**: Светлый (#e0e0e0) и серый (#888)
- **Фон элементов**: Прозрачный с эффектом стекла

### Компоненты стилей

```css
/* Градиентный текст */
.header h1 {
  background: linear-gradient(90deg, #00d9ff, #00ff88);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* Эффект стекла */
.sidebar, .messages {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

/* Активные элементы */
.tabs button.active {
  background: linear-gradient(135deg, #00d9ff, #00ff88);
  color: #1a1a2e;
}
```

### Анимации

```css
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message {
  animation: fadeIn 0.3s ease;
}
```

## WebSocket интеграция

### Подписка на события

```javascript
useEffect(() => {
  connectWebSocket()
  
  return () => {
    if (wsRef.current) {
      wsRef.current.close()
    }
  }
}, [connectWebSocket])
```

### Обработка сообщений

```javascript
const handleWsMessage = (data) => {
  switch (data.type) {
    case 'emotion_update':
      setEmotion(data.state)
      break
    case 'chat_response':
      setMessages(prev => [...prev, {
        role: 'ai',
        text: data.response,
        provider: data.provider
      }])
      break
    // ... другие события
  }
}
```

## RAG интеграция

### Поиск контекста

```javascript
const searchRag = async (query) => {
  const response = await fetch(`${API_URL}/api/v1/rag/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, n_results: 3 })
  })
  
  const data = await response.json()
  return data.results
}
```

### Отображение контекста

```jsx
{ragContext && ragContext.length > 0 && (
  <div className="rag-context">
    <div className="rag-header">
      <span>📚 Найдено в памяти</span>
      <button onClick={() => setRagContext(null)}>×</button>
    </div>
    <div className="rag-items">
      {ragContext.map((item, i) => (
        <div key={i} className="rag-item">
          <span className="rag-similarity">
            {(item.similarity * 100).toFixed(0)}% схожесть
          </span>
          <div className="rag-text">
            <strong>Вопрос:</strong> {item.metadata?.user_message}
          </div>
          <div className="rag-text">
            <strong>Ответ:</strong> {item.metadata?.ai_response}
          </div>
        </div>
      ))}
    </div>
  </div>
)}
```

## Безопасность

### CORS

```javascript
// Backend CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Защита API ключей

- API ключи хранятся только на сервере
- Клиент получает только статус конфигурации
- WebSocket соединение защищено CORS

## Производительность

### Оптимизации

- Использование `useCallback` для функций
- Memoization для тяжелых вычислений
- Пагинация и лимитирование запросов
- Кэширование статистики

### WebSocket оптимизации

- Подписка только на необходимые каналы
- Ограничение частоты обновлений
- Автоматическое переподключение

## Развертывание

### Локальная разработка

```bash
cd frontend
npm install
npm run dev
```

### Production сборка

```bash
npm run build
npm run preview
```

### Environment переменные

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

## Тестирование

### Рекомендации

- Тестирование WebSocket соединения
- Проверка API интеграции
- Тестирование RAG функциональности
- Проверка производительности

## Future улучшения

- TypeScript типизация
- Unit тесты с Jest
- E2E тесты с Cypress
- PWA поддержка
- Темная/светлая тема
- Адаптивный дизайн для мобильных