# 🎨 Style Manager — PAD+ AI v4.0

## Обзор

Style Manager управляет стилем ответов на основе эмоционального состояния.

**Файл:** `backend/core/style_manager.py`

## Параметры стиля

| Параметр | Значения | Описание |
|----------|----------|----------|
| tone | friendly, serious, neutral, playful | Тон общения |
| verbosity | concise, moderate, detailed | Уровень детализации |
| color | confident, uncertain, balanced | Эмоциональная окраска |

## Зависимость от эмоций

| Эмоция | Влияние |
|--------|---------|
| Pleasure > 0.3 | tone: friendly |
| Pleasure < -0.3 | tone: serious |
| Arousal > 0.3 | verbosity: detailed |
| Arousal < -0.3 | verbosity: concise |
| Confidence > 0.7 | color: confident |
| Confidence < 0.3 | color: uncertain |
