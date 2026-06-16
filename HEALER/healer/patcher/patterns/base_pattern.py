"""BasePattern — абстрактный контракт для всех паттернов."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from healer.diagnostics.report import DiagnosticReport


class BasePattern(ABC):
    """Абстрактный базовый класс для AST-паттернов HEALER.

    Все паттерны должны наследовать BasePattern и реализовывать:
      - can_apply(source_code, report) -> bool
      - apply(source_code, report) -> (patched_code, metadata)
    """

    name: str = ""
    description: str = ""
    supported_detectors: list[str] = []

    @abstractmethod
    def can_apply(self, source_code: str, report: DiagnosticReport) -> bool:
        """Проверить, применим ли паттерн к данному коду."""
        ...

    @abstractmethod
    def apply(self, source_code: str, report: DiagnosticReport) -> tuple[str, dict[str, Any]]:
        """Применить паттерн. Возвращает (patched_code, metadata).

        metadata должна содержать 'diff_lines' — количество изменённых строк.
        """
        ...
