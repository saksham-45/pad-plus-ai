# X-Ray: Brain + Tasks

## Девиз
Тест падает → чини СИСТЕМУ, не тест.

## Суть X-Ray
Система наблюдаемости AI. Вшита в каждый запрос.
Проверяет ПРОЦЕСС (20 phases, порядок, длительности, решения), а не результат.

---

## Текущее состояние (2026-06-08 23:00)

### ✅ Работает стабильно
- Чат: отвечает (OpenRouter, 2.3s)
- История: загружается мгновенно
- Провайдеры: загружаются мгновенно
- X-Ray: 6 тестов, показывает живые данные
- 55 тестов pipeline — все зелёные

### ⚠️ Задокументированные проблемы
- **Документы**: `count="exact"` пофикшен, но страница могла не успеть обновиться (нужен перезапуск)
- **RAG при старте**: `__init__` использует `self.conn/cursor` вместо локальных — пофикшено (см. `backend/memory/rag.py:422-423`)
- **stop.bat**: больше не убивает все python.exe/node.exe в системе
- **start.bat**: убран `--reload` (пустая трата ресурсов при ручном рестарте)
- **LeftSidebar**: очищен от дублирующих вкладок
- **App.jsx**: навигация восстановлена (все вкладки на месте)

---

## План оптимизации

### P0: Скорость старта (сейчас ~6-8s → цель 2-3s)
| Задача | Оценка | Статус |
|--------|--------|--------|
| `rag.py __init__`: ленивая иницализация таблиц/индексов | 15min | ❌ |
| Lazy import роутов в `frontend_routes.py` (1952 строки) | 20min | ❌ |
| `memory/__init__.py`: отложить тяжелые импорты | 10min | ❌ |
| Dashboard: отложить загрузку виджетов | 15min | ❌ |

### P1: Frontend производительность
| Задача | Оценка | Статус |
|--------|--------|--------|
| React.lazy + Suspense для всех страниц | 30min | ❌ |
| Убрать фоновые API запросы с hidden-страниц (Dashboard) | 15min | ❌ |
| Мемоизация `metrics/system` + `mind-state` запросов | 15min | ❌ |

### P2: Долгосрочные улучшения
| Задача | Оценка | Статус |
|--------|--------|--------|
| Унифицировать WebSocket (X-Ray + generic) | 1h | ❌ |
| REST `/xray/latest` с persist в SQLite | 1h | ❌ |
| InsightsEngine на реальных данных | 2h | ❌ |
| MetaLearner: анализ стратегий | 2h | ❌ |

---

## Ключевые файлы (для контекста)
```
backend/core/xray/trace_collector.py     — сбор событий
backend/core/xray/broadcaster.py         — WebSocket трансляция
backend/core/xray/thought_visualizer.py  — мысли AI
backend/core/pipeline/executor.py        — интеграция X-Ray
backend/memory/rag.py                    — RAG память (чинить __init__)
backend/api/frontend_routes.py           — 1952 строки, основной роутер
backend/api/document_routes.py           — документы (чинить count)
frontend/src/App.jsx                     — главная навигация
frontend/src/components/Dashboard.jsx    — главная страница (8 виджетов)
frontend/src/components/LeftSidebar.jsx  — очищен от дублей
tests/test_xray/                         — 6 X-Ray тестов
docs/XRAY_GUIDE.md                       — документация
```

---

## Для новой сессии: старт

1. Прочитать `XRAY_BRAIN.md` (корень) — контекст
2. Прочитать `docs/XRAY_BRAIN_TASKS.md` — задачи
3. Запустить `stop.bat` → `start.bat`
4. Продолжить с P0.1: ленивая иницализация `rag.py`
