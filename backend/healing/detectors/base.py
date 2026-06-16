"""
База для всех детекторов самовосстановления.
"""

from abc import ABC, abstractmethod
from typing import List

from healing.report import DiagnosticReport


class BaseDetector(ABC):
    """Абстрактный детектор проблем pipeline.

    Все детекторы наследуют BaseDetector и реализуют detect().
    """

    @abstractmethod
    def detect(self) -> List[DiagnosticReport]:
        ...
