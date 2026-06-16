# 🔍 RAG v3.0 — PAD+ AI v4.0

## Обзор

RAG (Retrieval-Augmented Generation) — семантическая память диалогов на основе ChromaDB.

**Файл:** `backend/memory/rag.py`

## Возможности

### Классификация тем
7 категорий: техническое, философское, личное, образовательное, творческое, аналитическое, бытовое

### Извлечение сущностей
6 типов: person, technology, concept, location, time, number

### Поиск
| Метод | Описание |
|-------|----------|
| `search()` | Базовый семантический поиск |
| `hybrid_search()` | Семантика + ключевые слова + давность |
| `search_by_topic()` | Поиск по теме |
| `search_by_keywords()` | Поиск по ключевым словам |
| `get_recent()` | Недавние диалоги |

## API

| Эндпоинт | Описание |
|----------|----------|
| `GET /api/v1/rag/stats` | Статистика RAG |
| `GET /api/v1/rag/topics` | Темы диалогов |
| `GET /api/v1/rag/entities` | Индекс сущностей |
| `POST /api/v1/rag/search` | Семантический поиск |
| `POST /api/v1/rag/hybrid` | Гибридный поиск |
| `POST /api/v1/rag/by-topic` | Поиск по теме |
