# Memory System — подсистема памяти

## Концепция

Память PAD+ — иерархическая, многослойная. Знания
консолидируются от конкретных эпизодов к абстрактным принципам.

## Четыре слоя

```
  ┌─────────────────────────────────────┐
  │         ROOTS (неизменяемые)         │
  │   принципы, философия, этика         │
  │   MemoryInterface.get_all()          │
  └──────────────▲──────────────────────┘
                 │ consolidation
  ┌──────────────┴──────────────────────┐
  │       SEMANTIC (знания)              │
  │   декларативные, процедурные,        │
  │   концептуальные, метакогнитивные    │
  └──────────────▲──────────────────────┘
                 │ consolidation
  ┌──────────────┴──────────────────────┐
  │       EPISODIC (диалоги)             │
  │   полные слепки диалогов с           │
  │   эмоциями, сущностями, значимостью  │
  └──────────────▲──────────────────────┘
                 │
  ┌──────────────┴──────────────────────┐
  │   RAG (векторный поиск)              │
  │   pgvector, LLM-суммаризация         │
  └─────────────────────────────────────┘
```

## Компоненты

### RAGMemory (`backend/memory/rag.py`)
- Векторный поиск по диалогам (pgvector)
- LLM-суммаризация результатов
- Извлечение сущностей из запросов

### EpisodicMemory (`backend/memory/episodic.py`)
- Хранение полных эпизодов диалогов
- CRUD + поиск по сходству
- `Episode` — dataclass с контекстом, эмоциями, значимостью

### SemanticMemory (`backend/memory/semantic.py`)
- Долгосрочные знания
- Типы: DECLARATIVE, PROCEDURAL, CONCEPTUAL, METACOGNITIVE
- Процедурные знания с шагами и триггерами

### PersonaMemory (`backend/memory/persona.py`)
- Личность системы: 7 черт (curiosity, skepticism, empathy, creativity, caution, openness, humility)
- Ценности, принципы, стиль общения
- Эволюция из диалогов

### UserPersona (`backend/memory/user_persona.py`)
- Предпочтения пользователя: verbosity, formality, technical_level, humor_level, interests
- Индивидуальный профиль для каждого пользователя

### RootsMemory (`backend/memory/roots.py`)
- Фундаментальные принципы (неизменяемые)
- Категории: CORE_IDENTITY, EPISTEMOLOGY, ETHICS, GOALS
- `RootKnowledge` — immutable запись

### MemoryHygiene (`backend/memory/hygiene.py`)
- Дедупликация, устаревание
- Оценка полезности записей
- Автоматическая очистка

### MemoryConsolidator (`backend/memory/consolidation.py`)
- Перенос знаний между слоями
- Episodic → Semantic → Roots
- Запускается каждые N диалогов

## API

`GET /api/v1/memory/dashboard` — агрегированная статистика всех систем памяти

## Интеграция с pipeline

| Фаза | Что делает |
|------|------------|
| RagPhase (4/22) | Поиск по RAG |
| EpisodicPhase (6/22) | Загрузка эпизодов |
| SemanticPhase (7/22) | Загрузка процедурных знаний |
| PersonaPhase (9/22) | Контекст личности |
| RootsPhase (10/22) | Фундаментальные принципы |
| SaveEpisodePhase (14/22) | Сохранение диалога |
