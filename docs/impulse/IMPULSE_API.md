# Impulse API — что умеет ядро

## Эндпоинты

### GET `/api/v1/impulse`

Возвращает текущее состояние импульсного ядра.

```json
{
  "primary_question": "Что я могу понять?",
  "primary_label": "understand",
  "dimensions": [
    {"label": "understand", "question": "Что я могу понять?", "weight": 0.6},
    {"label": "improve",   "question": "Что я могу улучшить?", "weight": 0.0},
    {"label": "protect",   "question": "Что я могу защитить?", "weight": 0.0},
    {"label": "create",    "question": "Что я могу создать?",  "weight": 0.4}
  ],
  "stack_depth": 0,
  "created_at": "2026-06-11T14:43:36",
  "modified_at": "2026-06-11T14:50:13"
}
```

### PUT `/api/v1/impulse`

Устанавливает веса размерностей.

```json
// Request
{"weights": {"understand": 0.7, "create": 0.3}}
// Response — полное состояние (аналогично GET)
```

- Не указанные в `weights` размерности получают `weight = 0.0`
- Нормализация к 1.0 **не выполняется**

### PUT `/api/v1/impulse/question`

Устанавливает импульс по строке вопроса (обратная совместимость).

```json
// Request
{"question": "понять"}
// Response — полное состояние
```

- Ищет подстроку среди известных вопросов
- При совпадении ставит `weight = 1.0` на найденную размерность
- Без совпадения — ставит первую размерность

### POST `/api/v1/impulse/push`

Сохраняет текущее состояние в стек.

```json
// Response
{"success": true, "stack_depth": 1}
```

### POST `/api/v1/impulse/pop`

Восстанавливает предыдущее состояние из стека.

```json
// Response
{"success": true, "stack_depth": 0}
```

- При пустом стеке возвращает `{"success": false, "stack_depth": 0}`

### GET `/api/v1/impulse/labels`

Возвращает все известные метки импульсов.

```json
{
  "understand": "Что я могу понять?",
  "improve": "Что я могу улучшить?",
  "protect": "Что я могу защитить?",
  "create": "Что я могу создать?"
}
```

## Интеграция

### Через код (Python)

```python
from scripts.impulse import get_impulse_core, set_impulse, push_impulse, pop_impulse

core = get_impulse_core()
core.get_primary_label()        # "understand"
core.get_prompt_line()          # "Твой импульс: ..."
core.set_from_labels({"create": 1.0})
core.push()                     # сохранить в стек
core.pop()                      # восстановить из стека
```

### В системном промпте

Импульс автоматически встраивается в промпт генерации на фазе `generate` пайплайна:

```
Твой импульс: "Что я могу понять? (0.7), Что я могу создать? (0.3)" — многомерная мотивация познания.
```

## Файловое хранение

- `data/impulse.json` — полное состояние ядра (версия 2, размерности + стек)
- `data/current_impulse.txt` — однострочный промпт для генерации
