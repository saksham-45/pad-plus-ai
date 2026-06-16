# 🖥️ Frontend — PAD+ AI v4.0

## Обзор

Frontend реализован на **React + Vite** (JavaScript, без TypeScript). Использует Tailwind CSS для стилизации.

**Порт:** `http://localhost:5174`

## Структура проекта

```
frontend/
├── src/
│   ├── App.jsx                    # Главный компонент (роутинг, auth, модель)
│   ├── main.jsx                   # Entry point
│   ├── index.css                  # Глобальные стили + Tailwind
│   │
│   ├── components/                # UI компоненты
│   │   ├── Auth.jsx               # Регистрация / Вход (Supabase Auth)
│   │   ├── ChatInterface.jsx      # Чат с SSE streaming
│   │   ├── Dashboard.jsx          # Главная страница с виджетами
│   │   ├── ModelSelector.jsx      # Выбор модели (dropdown)
│   │   ├── ApiKeyForm.jsx         # Форма добавления API ключа
│   │   ├── ProviderManagement.jsx # Управление провайдерами
│   │   ├── ProviderSelector.jsx   # Выбор провайдера
│   │   ├── ProviderTester.jsx     # Тест подключения провайдера
│   │   ├── LeftSidebar.jsx        # Левая боковая панель (навигация)
│   │   ├── RightSidebar.jsx       # Правая панель (метрики, PAD, виджеты)
│   │   ├── KpiCard.jsx            # KPI карточка
│   │   │
│   │   ├── ui/                    # Базовые UI компоненты
│   │   │   ├── Button.jsx
│   │   │   ├── Card.jsx
│   │   │   └── index.js
│   │   │
│   │   └── widgets/               # Виджеты дашборда
│   │       ├── FlowWidget.jsx         # Pipeline визуализация
│   │       ├── PadWidget.jsx          # Эмоции PAD+
│   │       ├── HealthWidget.jsx       # Здоровье системы
│   │       ├── MemoryWidget.jsx       # Память
│   │       ├── KnowledgeWidget.jsx    # Граф знаний
│   │       ├── MetricsWidget.jsx      # Метрики
│   │       ├── LogsWidget.jsx         # Логи
│   │       └── SystemResourcesWidget.jsx # Ресурсы системы
│   │
│   ├── pages/                     # Страницы
│   │   ├── ProvidersPage.jsx          # Каталог провайдеров (20+)
│   │   ├── ConnectedProvidersPage.jsx # Подключенные провайдеры
│   │   └── InstructionsPage.jsx       # Инструкции
│   │
│   ├── hooks/
│   │   └── useWebSocket.js        # WebSocket хук
│   │
│   └── services/
│       └── modelCache.js          # Кэширование моделей
│
├── package.json
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

## Архитектура

### Аутентификация

Используется **Supabase Auth** через backend эндпоинты:

```
POST /api/v1/auth/register  → Регистрация
POST /api/v1/auth/login     → Вход
GET  /api/v1/auth/me        → Текущий пользователь
```

Токен хранится в `localStorage` и передаётся в заголовке `Authorization: Bearer <token>`.

### Управление моделями

1. **App.jsx** хранит `selectedModel` в state + `localStorage`
2. При загрузке автоматически выбирается модель с `is_default=true`
3. Модель передаётся в `ChatInterface` как prop
4. При смене модели отправляется событие `model-changed`

### Чат

**Компонент:** `ChatInterface.jsx`

**Поток:**
```
User вводит сообщение
    ↓
POST /api/v1/chat/stream (SSE)
    ↓
Чтение потока через ReadableStream
    ↓
Отображение в реальном времени
```

**Запрос:**
```json
{
  "message": "Привет!",
  "key_id": "uuid-ключа",
  "model": "gigachat/GigaChat",
  "provider": "gigachat",
  "stream": true
}
```

### Управление провайдерами

**Страницы:**
- **ProvidersPage** — каталог всех 20+ провайдеров, подключение новых
- **ConnectedProvidersPage** — список подключенных, смена модели, удаление

**Поток подключения:**
```
Выбор провайдера → Ввод API ключа → POST /api/v1/keys → Сохранение в БД (зашифровано)
```

### WebSocket

**Хук:** `useWebSocket.js`

Подключается к `ws://localhost:8080/ws` для получения событий в реальном времени.

## Стили

### Tailwind CSS

Используется кастомная тема с тёмной цветовой схемой:

```js
// tailwind.config.js
colors: {
  background: '#0B0F14',
  card: '#111827',
  border: '#1F2937',
  primary: '#6366F1',
  text: {
    primary: '#FFFFFF',
    secondary: '#9CA3AF',
    muted: '#6B7280'
  }
}
```

### Компоненты UI

- **Button.jsx** — варианты: `default`, `outline`, размеры: `sm`, `default`
- **Card.jsx** — `Card`, `CardHeader`, `CardTitle`, `CardContent`

## Запуск

### Development

```bash
cd frontend
npm install
npm run dev
```

Откройте http://localhost:5174

### Production сборка

```bash
npm run build
# Результат в frontend/dist/
```

## Переменные окружения

Vite проксирует API запросы на backend автоматически. Настройка в `vite.config.js`:

```js
server: {
  proxy: {
    '/api': 'http://127.0.0.1:8080',
    '/ws': { target: 'ws://127.0.0.1:8080', ws: true }
  }
}
```

## Зависимости

| Пакет | Версия | Назначение |
|-------|--------|------------|
| react | 18.x | UI фреймворк |
| vite | 5.4.x | Сборщик |
| tailwindcss | 3.x | Стили |
| postcss | 8.x | Обработка CSS |
