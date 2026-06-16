"""AST-паттерны для Patch Engine.

Каждый паттерн — класс, наследующий BasePattern с методами:
  - can_apply(code, report) -> bool
  - apply(code, report) -> (patched_code, metadata)
"""

from healer.patcher.patterns.base_pattern import BasePattern
from healer.patcher.patterns.lazy_import_py import LazyImportPattern
from healer.patcher.patterns.try_finally_py import TryFinallyPattern
from healer.patcher.patterns.add_timeout_py import AddTimeoutPattern
from healer.patcher.patterns.remove_dead_py import RemoveDeadPattern
from healer.patcher.patterns.close_resource_py import CloseResourcePattern

ALL_PATTERNS: dict[str, BasePattern] = {
    "lazy_import": LazyImportPattern(),
    "try_finally": TryFinallyPattern(),
    "add_timeout": AddTimeoutPattern(),
    "remove_dead": RemoveDeadPattern(),
    "close_resource": CloseResourcePattern(),
}

PATTERN_DETECTOR_MAP: dict[str, list[str]] = {
    "lazy_import": ["slow_import", "slowimport"],
    "try_finally": ["error_path", "errorpath", "span_analyzer", "spananalyzer"],
    "add_timeout": ["latency_anomaly", "latencyanomaly"],
    "remove_dead": ["dead_code", "deadcode"],
    "close_resource": ["resource_leak", "resourceleak"],
}

__all__ = [
    "BasePattern",
    "LazyImportPattern",
    "TryFinallyPattern",
    "AddTimeoutPattern",
    "RemoveDeadPattern",
    "CloseResourcePattern",
    "ALL_PATTERNS",
    "PATTERN_DETECTOR_MAP",
]
