"""JSSourceDetector — анализирует JS/TS исходный код без трейсов.

Работает на regex (нет AST в stdlib для JS).
Находит: отсутствующие timeout в fetch, try/catch, утечки ресурсов.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.diagnostics.base import BaseDetector


FETCH_WITHOUT_TIMEOUT = re.compile(
    r'fetch\s*\([^)]*\)(?!\s*[;,]?\s*\.\s*then)',
)
FETCH_WITH_TIMEOUT = re.compile(r'timeout', re.IGNORECASE)

CONSOLE_LOG = re.compile(r'console\.(log|warn|error|debug)\s*\(')
NO_TRY_CATCH = re.compile(
    r'(async\s+)?function\s+\w+\s*\([^)]*\)\s*\{(?:(?!try|catch)[^}])*\}'
)
SET_INTERVAL_NO_CLEAR = re.compile(r'setInterval\s*\(')

ADD_EVENT_LISTENER = re.compile(r'\.addEventListener\s*\(')
REMOVE_EVENT_LISTENER = re.compile(r'\.removeEventListener\s*\(')

_UNSAFE_GLOBALS = {"innerHTML", "outerHTML", "eval(", "setTimeout(", "document.write"}


class JSSourceDetector(BaseDetector):
    """Ищет проблемы в JS/TS исходном коде проекта."""

    def __init__(self, project_path: str | None = None):
        self.project_path = project_path

    def detect(self) -> list[DiagnosticReport]:
        reports: list[DiagnosticReport] = []

        base = self.project_path or _find_nearest_package()
        if not base:
            return reports

        js_files = _find_js_files(base)
        for filepath in js_files:
            try:
                source = filepath.read_text("utf-8", errors="replace")
            except (OSError, UnicodeDecodeError):
                continue

            rel = str(filepath.relative_to(base)) if base else str(filepath)

            reports.extend(_check_fetch_timeout(source, rel, filepath))
            reports.extend(_check_console_left(source, rel, filepath))
            reports.extend(_check_missing_try_catch(source, rel, filepath))
            reports.extend(_check_interval_cleanup(source, rel, filepath))
            reports.extend(_check_event_listener_cleanup(source, rel, filepath))
            reports.extend(_check_unsafe_globals(source, rel, filepath))

        return reports


def _find_nearest_package() -> str | None:
    """Ищет package.json от текущей директории вверх."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        pkg = parent / "package.json"
        if pkg.exists():
            return str(parent)
    return None


def _find_js_files(base: str) -> list[Path]:
    """Ищет .js, .jsx, .ts, .tsx файлы, исключая node_modules и .git.

    Использует os.walk с dirnames[:] = ... чтобы node_modules не обходился.
    """
    root = Path(base)
    extensions = {".js", ".jsx", ".ts", ".tsx"}
    excluded = {"node_modules", ".git", "__pycache__", "bower_components",
                ".next", ".nuxt", "dist", "build", ".cache"}
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in excluded]
        for fname in filenames:
            if Path(fname).suffix in extensions:
                files.append(Path(dirpath) / fname)
    return files


def _check_fetch_timeout(source: str, relpath: str, filepath: Path) -> list[DiagnosticReport]:
    reports: list[DiagnosticReport] = []
    for match in FETCH_WITHOUT_TIMEOUT.finditer(source):
        call = match.group(0)
        if FETCH_WITH_TIMEOUT.search(call):
            continue
        line = source[:match.start()].count("\n") + 1
        reports.append(DiagnosticReport(
            severity=ReportSeverity.WARNING,
            category=ReportCategory.PERFORMANCE,
            detector="JSSourceDetector",
            location=f"{relpath}:{line}",
            message=f"fetch() без timeout: {call[:60]}",
            recommendation="Добавить AbortSignal.timeout(30000)",
            details={"file": str(filepath), "line": line, "pattern": "fetch_no_timeout"},
        ))
    return reports


