# План Фаза 4: Типизация, тесты финальная чистка

## Приоритет: P0 → P1 → P2

---

## P0: Тесты для pipeline-фаз

**Сейчас:** 14 фаз, 0 unit-тестов. 

**План:**
1. `tests/test_pipeline/` — директория для тестов фаз
2. Каждая фаза получает файл: `test_anti_loop.py`, `test_safety.py`, `test_intent.py`, `test_rag.py`, `test_knowledge_graph.py`, `test_episodic.py`, `test_semantic.py`, `test_emotion.py`, `test_persona.py`, `test_generate.py`, `test_truth_loop.py`, `test_events.py`, `test_health.py`, `test_response_guard.py`
3. Для каждой фазы — 2-3 теста: успех, fallback (импорт не найден), пустые данные
4. `test_orchestrator.py` — 1 интеграционный тест

**Оценка:** 2-3 часа · Риск: низкий

---

## P1: Чистка `pipeline_handlers.py`

**Сейчас:** `backend/core/pipeline_handlers.py` (271 строка, 0 импортов после рефакторинга). Все фазы переписаны в `core/pipeline/phases/`.

**План:**
1. Перепроверить grep — нет ли импортов `pipeline_handlers`
2. Если нет — удалить

**Оценка:** 5 минут · Риск: низкий

---

## P2: Оптимизация времени старта API-тестов

**Сейчас:** `test_full_system_status_structure` — 17 секунд из-за:
- `from memory.rag import get_rag` (пытается подключиться к БД)
- `from knowledge.graph import get_knowledge_graph`
- `from emotion.pad_model import get_pad_model`

**План:**
1. Добавить `@pytest.fixture` с `monkeypatch.setenv("SKIP_DB", "1")` или
2. Создать `tests/conftest.py` с глобальной настройкой окружения для быстрых тестов
3. Либо просто принять 17 секунд (тест запускается редко)

**Оценка:** 15 минут · Риск: низкий

---

## P3: Фронтенд — TypeScript миграция

**Текущий стек:**
- React 18 (JSX)
- Vite 5
- `@types/react` и TypeScript уже в devDependencies
- Нет ни одного `.tsx` файла

### Состояние фронтенда:

| Раздел | Файлы | Размер |
|--------|-------|--------|
| pages/ | 9 файлов | ~4000 строк |
| components/ | 15 файлов | ~5000 строк |
| components/ui/ | 3 файла | ~300 строк |
| components/widgets/ | 7 файлов | ~1500 строк |
| components/xray/ | 4 файла | ~800 строк |
| hooks/ | 2 файла | ~200 строк |
| services/ | 2 файла | ~300 строк |

**Всего:** ~12 000 строк JSX, 42 файла

### Стратегия: «Слоёный» подход (не взрывной)

```
Фаза A: Инфраструктура TS (30 мин)
  - tsconfig.json уже есть
  - vite.config.ts (переименовать)
  - main.jsx → main.tsx
  - services/api.js → services/api.ts
  - services/modelCache.js → services/modelCache.ts

Фаза B: types/ (1 час)
  - types/index.ts
    * Model, Provider, ChatMessage, APIKey, User
    * PipelineResult, DashboardMetrics
    * Все типы из Python API (один к одному)

Фаза C: ui/ компоненты (30 мин)
  - Button.jsx → Button.tsx
  - Card.jsx → Card.tsx

Фаза D: hooks/ (1 час)
  - useWebSocket.js → useWebSocket.ts
  - useNotifications.jsx → useNotifications.tsx

Фаза E: pages/ — по 1 файлу за раз (4-6 часов)
  - LoginPage.jsx → LoginPage.tsx (самый простой)
  - ProvidersPage.jsx → ProvidersPage.tsx
  - ConnectedProvidersPage.jsx → ConnectedProvidersPage.tsx
  - XRayPage.jsx → XRayPage.tsx
  - SettingsPage.jsx → SettingsPage.tsx
  - InstructionsPage.jsx → InstructionsPage.tsx
  - HistoryPage.jsx → HistoryPage.tsx
  - DocumentsPage.jsx → DocumentsPage.tsx

Фаза F: components/ — по 2-3 файла за раз (3-4 часа)
  - ProviderManagement.jsx → ProviderManagement.tsx (самый сложный, ~500 строк)
  - ChatInterface.jsx → ChatInterface.tsx
  - ModelSelector.jsx → ModelSelector.tsx
  - Dashboard.jsx → Dashboard.tsx
  - LeftSidebar.jsx → LeftSidebar.tsx
  - RightSidebar.jsx → RightSidebar.tsx
  - CognitivePanel.jsx → CognitivePanel.tsx
  - остальные
```

### Общий план миграции:

| Шаг | Что | Файлов | Время |
|-----|-----|--------|-------|
| A | Инфраструктура TS + сервисы | 4 | 30 мин |
| B | types/index.ts | 1 | 1 ч |
| C | ui/ компоненты | 2 | 30 мин |
| D | hooks/ | 2 | 1 ч |
| E | pages/ (8 файлов) | 8 | 4-6 ч |
| F | components/ (15 файлов) | 15 | 3-4 ч |
| G | Финальный build + фикс ошибок | — | 1-2 ч |

**Итого:** ~12-15 часов · Риск: средний

### Ключевые риски:
1. **PropTypes → TypeScript** — многие компоненты используют `prop-types` или鸭子-типизацию через дефолтные параметры
2. **window events** — `model-changed`, `keys-updated` — нужны типизированные обёртки
3. **apiFetch** — возвращает `Promise<any>` → нужен generic `apiFetch<T>`
4. **ReactFlow** — типы из `reactflow` пакета (уже есть в зависимостях)
5. **Recharts** — типы из `recharts` (уже есть)
6. **Framer Motion** — типы из `framer-motion`

### Не TS:
- CSS файлы (остаются `.css`)
- `.env`, конфиги

**Decision:** После каждого шага — `npm run build`. Если билд зелёный — коммит.

---

## План тестирования фронтенда (опционально)

После TS миграции:
1. `vitest` — добавить
2. `@testing-library/react` — добавить  
3. Тест для `ChatInterface`, `ProviderManagement`, `ModelSelector`
4. Тест для window events (`model-changed`)

---

## Итоговый порядок

```
P0: pipeline тесты (2-3ч)
  ↓
P1: удалить pipeline_handlers.py (5 мин)
  ↓
P2: оптимизация API тестов (15 мин)
  ↓
P3: TS миграция фронтенда (12-15ч)
  ├── A: Инфраструктура (30 мин)
  ├── B: types/ (1 ч)
  ├── C: ui/ (30 мин)
  ├── D: hooks/ (1 ч)
  ├── E: pages/ (4-6 ч)
  ├── F: components/ (3-4 ч)
  └── G: build fix (1-2 ч)
```

**Общая оценка:** 15-20 часов · Риск: средний (из-за фронтенда)
