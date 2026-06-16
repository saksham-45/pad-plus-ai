# Интеграция HEALER Viewer с HEALER

## Как viewer находит HEALER

В `viewer.py`:
```python
HEALER_DIR = Path(__file__).parent.parent / "HEALER"
```

Путь: `../HEALER/` относительно папки `healer-viewer/`.

Если HEALER в другой папке — поправить эту строку.

## Как viewer использует HEALER

### 1. X-RAY ядро

```python
from aethon.xray import start_trace, start_span, SpanKind, store
```

Viewer использует X-RAY ядро HEALER для трейсинга своих запросов.

### 2. Диагностика

```python
from aethon.xray.trace_store import store
store.clear()
store.configure_persistence(target_path)

from healer.diagnostics.runner import run_diagnostics
reports = run_diagnostics()
```

Viewer загружает data HEALER (или свои данные) и запускает все 7 детекторов.

### 3. Патчинг

```python
from healer.diagnostics.report import DiagnosticReport
from healer.patcher.python_patcher import PythonPatcher

report = DiagnosticReport(detector="SpanAnalyzer", ...)
result = PythonPatcher().patch_file("viewer.py", report)
```

### 4. Сохранение/откат

```python
from healer.patcher.result import PatchResult
result.apply(backup=True)     # создаёт *.healer.bak
result.rollback()             # восстанавливает из бэкапа
```

## Как HEALER диагностирует viewer

HEALER запускается с `--path` указывающим на трейсы viewer:

```bash
cd HEALER
python -m healer.diagnostics.runner --path ../healer-viewer/data/trace_store
```

Viewer эмулирует это через прямой вызов:
1. `store.clear()` — очищает кэш
2. `store.configure_persistence(target_path)` — загружает данные viewer
3. `run_diagnostics()` — запускает все детекторы

## Self-healing cycle

```
1. Пользователь открывает viewer → запросы пишут трейсы в data/trace_store/
2. Пользователь нажимает "Запустить HEALER диагностику"
3. viewer вызывает run_diagnostics() на своих трейсах
4. HEALER находит проблемы (незавершённые spans, ошибки, мёртвый код...)
5. Пользователь видит отчёты и нажимает P (Patch)
6. viewer вызывает PythonPatcher().patch_file("viewer.py", report)
7. Патч генерирует diff, viewer применяет его (apply + backup)
8. Пользователь перезапускает viewer — ошибки исправлены
```

## Маппинг детекторов на паттерны

| Детектор HEALER | Паттерн PythonPatcher | Что меняет в коде |
|----------------|----------------------|-------------------|
| SpanAnalyzer | try_finally | Оборачивает тело функции в try/finally с end() |
| ErrorPathDetector | try_finally | Добавляет try/except с fallback |
| SlowImportDetector | lazy_import | Переносит import внутрь функции |
| LatencyAnomalyDetector | add_timeout | Добавляет timeout=30 к HTTP вызовам |
| DeadCodeDetector | remove_dead | Удаляет неиспользуемые импорты |
| ResourceLeakDetector | close_resource | open() → with-блок |

## Зависимости

- HEALER и viewer — независимые проекты
- viewer импортирует HEALER через sys.path
- HEALER НЕ знает о viewer
- HEALER может диагностировать viewer как любой другой проект
- Разработка HEALER не зависит от viewer
