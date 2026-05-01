# 🔬 X-Ray Testing Guide

## 4 уровня тестирования

### 1. Unit-тесты (микро уровень)

**Расположение:** `tests/xray/test_trace_context.py`, `tests/xray/test_cognitive_state.py`

Тестируют отдельные компоненты:
- `SpanContext` — создание, длительность, статус
- `Trace` — дерево спанов, критический путь
- `TraceContextManager` — управление трассировками
- `CognitiveState` — метрики, решения, веса источников
- `CognitiveStateManager` — жизненный цикл состояний

**Запуск:**
```bash
pytest tests/xray/test_trace_context.py -v
pytest tests/xray/test_cognitive_state.py -v
```

### 2. Pipeline Trace Tests (сквозные)

**Расположение:** `tests/xray/test_pipeline_trace.py`

Проверяют прохождение trace через ВСЕ стадии пайплайна.

**Пример:**
```python
def test_full_pipeline_trace():
    trace_id = xray_collector.start_trace()
    run_pipeline("What is AI?", trace_id=trace_id)
    trace = xray_collector.get_trace(trace_id)
    stages = [event.stage for event in trace.events]
    
    assert "intent" in stages
    assert "retrieve" in stages
    assert "generate" in stages
```

### 3. Event Stream Tests (WebSocket)

**Расположение:** `tests/xray/test_websocket.py`

Проверяют real-time трансляцию событий.

**Запуск (требует запущенного сервера):**
```bash
pytest tests/xray/test_websocket.py -v
```

### 4. Golden Trace Tests (эталонные)

**Расположение:** `tests/xray/golden/`

Сравнивают текущие трассировки с эталонными.

**Пример:**
```python
def test_golden_trace():
    trace = run_pipeline_with_trace("Explain quantum physics")
    
    with open("tests/golden_traces/quantum.json") as f:
        golden = json.load(f)
    
    assert trace["stages"] == golden["stages"]
```

## Запуск всех тестов

```bash
# Все тесты X-Ray
pytest tests/xray/ -v

# С отчётом о покрытии
pytest tests/xray/ -v --cov=backend/core/xray

# Только unit-тесты
pytest tests/xray/test_trace_context.py tests/xray/test_cognitive_state.py -v
```

## VS Code интеграция

### settings.json
```json
{
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "editor.formatOnSave": true
}
```

### Запуск из VS Code
1. Откройте тестовый файл
2. Нажмите `Run Test` над каждым тестом
3. Или используйте Testing sidebar

## Validation Rules

Автоматическая проверка trace:

```python
def validate_trace(trace):
    required_stages = ["intent", "retrieve", "generate"]
    
    for stage in required_stages:
        if stage not in trace.stages:
            raise Exception(f"Missing stage: {stage}")
```

## Debug режим

Включите для подробного логирования:

```bash
XRAY_DEBUG=true pytest tests/xray/ -v -s
```

## Stress тесты

**Расположение:** `tests/xray/test_stress.py`

```python
def test_stress_pipeline():
    for _ in range(100):
        run_pipeline("test query")
    
    assert collector.events_count > 100
```

## Health endpoint

Добавьте endpoint для мониторинга:

```python
@app.get("/api/v1/xray/health")
def xray_health():
    return {
        "active_traces": len(collector.active),
        "events_per_sec": collector.rate(),
        "dropped_events": collector.dropped
    }
```

## CI/CD интеграция

### GitHub Actions
```yaml
- name: Run X-Ray Tests
  run: |
    pytest tests/xray/ -v --junitxml=xray-report.xml

- name: Upload Test Results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: xray-test-results
    path: xray-report.xml
```

## Best Practices

1. **Изолируйте тесты** — каждый тест должен быть независимым
2. **Используйте фикстуры** — для общих setup/teardown
3. **Мокайте внешние зависимости** — LLM, базы данных
4. **Проверяйте граничные случаи** — пустые трассировки, ошибки
5. **Документируйте ожидания** — что именно проверяет тест