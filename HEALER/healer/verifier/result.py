from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Verdict(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


@dataclass
class VerificationResult:
    phase: str
    verdict: Verdict
    name: str = ""
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "verdict": self.verdict.value,
            "name": self.name,
            "message": self.message,
            "details": self.details,
            "error": self.error,
        }


class PhaseVerdict:
    """Собирает результаты нескольких проверок в общий вердикт."""

    def __init__(self):
        self.results: list[VerificationResult] = []

    def add(self, result: VerificationResult):
        self.results.append(result)

    @property
    def verdict(self) -> Verdict:
        if any(r.verdict == Verdict.ERROR for r in self.results):
            return Verdict.ERROR
        if any(r.verdict == Verdict.FAILED for r in self.results):
            return Verdict.FAILED
        return Verdict.PASSED

    @property
    def summary(self) -> str:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.verdict == Verdict.PASSED)
        failed = sum(1 for r in self.results if r.verdict == Verdict.FAILED)
        errors = sum(1 for r in self.results if r.verdict == Verdict.ERROR)
        parts = [f"{passed}/{total} passed"]
        if failed:
            parts.append(f"{failed} failed")
        if errors:
            parts.append(f"{errors} errors")
        return ", ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "summary": self.summary,
            "results": [r.to_dict() for r in self.results],
        }
