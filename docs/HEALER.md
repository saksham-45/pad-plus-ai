# HEALER — Система самодиагностики и самовосстановления

## Что это

HEALER — **автономная система самодиагностики и самовосстановления** PAD+ AI.

Анализирует каждый проход пайплайна, находит проблемы, предлагает исправления и (в режиме auto) применяет их автоматически.

```
Pipeline Complete
       │
       ▼
┌──────────────────────┐
│  5 Детекторов        │── DiagnosticReport[]
│  SlowPhases          │    ├ severity: info|warning|error|critical
│  ErrorPath           │    ├ category: performance|correctness|resource|integrity|stability
│  BrokenPhases        │    ├ status: detected|fixed|ignored|rolled_back
│  ProviderHealth      │    ├ message + recommendation
│  StrategyDrift       │    ├ old_value + new_value + timestamp
└──────────┬───────────┘    └ details
           ▼
┌──────────────────────┐
│  ReflectionLoop      │── { learnings: [], changes: [], stats: {} }
│  Мета-анализ         │    ├ learnings: выявленные паттерны
│  истории циклов      │    ├ changes: применённые исправления
└──────────┬───────────┘    └ stats: total_cycles, success_rate, avg_duration
           ▼
┌──────────────────────┐
│  RemediationEngine   │── RemediationAction[]
│  Config-driven       │    ├ detector_pattern: "SlowPhasesDetector"
│  исправления         │    ├ condition: "generate > 8000ms"
└──────────┬───────────┘    ├ action: "switch_model"
           │                └ params: { prefer: "groq/llama-3.1-8b" }
           ▼
┌──────────────────────┐
│  HealingChangesStore │── { patch_id, component, file_path, backup }
│  Backup + Rollback   │    ├ record_apply() → patch_id
│  Thread-safe         │    ├ get_all() / get_by_status()
└──────────┬───────────┘    └ rollback(patch_id) → bool
           ▼
┌──────────────────────┐
│  HEALER Orchestrator │── Полный цикл (режим auto)
│  (внешний модуль)    │    ├ Diagnostics → Reports
│                      │    ├ AST Patcher → Patch files
│                      │    ├ Verifier → Verify patch
│                      │    └ Apply / Rollback
└──────────────────────┘
```

## Режимы работы

| Режим | Описание | Действия |
|-------|----------|----------|
| `monitor` | Только наблюдение | Диагностика + сохранение отчётов |
| `suggest` | Диагностика + рекомендации | Диагностика + генерация патчей, без apply |
| `auto` | Полный цикл | Диагностика → патч → верификация → apply/rollback |

## 5 Детекторов

### SlowPhasesDetector
- **Находит**: фазы пайплайна, превышающие порог длительности
- **Порог**: generate > 8000ms, другие фазы > 5000ms
- **Действие**: рекомендация смены модели

### ErrorPathDetector
- **Находит**: цепочки ошибок без fallback
- **Паттерн**: ProviderFailedError → AllProvidersFailedError
- **Действие**: включение fallback цепочки

### BrokenPhasesDetector
- **Находит**: фазы, завершившиеся с ошибкой без recovery
- **Паттерн**: verify/remember/emit error > 2 раз подряд
- **Действие**: рекомендация изоляции фазы

### ProviderHealthDetector
- **Находит**: нестабильных провайдеров (failure_rate > 0.3)
- **Метрики**: успешные/упавшие запросы по каждому провайдеру
- **Действие**: деприоритизация проблемного провайдера

### StrategyDriftDetector
- **Находит**: отклонения от выбранной стратегии
- **Паттерн**: mismatch между intent и фактическим routing
- **Действие**: корректировка стратегии

## ReflectionLoop

Анализирует историю циклов и возвращает:

```python
{
    "learnings": [
        {
            "title": "Высокий уровень ошибок диагностики",
            "description": "Доля ошибок: 66%",
            "impact": "Частые сбои снижают доверие к HEALER",
            "pattern": "repeated_failures",
        }
    ],
    "changes": [
        {
            "component": "SlowPhasesDetector",
            "old_value": "gpt-4",
            "new_value": "groq/llama-3.1-8b",
            "status": "applied",
            "reason": "auto-fix по результатам diagnostics",
            "timestamp": "2026-07-03T20:00:00",
        }
    ],
    "stats": {
        "total_cycles": 10,
        "success_cycles": 7,
        "failed_cycles": 2,
        "partial_cycles": 1,
        "total_reports": 15,
        "avg_duration_ms": 1250.50,
    }
}
```

## HealingChangesStore

Хранилище применённых изменений с возможностью отката.

