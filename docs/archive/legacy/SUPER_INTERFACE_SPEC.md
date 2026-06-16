# 🎨 PAD+ AI — СПЕЦИФИКАЦИЯ ИНТЕРФЕЙСА ДЛЯ FIGMA & VIBE CODING

## 📋 **ОБЩАЯ ИНФОРМАЦИЯ**

**Проект:** PAD+ AI v4.0 — Когнитивный слой для AI систем  
**Цель:** Создать супер-интерфейс с полной визуализацией всех систем  
**Стек:** React + Tailwind CSS + Recharts + Framer Motion  
**API:** FastAPI + Supabase Auth + LiteLLM

---

## 🏗️ **АРХИТЕКТУРА СИСТЕМЫ**

### **1. Ядро системы (Core)**
- **Pipeline** — обработка запросов (5 этапов: Input → PAD → RAG → LLM → Output)
- **TruthLoop** — проверка фактов, верификация
- **Safety Layer** — безопасность, блокировки угроз
- **Health Monitor** — мониторинг здоровья системы
- **Event Bus** — шина событий
- **Rate Limiter** — ограничение запросов
- **Cache Manager** — кэширование
- **Session Manager** — управление сессиями

### **2. Память (Memory Systems)**
- **RAG Memory** — векторный поиск документов
- **Episodic Memory** — диалоги, временные метки
- **Semantic Memory** — общие знания, концепции
- **Fact Memory** — структурированные факты
- **Persona** — личность, черты характера
- **User Persona** — профиль пользователя
- **SmartCache** — умный кэш
- **Vector Memory** — векторные представления

### **3. Эмоции (Emotion System)**
- **PAD Model** — 6 измерений:
  - Pleasure (удовольствие)
  - Arousal (возбуждение)
  - Dominance (доминирование)
  - Curiosity (любознательность)
  - Confidence (уверенность)
  - Social Connection (социальная связь)

### **4. Знания (Knowledge System)**
- **Knowledge Graph** — граф знаний (entities, relations)
- **Graph Visualization** — визуализация связей

### **5. Инфраструктура (Infrastructure)**
- **WebSocket Manager** — WebSocket подключения
- **HTTP Client** — HTTP запросы
- **Monitoring** — история метрик
- **Feedback System** — обратная связь

---

## 🎯 **ФУНКЦИОНАЛЬНЫЕ ТРЕБОВАНИЯ**

### **A. ГЛАВНАЯ СТРАНИЦА (Dashboard)**

#### **A1. HEADER**
- **Название:** "PAD-AI Control Center"
- **Подзаголовок:** "Cognitive Layer for AI Systems"
- **Кнопки:**
  - "Chat" — переход в чат
  - "Launch" — запуск демо-обработки

#### **A2. KPI КАРТОЧКИ (4 шт)**
1. **System** — статус (Online/Offline)
2. **Memory** — активность (Active/Inactive)
3. **PAD State** — стабильность (Stable/Unstable)
4. **Model** — текущая model (GPT-4/Claude/Gemini)

#### **A3. PROCESSING FLOW (горизонтальный)**
- 5 этапов с иконками:
  - 📥 Input
  - 🧠 PAD Processing
  - 📚 Memory + RAG
  - 🤖 LLM
  - 📤 Output
- Анимация прохождения запроса

#### **A4. ВИДЖЕТЫ (8 шт)**

**1. System Resources Monitor**
- CPU Usage (%) — прогресс-бар с порогами
- Memory Usage (%) — прогресс-бар
- Disk I/O (MB/s) — прогресс-бар
- Network Latency (ms) — прогресс-бар
- Active Connections — счетчик
- Load Score — общий показатель
- Статус: HEALTHY / WARNING / CRITICAL

**2. Flow Widget (AI Pipeline)**
- Анимация этапов обработки
- Индикация текущего этапа
- Статус: idle / processing / success / error

**3. PAD Emotion Widget**
- 6 радиальных индикаторов (P, A, D, C, Conf, SC)
- Значения 0.0 - 1.0
- Цветовая индикация

**4. Health Monitor Widget**
- 8 метрик здоровья:
  - Reflection, Learning, Adaptation
  - Memory, Coherence, Quality
  - Safety, Emotional Balance
- Прогресс-бары с порогами
- Overall Score

**5. Memory Widget**
- RAG: документы, коллекции, запросы, точность
- Episodic: диалоги, записи
- Semantic: концепты, связи
- Facts: факты, верификация
- Persona: черты, согласованность

