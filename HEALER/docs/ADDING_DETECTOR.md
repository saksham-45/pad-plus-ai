# Добавление нового детектора

## Контракт

Все детекторы наследуют `BaseDetector` из `healer.diagnostics.base`:

```python
class BaseDetector(ABC):
    @abstractmethod
    def detect(self) -> list[DiagnosticReport]:
        ...
```

## Шаг 1: Создать файл детектора

```python
# healer/diagnostics/my_detector.py
from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.diagnostics.base import BaseDetector

class MyDetector(BaseDetector):
    def detect(self) -> list[DiagnosticReport]:
        reports = []
        for trace in get_traces():
            if problem_found(trace):
                reports.append(DiagnosticReport(
                    severity=ReportSeverity.WARNING,
                    category=ReportCategory.PERFORMANCE,
                    trace_id=trace.trace_id,
                    location=f"trace {trace.name}",
                    message="Найдена проблема",
                    recommendation="Как исправить",
                ))
        return reports
```

**Важно:** `detector` поле не заполняется — оно проставляется автоматически в `run_diagnostics()`.

## Шаг 2: Зарегистрировать в `__init__.py`

```python
# healer/diagnostics/__init__.py
from healer.diagnostics.my_detector import MyDetector
```

## Шаг 3: Добавить в CLI runner

```python
# healer/diagnostics/runner.py
from healer.diagnostics.my_detector import MyDetector

DETECTORS = [
    # ...
    ("MyDetector", MyDetector()),
]
```

## Шаг 4: Написать тесты

```python
# tests/test_my_detector.py
class TestMyDetector:
    def test_detects_problem(self):
        detector = MyDetector()
        reports = detector.detect()
        assert len(reports) > 0
```

## Шаг 5: Связать с паттерном (опционально)

```python
# healer/patcher/python_patcher.py
PATTERN_NAMES["MyDetector"] = "my_patch"
```

## Streaming события

Детектор автоматически участвует в streaming-событиях `run_diagnostics()`:
- `detector_start` — перед `detect()`
- `detector_found` — для каждого найденного отчёта
- `detector_done` — после завершения

Никаких дополнительных действий не требуется.

## Требования

- Детектор наследует `BaseDetector` и реализует `detect()`
- Должен быть stateless (один экземпляр переиспользуется)
- Должен возвращать `list[DiagnosticReport]`
- Не должен изменять trace_store
- Только stdlib + X-RAY ядро (zero external dependencies)