def _check_console_left(source: str, relpath: str, filepath: Path) -> list[DiagnosticReport]:
    reports: list[DiagnosticReport] = []
    for match in CONSOLE_LOG.finditer(source):
        line = source[:match.start()].count("\n") + 1
        reports.append(DiagnosticReport(
            severity=ReportSeverity.INFO,
            category=ReportCategory.MAINTAINABILITY,
            detector="JSSourceDetector",
            location=f"{relpath}:{line}",
            message=f"console.{match.group(1)} оставлен в коде: {match.group(0)[:50]}",
            recommendation="Удалить или заменить на логгер",
            details={"file": str(filepath), "line": line, "pattern": "console_log"},
        ))
    return reports


def _check_missing_try_catch(source: str, relpath: str, filepath: Path) -> list[DiagnosticReport]:
    reports: list[DiagnosticReport] = []
    for match in NO_TRY_CATCH.finditer(source):
        func = match.group(0)[:80]
        if len(func.strip()) < 30:
            continue
        line = source[:match.start()].count("\n") + 1
        reports.append(DiagnosticReport(
            severity=ReportSeverity.WARNING,
            category=ReportCategory.CORRECTNESS,
            detector="JSSourceDetector",
            location=f"{relpath}:{line}",
            message=f"Функция без try/catch: {func[:50]}",
            recommendation="Обернуть тело в try/catch",
            details={"file": str(filepath), "line": line, "pattern": "no_try_catch"},
        ))
    return reports


def _check_interval_cleanup(source: str, relpath: str, filepath: Path) -> list[DiagnosticReport]:
    reports: list[DiagnosticReport] = []
    for match in SET_INTERVAL_NO_CLEAR.finditer(source):
        line = source[:match.start()].count("\n") + 1
        if "clearInterval" not in source:
            reports.append(DiagnosticReport(
                severity=ReportSeverity.WARNING,
                category=ReportCategory.RESOURCE,
                detector="JSSourceDetector",
                location=f"{relpath}:{line}",
                message=f"setInterval без clearInterval: утечка таймера",
                recommendation="Сохранить ID и вызвать clearInterval() при размонтировании",
                details={"file": str(filepath), "line": line, "pattern": "interval_no_cleanup"},
            ))
    return reports


def _check_event_listener_cleanup(source: str, relpath: str, filepath: Path) -> list[DiagnosticReport]:
    reports: list[DiagnosticReport] = []
    add_count = len(ADD_EVENT_LISTENER.findall(source))
    remove_count = len(REMOVE_EVENT_LISTENER.findall(source))
    if add_count > remove_count + 2:
        reports.append(DiagnosticReport(
            severity=ReportSeverity.WARNING,
            category=ReportCategory.RESOURCE,
            detector="JSSourceDetector",
            location=relpath,
            message=f"addEventListener ({add_count}) > removeEventListener ({remove_count}): утечка",
            recommendation="Добавить removeEventListener в cleanup",
            details={"file": str(filepath), "add_count": add_count, "remove_count": remove_count, "pattern": "listener_leak"},
        ))
    return reports


def _check_unsafe_globals(source: str, relpath: str, filepath: Path) -> list[DiagnosticReport]:
    reports: list[DiagnosticReport] = []
    for pattern in _UNSAFE_GLOBALS:
        idx = source.find(pattern)
        if idx == -1:
            continue
        line = source[:idx].count("\n") + 1
        reports.append(DiagnosticReport(
            severity=ReportSeverity.WARNING,
            category=ReportCategory.SECURITY,
            detector="JSSourceDetector",
            location=f"{relpath}:{line}",
            message=f"Использование {pattern}: риск XSS/безопасности",
            recommendation="Использовать textContent вместо innerHTML, избегать eval",
            details={"file": str(filepath), "line": line, "pattern": "unsafe_global"},
        ))
    return reports