**6. Knowledge Widget**
- Entities count
- Relations count
- Graphs count
- Визуализация графа (опционально)

**7. Metrics Widget (Pipeline Performance)**
- Линейный график производительности
- Real-time обновление (каждые 2 сек)
- Значения 0.0 - 1.0
- Tooltip при наведении

**8. System Logs Widget**
- Список последних событий
- Цветовая индикация уровней (INFO/WARNING/ERROR/DEBUG)
- Автопрокрутка вниз
- Фильтрация по типам

#### **A5. STATUS BAR**
- WebSocket статус (● зеленый/красный)
- Backend статус (● зеленый/красный)
- Текущее время

---

### **B. СТРАНИЦА ПРОВАЙДЕРОВ (ProvidersPage)**

#### **B1. ДОСТУПНЫЕ ПРОВАЙДЕРЫ**
- Google AI Studio (Gemini)
- Groq (Llama, Mistral)
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- OpenRouter (мульти-модель)
- Ollama (локальные модели)

#### **B2. ФУНКЦИОНАЛ**
- Подключение провайдера
- Выбор модели
- Тестирование ключа
- Установка по умолчанию

---

### **C. СТРАНИЦА ПОДКЛЮЧЕННЫХ ПРОВАЙДЕРОВ (ConnectedProvidersPage)**

#### **C1. СПИСОК ПОДКЛЮЧЕННЫХ**
- Название провайдера
- Выбранная модель
- Статус (активен/не активен)
- Ключ зашифрован

#### **C2. ДЕЙСТВИЯ**
- Редактировать модель
- Изменить имя
- Удалить ключ
- Установить по умолчанию
- Протестировать

---

### **D. СТРАНИЦА ИНСТРУКЦИЙ (InstructionsPage)**

#### **D1. РАЗДЕЛЫ**
- Быстрый старт
- Настройка API ключей
- Использование чата
- Работа с провайдерами
- RAG и память
- Настройка Persona

---

### **E. ЧАТ (ChatInterface)**

#### **E1. ОСНОВНОЙ ФУНКЦИОНАЛ**
- Ввод сообщения
- Выбор модели
- Отправка запроса
- Потоковый ответ (SSE)
- История диалога

#### **E2. ДОПОЛНИТЕЛЬНО**
- Прикрепление файлов
- Голосовой ввод
- Экспорт диалога
- Очистка истории

---

### **F. БОКОВЫЕ ПАНЕЛИ**

#### **F1. ЛЕВАЯ ПАНЕЛЬ (LeftSidebar)**
- 📖 Инструкции
- ⚡ Провайдеры
- 📄 Документы
- Кнопка скрытия/показа

#### **F2. ПРАВАЯ ПАНЕЛЬ (RightSidebar)**
- KPI метрики (4 карточки)
- Виджеты:
  - PAD Emotion
  - Health Monitor
  - Memory Stats
  - Knowledge Graph
  - Metrics Chart
- Регулировка ширины
- Кнопка скрытия/показа

---

## 🎨 **ДИЗАЙН-СИСТЕМА**

### **ЦВЕТОВАЯ ПАЛИТРА**
```css
/* Фон */
--bg-primary: #0B0F14
--bg-secondary: #111827
--bg-tertiary: #1F2937
--bg-card: #111827

/* Границы */
--border-primary: #1F2937
--border-secondary: #374151

/* Текст */
--text-primary: #F5F5F5
--text-secondary: #9CA3AF
--text-muted: #6B7280

/* Акцент */
--primary: #6366F1
--primary-hover: #4F46E5

/* Статусы */
--success: #10B981 (зеленый)
--warning: #F59E0B (желтый)
--error: #EF4444 (красный)
--info: #3B82F6 (синий)
```

### **ТИПОГРАФИКА**
```css
/* Заголовки */
h1: text-2xl font-bold
h2: text-xl font-semibold
h3: text-lg font-medium

/* Текст */
body: text-sm text-gray-300
small: text-xs text-gray-400

/* Моноширинный */
code: font-mono text-xs
```

### **КОМПОНЕНТЫ**

#### **Карточка (Card)**
```css
bg-[#111827] border border-[#1F2937] rounded-lg
hover:border-[#374151] transition-colors
```

