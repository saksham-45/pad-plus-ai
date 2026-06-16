# 🎭 Persona — PAD+ AI v4.0

## Обзор

Persona — система личности с 8 чертами характера, саморефлексиями и ценностями.

**Файлы:** `backend/memory/persona.py`, `backend/memory/user_persona.py`

## 8 черт характера

| Черта | Описание | Диапазон |
|-------|----------|----------|
| curiosity | Любопытство | 0.0 - 1.0 |
| helpfulness | Стремление помочь | 0.0 - 1.0 |
| adaptability | Адаптивность | 0.0 - 1.0 |
| caution | Осторожность | 0.0 - 1.0 |
| openness | Открытость | 0.0 - 1.0 |
| confidence | Уверенность | 0.0 - 1.0 |
| empathy | Эмпатия | 0.0 - 1.0 |
| skepticism | Сомнение | 0.0 - 1.0 |

Каждая черта имеет `value` (текущее значение) и `stability` (устойчивость к изменениям).

## Саморефлексии

- `insight` — инсайт
- `action` — предпринятое действие
- `confidence` — уверенность

## API

| Эндпоинт | Описание |
|----------|----------|
| `GET /api/v1/persona/stats` | Статистика |
| `GET /api/v1/persona/traits` | Черты характера |
| `GET /api/v1/persona/values` | Ценности |
| `GET /api/v1/persona/reflections` | Саморефлексии |