```python
store = HealingChangesStore()

# Запись изменения (с backup файла)
patch_id = store.record_apply(
    component="SlowPhasesDetector",
    file_path="/path/to/config.py",
    old_content=b"model=gpt-4",
    new_content=b"model=groq/llama-3.1-8b",
    report={"recommendation": "switch to faster model"},
)

# Получение списка
all_changes = store.get_all()
applied = store.get_by_status("applied")    # только применённые
rolled_back = store.get_by_status("rolled_back")  # только откаченные

# Откат
success = store.rollback(patch_id)  # восстановит файл из backup
```

## DiagnosticReport

Единый формат результата диагностики:

```python
@dataclass
class DiagnosticReport:
    detector: str                    # Имя детектора
    severity: ReportSeverity         # info | warning | error | critical
    category: ReportCategory         # performance | correctness | resource | integrity | stability
    message: str                     # Описание проблемы
    recommendation: str              # Рекомендация
    status: str                      # detected | fixed | ignored | rolled_back
    old_value: Any                   # Значение до исправления
    new_value: Any                   # Значение после исправления
    details: dict                    # Дополнительные данные
    timestamp: str                   # Время создания
```

## API Endpoints

### HEALER Core
| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/v1/healer/status` | GET | Статус HealerListener |
| `/api/v1/healer/mode` | GET | Текущий режим |
| `/api/v1/healer/mode?mode=` | POST | Установить режим |
| `/api/v1/healer/diagnose` | POST | Запустить диагностику |
| `/api/v1/healer/reports` | GET | Последние отчёты |
| `/api/v1/healer/reports?severity=error&detector=` | GET | Фильтр отчётов |

### HEALER Bridge
| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/v1/healer/bridge/status` | GET | Статус HealerBridge |
| `/api/v1/healer/bridge/mode` | GET | Режим Bridge |
| `/api/v1/healer/bridge/mode?mode=` | POST | Установить режим Bridge |
| `/api/v1/healer/bridge/diagnose` | POST | Диагностика через Bridge |
| `/api/v1/healer/bridge/cycle` | POST | Полный healing cycle |
| `/api/v1/healer/bridge/cycle/stop` | POST | Остановить цикл |
| `/api/v1/healer/bridge/orchestrator` | GET | Статус Orchestrator |
| `/api/v1/healer/bridge/reflection/latest` | GET | Последняя рефлексия |
| `/api/v1/healer/bridge/changes?status=applied` | GET | Список изменений |
| `/api/v1/healer/bridge/rollback/{patch_id}` | POST | Откатить патч |
| `/api/v1/healer/bridge/auto-cycle` | GET/POST | Управление автоциклом |

## WebSocket события HEALER

```json
// Цикл завершён
{"type": "healer_bridge_cycle_complete", "data": {"status": "done", "reports": [], "result": {}}}

// Рефлексия обновлена
{"type": "healer_bridge_reflection", "data": {"learnings": [], "changes": [], "stats": {}}}

// Событие диагностики (streaming)
{"type": "healer_bridge_diag_event", "data": {"event": "detector_found", "detector": "SlowPhasesDetector", "report": {}}}
```

## Frontend компоненты

| Компонент | Описание |
|-----------|----------|
| `HealerPage` | Главная страница: статус, циклы, мост, автоцикл |
| `HealerReflectionPanel` | Панель рефлексии (WS + polling 30s + rollback) |
| `HealerTracePanel` | Трейсы HEALER (через X-Ray) |
| `HealerResults` | Результаты диагностики с фильтрацией |
| `HealerReflection` | Отображение learnings + changes + кнопка отката |
| `HealerHistory` | История циклов диагностики |

## Интеграция (main.py lifecycle)

В `backend/main.py` при старте сервера:

```python
# 1. WS manager внедряется в healer_routes
set_ws_manager(manager)

# 2. HealerBridge подключается к XRayTraceCollector
bridge = get_healer_bridge(mode=os.getenv("HEALER_MODE", "monitor"))
bridge.start(collector)

# 3. HealerListener подписывается на core TraceCollector
healer = get_healer()
healer.subscribe(lambda: core_collector)
```

## Тесты

```bash
# ReflectionLoop — 7 тестов
pytest tests/test_healing/test_reflection_loop.py -v

# ChangesStore — 7 тестов
pytest tests/test_healing/test_changes_store.py -v
```

## Поток данных

```
Pipeline Event
       │
       ▼
core TraceCollector ──→ save_trace(session_id, event)
       │                      │
       │                      ▼
       │              HealerListener.on_event()
       │                      │
       │                      ▼
       │              run_diagnostics()
       │                      │
       │                      ▼
       │              5 Detectors ──→ DiagnosticReport[]
       │                      │
       │                      ▼
       │              TraceCollector.save_trace ("diagnostic_completed")
       │              ReflectionLoop.reflect()
       │                      │
       │                      ▼
       │              WS broadcast: healer_bridge_reflection
       │
       ▼
XRayTraceCollector ──→ record_event(stage, duration, status)
       │
       ▼
XRayBroadcaster ──→ broadcast("trace", data)
                     broadcast("thought", data)
                     broadcast("pipeline", data)
```
