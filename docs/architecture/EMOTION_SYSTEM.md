# Emotion System — эмоциональная подсистема

## Концепция

Эмоции в PAD+ — это не симуляция чувств, а аффективный слой,
влияющий на тон и стиль ответа. Реализована трёхмерная модель
PAD (Pleasure-Arousal-Dominance) с дополнительными метриками.

## Параметры (PAD+)

| Параметр | Диапазон | Описание |
|----------|----------|----------|
| pleasure | [-1, 1] | Удовольствие — позитив/негатив |
| arousal | [0, 1] | Возбуждение — энергия/апатия |
| dominance | [-1, 1] | Доминантность — уверенность/неуверенность |
| curiosity | [0, 1] | Любопытство — желание исследовать |
| confidence | [0, 1] | Уверенность в ответах |
| social_connection | [-1, 1] | Социальная связь — теплота/отчуждение |

## Реакция на события

Система реагирует на 8 типов событий:
- `new_knowledge` — ↑ curiosity
- `contradiction` — ↓ confidence, ↑ curiosity
- `user_praise` — ↑ pleasure, ↑ social_connection
- `user_criticism` — ↓ pleasure, ↓ confidence
- `fallback` — ↓ confidence
- `self_reflection` — ↑ curiosity, ↑ confidence
- `new_skill` — ↑ dominance, ↑ confidence

## Стиль ответа

Эмоции влияют на три параметра ответа:
- **tone** — `warm` / `neutral` / `cold` / `playful` / `serious`
- **verbosity** — `concise` / `balanced` / `detailed`
- **color** — `rich` / `neutral` / `minimal`

## Архитектура

```
Событие (из pipeline)
     ↓
PADModel.apply_event()
     ↓
EmotionState (параметры)
     ↓
EmotionState.get_style()
     ↓
tone / verbosity / color → в GeneratePhase
```

## Интеграция

- **EmotionPhase** (фаза 8/22) — читает эмоции в контекст
- **EmotionUpdatePhase** (фаза 15/22) — обновляет эмоции после ответа
- **GeneratePhase** — встраивает tone/verbosity/color в промпт
- **DreamSystem** — затухание эмоций во сне

## Код

- `backend/emotion/pad_model.py` — PADModel + EmotionState
- `data/emotion_state.json` — файл состояния
