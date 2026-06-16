"""BaseDetector — абстрактный контракт для всех детекторов."""

from __future__ import annotations

from abc import ABC, abstractmethod

from healer.diagnostics.report import DiagnosticReport


class BaseDetector(ABC):
    """Абстрактный базовый класс для детекторов HEALER.

    Все детекторы должны наследовать BaseDetector и реализовывать detect().
    """

    @abstractmethod
    def detect(self) -> list[DiagnosticReport]:
        """Запустить диагностику, вернуть список проблем."""
        ...
