# PAD+ AI — общая архитектура

## Сводка подсистем

```
                        ┌──────────────────────┐
                        │   Chat / WebSocket    │
                        └──────────┬───────────┘
                                   │
                        ┌──────────▼───────────┐
                        │   Pipeline (22 фазы)  │
                        │   backend/core/pipeline│
                        └──┬──┬──┬──┬──┬──┬───┘
                           │  │  │  │  │  │
         ┌─────────────────┘  │  │  │  │  └────────────┐
         ▼                    ▼  ▼  ▼  ▼                ▼
  ┌──────────┐   ┌──────┐ ┌──────┐ ┌──────┐   ┌──────────┐
  │  Emotion  │   │Memory│ │Persona│ │Roots │   │ X-Ray    │
  │ pad_model │   │ 4+   │ │Memory│ │Memory│   │ Trace +   │
  │           │   │layers│ │      │ │      │   │ Broadcaster│
  └──────────┘   └──────┘ └──────┘ └──────┘   └──────────┘
                                                   │
                    ┌──────────┐           ┌───────▼───────┐
                    │  Impulse │           │  Meta/Cognitive│
                    │   Core   │           │  Learner,State │
                    └──────────┘           │  Reflection    │
                                           └───────────────┘
```

## Иерархия влияния

```
          Impulse Core (когнитивное поле)
               ↓
         Persona Identity (черты личности)
               ↓
         Emotion State (аффективный тон)
               ↓
    ┌─────────────────────────────┐
    │    Memory (4 слоя)          │
    │  Roots → Semantic → Episodic│
    └─────────────────────────────┘
               ↓
          Generate Phase
               ↓
           Response
```

## Data flow

```
User message
    ↓ API (POST /api/v1/chat)
    ↓ PipelineContext
    ↓ 22 phase execution
    ↓ Impulse → Personality → Emotion → Memory → Generate
    ↓ PipelineResult
    ↓ Response (JSON)
    ↓ SaveEpisode → EmotionUpdate → PersonaEvolution
    ↓ EventsBroadcast (WebSocket)
    ↓ Reflection → Dreams → Metrics
```

## Файловая структура

```
backend/
├── api/          — 15 файлов роутов (все эндпоинты)
├── core/         — ядро: pipeline, xray, middleware, healer, CSRF
├── emotion/      — PAD-модель эмоций
├── memory/       — 4 слоя памяти + гигиена + консолидация
├── models/       — Pydantic модели
├── knowledge/    — граф знаний
├── scripts/      — impulse.py (ядро импульса)
docs/
├── architecture/ — документы подсистем
├── impulse/      — документы Impulse Core
tests/            — ~80 тестовых файлов
```

## API endpoints (105)

| Группа | Методы |
|--------|--------|
| Auth | login, register, me, refresh |
| Chat | /chat, /chat/stream |
| Impulse | GET/PUT /impulse, /question, /push, /pop, /labels |
| Memory | /memory/dashboard, /memory/consolidation |
| Knowledge | /knowledge/search, /related, /stats, /graph |
| X-Ray | /xray/* (20 endpoints) |
| Dialogs | /dialogs/* (8 endpoints) |
| Documents | /documents/* (10 endpoints) |
| Metrics | /metrics/* (8 endpoints) |
| Healer | /healer/* (8 endpoints) |
| Feedback | /feedback, /feedback/stats |
| User | /user/* (12 endpoints) |
| System | /health, /system/full-status, /mind-state |
