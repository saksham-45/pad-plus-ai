# Experience Layer

## Что это

Experience Layer — слой наблюдения, который фиксирует разницу между ожиданием и реальностью после каждого диалога. Работает в режиме read-only (v0): только запись, без обратного влияния на систему.

## Как работает

1. После ответа AI собираются сигналы: сентимент, сложность, противоречия, повторы
2. Определяется тип взаимодействия (7 типов)
3. Вычисляется significance (0.0–1.0) — насколько событие значимо
4. Запись сохраняется в `data/experiences/exp_*.json`
5. Significance используется тремя слоями:

   - **v1: Emotion** — чем выше sig, тем сильнее PAD-реакция
   - **v2: Impulse** — значимые события перераспределяют веса импульсов
   - **v3: Persona** — черты характера и стиль меняются пропорционально sig

## API

- `GET /api/v1/admin/experiences` — список записей
- `GET /api/v1/admin/experiences/stats` — сводка
- `GET /api/v1/admin/persona/deltas` — текущие коэффициенты

## CLI

```bash
python -m core.experience.analyzer
python -m core.experience.analyzer --recent 20
python -m core.experience.analyzer --min-significance 0.7
```

## Типы взаимодействий

| Тип | Доля | Описание |
|-----|------|----------|
| new_knowledge | ~39% | Штатное получение знаний |
| praise | ~15% | Похвала, положительная обратная связь |
| contradiction | ~12% | Обнаружено противоречие |
| exploration | ~11% | Исследовательский вопрос |
| criticism | ~10% | Критика, недовольство |
| error_recovery | ~9% | Сбой, восстановление |
| repetition | ~5% | Повтор вопроса |

## Коэффициенты

### Emotion (`emotion_update.py`)
```
new_knowledge: 0.12  contradiction: 0.35  praise: 0.25
criticism: 0.30  exploration: 0.25  error_recovery: 0.35  repetition: 0.08
```

### Impulse (`impulse_update.py`)
```
criticism:     understand -0.25, improve +0.20
contradiction: understand -0.20, improve +0.15
praise:        understand +0.20
exploration:   understand +0.15
error_recovery: protect +0.20, improve +0.10
repetition:    understand -0.08
```

### Persona system (`persona_evolution.py`)
```
contradiction: skepticism +0.08, humility +0.08
praise:        empathy +0.10, openness +0.08
criticism:     humility +0.10, skepticism +0.05
exploration:   curiosity +0.10, creativity +0.08
error_recovery: caution +0.10, humility +0.08
repetition:    curiosity -0.03
new_knowledge: curiosity +0.03
```

### Persona user style (`persona_evolution.py`)
```
contradiction: technical_level +0.03
praise:        verbosity +0.03, formality -0.02
criticism:     technical_level +0.02
exploration:   formality -0.03
error_recovery: technical_level -0.02
repetition:    verbosity -0.02
```