#### **Кнопка (Button)**
```css
/* Primary */
bg-[#6366F1] text-white rounded-lg px-4 py-2
hover:bg-[#4F46E5] transition-colors

/* Outline */
border border-[#1F2937] text-gray-300 rounded-lg
hover:border-[#374151] hover:text-white
```

#### **Прогресс-бар**
```css
h-2 bg-gray-800 rounded-full overflow-hidden
fill: bg-blue-500 (или другой цвет)
transition: width 0.5s ease-out
```

---

## 📊 **ДАННЫЕ И API**

### **ОСНОВНЫЕ ЭНДПОИНТЫ**

#### **Аутентификация**
- `POST /api/v1/auth/register` — регистрация
- `POST /api/v1/auth/login` — вход
- `GET /api/v1/auth/me` — текущий пользователь
- `POST /api/v1/auth/refresh` — обновление токена

#### **Ключи**
- `GET /api/v1/keys` — список ключей
- `POST /api/v1/keys` — добавить ключ
- `DELETE /api/v1/keys/{id}` — удалить ключ
- `PATCH /api/v1/keys/{id}` — обновить ключ
- `POST /api/v1/keys/{id}/set-default` — установить по умолчанию
- `POST /api/v1/keys/{id}/test` — тестировать ключ

#### **Провайдеры**
- `GET /api/v1/providers` — список провайдеров
- `GET /api/v1/providers/{id}/models` — модели провайдера
- `GET /api/v1/models` — все модели

#### **Чат**
- `POST /api/v1/chat` — обычный запрос
- `POST /api/v1/chat/stream` — потоковый запрос (SSE)

#### **Dashboard**
- `GET /api/v1/mind-state` — состояние системы
- `GET /api/v1/events/recent` — недавние события
- `GET /api/v1/metrics/activity` — метрики активности
- `GET /api/v1/metrics/system` — системные метрики
- `GET /api/v1/system/full-status` — полный статус всех систем

---

## 🔧 **ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ**

### **Производительность**
- Загрузка Dashboard < 2 сек
- Обновление виджетов каждые 3-5 сек
- Потоковый ответ чата < 1 сек на токен
- Кэширование статичных данных

### **Безопасность**
- HTTPS обязательно
- API ключи шифруются (AES-256)
- Rate limiting (10 запросов/мин)
- CORS настроен правильно

### **Адаптивность**
- Desktop: 1920x1080 (основной)
- Tablet: 1024x768
- Mobile: 375x667 (ограниченный функционал)

### **Доступность**
- ARIA метки для скринридеров
- Клавиатурная навигация
- Контрастность WCAG AA
- Фокус индикаторы

---

## 🚀 **ПРИОРИТЕТЫ РЕАЛИЗАЦИИ**

### **Фаза 1 (MVP)**
1. Dashboard с основными виджетами
2. Страница провайдеров
3. Чат с базовым функционалом
4. Аутентификация

### **Фаза 2 (Расширение)**
1. Страница подключенных провайдеров
2. Страница инструкций
3. Боковые панели
4. Настройки пользователя

### **Фаза 3 (Продвинутый)**
1. Все виджеты с реальными данными
2. Графики и аналитика
3. Уведомления
4. Экспорт данных

### **Фаза 4 (Оптимизация)**
1. Производительность
2. Доступность
3. Мобильная версия
4. PWA поддержка

---

## 📝 **ПРИМЕЧАНИЯ ДЛЯ ДИЗАЙНЕРА**

1. **Стиль:** Темный, минималистичный, профессиональный
2. **Анимации:** Плавные, ненавязчивые (Framer Motion)
3. **Иконки:** Emoji + Heroicons/SVG
4. **Шрифты:** Inter или системные (SF Pro, Segoe UI)
5. **Отступы:** Минимальные, компактная компоновка
6. **Цвета:** Темная тема с яркими акцентами
7. **Градиенты:** Использовать умеренно
8. **Тени:** Легкие, для глубины

---

## 🎯 **КРИТЕРИИ ПРИЕМКИ**

- [ ] Все виджеты отображаются корректно
- [ ] Анимации плавные (60fps)
- [ ] Данные обновляются в реальном времени
- [ ] Адаптивность работает
- [ ] Доступность соответствует WCAG AA
- [ ] Производительность в норме
- [ ] Безопасность проверена
- [ ] Документация полная

---

**Версия:** 1.0  
**Дата:** 2026-04-03  
**Статус:** Готово к реализации