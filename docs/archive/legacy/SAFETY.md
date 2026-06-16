# 🛡️ Safety Layer — PAD+ AI v4.0

## Обзор

Safety Layer — система безопасности, проверяющая запросы на вредоносность.

**Файл:** `backend/core/safety_layer.py`

## Проверки

### 1. Injection Detection
- SQL injection
- Prompt injection
- Command injection

### 2. Harmful Content
- Вредоносные запросы
- Опасные инструкции

### 3. Rate Limiting
**Файл:** `backend/core/rate_limiter.py`

| Тип | Лимит |
|-----|-------|
| Стандартные запросы | 60/мин |
| Чат | 10/мин |
| Поиск | 30/мин |

### 4. Strict Mode
Усиленная проверка с блокировкой подозрительных запросов.

## API

| Эндпоинт | Описание |
|----------|----------|
| `GET /api/v1/safety/stats` | Статистика безопасности |
| `POST /api/v1/safety/check` | Проверка текста |
| `POST /api/v1/safety/strict-mode` | Вкл/выкл строгий режим |
