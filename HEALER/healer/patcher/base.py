from __future__ import annotations

from abc import ABC, abstractmethod

from healer.diagnostics.report import DiagnosticReport
from healer.patcher.result import PatchResult


class BasePatcher(ABC):
    language: str = ""

    @abstractmethod
    def patch(self, source_code: str, report: DiagnosticReport, source_path: str = "") -> PatchResult:
        ...

    def patch_file(self, filepath: str, report: DiagnosticReport) -> PatchResult:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        return self.patch(source, report, source_path=filepath)

    @abstractmethod
    def get_supported_patterns(self) -> list[str]:
        ...

    def get_supported_detectors(self) -> list[str]:
        return []
