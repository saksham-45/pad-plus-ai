# Добавление нового паттерна

## Контракт

Все паттерны наследуют `BasePattern` из `healer.patcher.patterns.base_pattern`:

```python
class BasePattern(ABC):
    name: str = ""
    description: str = ""
    supported_detectors: list[str] = []

    @abstractmethod
    def can_apply(self, source_code: str, report: DiagnosticReport) -> bool:
        ...

    @abstractmethod
    def apply(self, source_code: str, report: DiagnosticReport) -> tuple[str, dict[str, Any]]:
        ...
```

- `can_apply()` — проверяет, применим ли паттерн (без модификации)
- `apply()` — возвращает `(patched_code, metadata)`. metadata обязана содержать `diff_lines`

## Шаг 1: Создать файл паттерна

```python
# healer/patcher/patterns/my_patch_py.py
import ast
from typing import Any

from healer.diagnostics.report import DiagnosticReport
from healer.patcher.patterns.base_pattern import BasePattern


class MyPatchPattern(BasePattern):
    name = "my_patch"
    description = "Что делает паттерн"
    supported_detectors = ["my_detector"]

    def can_apply(self, source_code: str, report: DiagnosticReport) -> bool:
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return False
        # Анализ: есть ли в коде то, что мы можем исправить
        checker = MyChecker()
        checker.visit(tree)
        return bool(checker.found_issues)

    def apply(self, source_code: str, report: DiagnosticReport) -> tuple[str, dict[str, Any]]:
        tree = ast.parse(source_code)
        transformer = MyTransformer()
        transformer.visit(tree)
        patched = ast.unparse(tree)
        metadata = {
            "patched": transformer.patched,
            "diff_lines": _count_diff_lines(source_code, patched),
        }
        return patched, metadata
```

## Шаг 2: Зарегистрировать в `patterns/__init__.py`

```python
# healer/patcher/patterns/__init__.py
from healer.patcher.patterns.my_patch_py import MyPatchPattern

ALL_PATTERNS["my_patch"] = MyPatchPattern()
PATTERN_DETECTOR_MAP["my_patch"] = ["my_detector"]
```

## Шаг 3: Интегрировать с PythonPatcher

```python
# healer/patcher/python_patcher.py
PATTERN_NAMES["MyDetector"] = "my_patch"
SUPPORTED_PATTERNS.add("my_patch")
```

## Шаг 4: Написать тесты

```python
class TestMyPatch:
    def test_can_apply(self):
        pattern = MyPatchPattern()
        code = "def foo():\n    pass"
        assert pattern.can_apply(code, mock_report)

    def test_apply(self):
        pattern = MyPatchPattern()
        code = "def foo():\n    pass"
        patched, meta = pattern.apply(code, mock_report)
        assert "my_change" in patched
        assert "diff_lines" in meta
```

## Требования

- Паттерн наследует `BasePattern` и реализует `can_apply()` + `apply()`
- `can_apply()` не должен модифицировать код (read-only анализ)
- `apply()` возвращает `(patched_code: str, metadata: dict)`
- metadata обязана содержать `diff_lines: int`
- `suppoted_detectors` связывает паттерн с детекторами
- Zero external dependencies (только ast/stdlib)
- Идемпотентность: повторный вызов `can_apply()` после `apply()` → False
