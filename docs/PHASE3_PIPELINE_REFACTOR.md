# Фаза 3: Рефакторинг Pipeline — разбиение монолита

## Текущее состояние

| Метрика | Значение |
|---------|----------|
| Файл | `backend/core/pipeline.py` |
| Строк | 1171 |
| Этапов в `execute()` | 14 |
| Средний этап | ~50-80 строк |
| Вложенность | Все `async def` внутри `execute()` |
| Lazy imports | Каждый этап импортирует модули в try/except |
| `pipeline_handlers.py` | 271 строка, базовый класс + `HandlerResult`, но 0 конкретных хендлеров |

## Структура: что куда

```
backend/core/pipeline.py → backend/core/pipeline/
```

```
pipeline/
  __init__.py              # PipelineExecutor + get_pipeline()
  models.py                # PipelineState, DegradationInfo, PipelineResult
  base.py                  # PipelinePhase (abstract)
  phases/
    __init__.py             # Registry всех фаз
    anti_loop.py            # Phase 1
    safety.py               # Phase 2
    intent.py               # Phase 3
    retrieve.py             # Phase 4 (RAG + Knowledge Graph)
    episodic.py             # Phase 4.1
    semantic.py             # Phase 4.2
    emotion.py              # Phase 5
    persona.py              # Phase 6
    generate.py             # Phase 7 (LLM call)
    consolidation.py        # Phase 8.2
    emotion_update.py       # Phase 8 (update emotion)
    persona_evolution.py    # Phase 10
    events.py               # Phase 11
    health.py               # Phase 12
    reflection.py           # Phase 13
    dreams.py               # Phase 14
    metrics.py              # V3.2 metrics
    response_guard.py       # Response guard
  error_handler.py          # DegradationInfo, FailStrategy
  context.py                # PipelineContext dataclass (user_message, api_key, provider, etc.)
```

## Порядок выполнения

### P0: models + context (вынос структур)

**Из pipeline.py:**
- `PipelineState` enum
- `DegradationInfo` dataclass  
- `PipelineResult` dataclass + `to_dict()`, `_get_truth_status()`, `_get_sources_count()`, `_generate_xray_insights()`

**В `pipeline/models.py`.**
**Новый `pipeline/context.py`:** `PipelineContext(user_message, context, session_id, api_key, provider)`

Обратная совместимость: `from core.pipeline import PipelineResult` → продолжает работать через `__init__.py`.

### P1: PipelinePhase (абстрактный класс)

**На базе `pipeline_handlers.py`:**
- Упростить `PipelineHandler` → `PipelinePhase`
- Сигнатура: `async def execute(context: PipelineContext) -> PhaseResult`
- `PhaseResult(success, data, errors, metadata, degradation: Optional[DegradationInfo])`
- `name: str` — имя фазы для логирования

**В `pipeline/base.py`.**

### P2: Каждая фаза — отдельный файл

Условный шаблон каждой фазы:

```python
class AntiLoopPhase(PipelinePhase):
    name = "anti_loop"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        warning = check_anti_loop(ctx.user_message)
        if warning:
            return PhaseResult(
                success=True,  # мягкая обработка
                data={"warning": warning, "blocked": True},
                metadata={"anti_loop_warning": warning}
            )
        return PhaseResult(success=True, data={"blocked": False})
```

### P3: PipelineExecutor — чистый оркестратор

```python
class PipelineExecutor:
    def __init__(self):
        self._phases: Dict[str, PipelinePhase] = {}
        self._register_phases()
    
    def _register_phases(self):
        phases = [
            AntiLoopPhase(),
            SafetyPhase(),
            IntentPhase(),
            RetrievePhase(),
            ...
        ]
        for phase in phases:
            self._phases[phase.name] = phase
    
    async def execute(self, ...) -> PipelineResult:
        ctx = PipelineContext(...)
        result = PipelineResult(success=False)
        
        for phase_name, phase in self._phases.items():
            try:
                phase_result = await phase.execute(ctx)
                # запись результата в PipelineResult
                if not phase_result.success:
                    self._mark_degraded(phase_name, phase_result.errors)
                    if self._should_stop(phase_name):
                        break
            except Exception as e:
                self._mark_degraded(phase_name, str(e))
                if self._should_stop(phase_name):
                    break
        
        # финализация
        return result
```

**Преимущества:**
- Каждая фаза тестируется изолированно
- Приватные импорты не засоряют `execute()`
- `try/except` в одном месте, а не 14 копий
- Можно отключать фазы по имени
- Порядок фаз легко менять

### P4: Удаление дублирования

- `_mark_degraded()` → общий механизм в `PipelineExecutor`
- Все `try/except ErrorSeverity.LOW` → единый `phase.execute()` wrapper
- `_record_metrics()` → `MetricsPhase`

### P5: Тесты для каждой фазы

```
tests/test_pipeline/
  test_anti_loop.py
  test_safety.py
  test_intent.py
  test_retrieve.py
  test_generate.py
  ...
  test_orchestrator.py     # PipelineExecutor интеграционный
```

### P6: pipeline.py → заглушка обратной совместимости

```python
# backend/core/pipeline.py
# DEPRECATED — используйте core.pipeline
from core.pipeline import PipelineExecutor, PipelineResult, get_pipeline
```

---

## Оценка сложности

| Пункт | Файлов | Строк | Риск | Время |
|-------|--------|-------|------|-------|
| P0: models + context | 2 новых | ~200 | Низкий | 30 мин |
| P1: PipelinePhase | 1 новый | ~60 | Низкий | 15 мин |
| P2: Фазы (14 шт) | 14 новых | ~700 | Средний | 3-4 ч |
| P3: Оркестратор | 1 новый | ~200 | Средний | 1 ч |
| P4: Чистка дублирования | patch | ~100 | Низкий | 30 мин |
| P5: Тесты | 15 новых | ~500 | Низкий | 2 ч |
| P6: pipeline.py → заглушка | 1 patch | ~10 | Низкий | 5 мин |

**Итого:** ~7.5-8.5 часов

---

## Критерии успеха

1. Все существующие тесты проходят (44 provider + 9 cache + 2 API + 16 gigachat = 71)
2. `GET /chat` работает через новый оркестратор
3. Каждая фаза покрыта unit-тестом
4. Нет `try/except` с пустым `pass` в каждой фазе
5. Файл `pipeline.py` сокращён с 1171 до ~30 строк (заглушка)
