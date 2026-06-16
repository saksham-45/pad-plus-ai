# 🧠 Память — PAD+ AI v4.0

## Обзор

Система памяти PAD+ AI состоит из 7 типов, каждый со своим назначением и хранилищем.

## Типы памяти

### 1. RAG Memory (ChromaDB)

**Файл:** `backend/memory/rag.py`

Семантическая память диалогов на основе векторных эмбеддингов.

**Возможности:**
- Классификация тем (7 категорий: техническое, философское, личное, образовательное, творческое, аналитическое, бытовое)
- Извлечение сущностей (person, technology, concept, location, time, number)
- Извлечение связей между сущностями
- LLM-суммаризация диалогов
- Гибридный поиск (семантика + ключевые слова + давность)

**Методы:**
- `add_dialog()` — добавить диалог
- `search()` — семантический поиск
- `hybrid_search()` — гибридный поиск
- `search_by_topic()` — поиск по теме
- `get_recent()` — недавние диалоги

### 2. Fact Memory (SQLite + ChromaDB)

**Файлы:** `backend/memory/fact_memory.py`, `fact_memory_chroma.py`

Структурированные факты в формате subject-predicate-object.

**Схема:** `(subject, predicate, object, confidence, source)`

**Возможности:**
- Автопоиск противоречий
- Поиск по субъекту/объекту
- Обновление уверенности

### 3. Knowledge Graph (NetworkX)

**Файл:** `backend/knowledge/graph.py`

Граф концепций и связей.

**Структура:**
- Nodes: `{id, name, type, confidence, metadata}`
- Edges: `{source, target, type, weight}`

### 4. Episodic Memory (SQLite)

**Файл:** `backend/memory/episodic.py`

Последовательности событий с временными метками.

**Структура эпизода:**
- `timestamp`, `event_type`, `content`, `context`, `importance`

### 5. Semantic Memory (SQLite)

**Файл:** `backend/memory/semantic.py`

Общие знания и концепции.

**Структура:**
- `concept`, `category`, `properties`, `relations`, `confidence`, `source`

### 6. Roots Memory (JSON)

**Файл:** `backend/memory/roots.py`

Фундаментальные принципы (философия, этика, идентичность).

**Категории:**
- `philosophy` — философские принципы
- `ethics` — этические принципы
- `identity` — факты об идентичности
- `preferences` — предпочтения

### 7. Persona (SQLite)

**Файлы:** `backend/memory/persona.py`, `user_persona.py`

Личность с 8 чертами характера.

**Черты:**
| Черта | Описание |
|-------|----------|
| curiosity | Любопытство |
| helpfulness | Помощь |
| adaptability | Адаптивность |
| caution | Осторожность |
| openness | Открытость |
| confidence | Уверенность |
| empathy | Эмпатия |
| skepticism | Сомнение |

## Консолидация

**Файл:** `backend/memory/consolidation.py`

Автоматическая обработка памяти по аналогии со сном:
- Episodic → Semantic (перенос знаний)
- Deduplication (удаление дубликатов)
- Importance Ranking
- Forgetting (забывание неважного)

## Hygiene

**Файл:** `backend/memory/hygiene.py`

Автоматическая очистка:
- Дубликаты (схожесть > 0.85)
- Устаревшее (возраст > 90 дней)
- Низкое качество (полезность < 0.2)
