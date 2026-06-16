from __future__ import annotations

import ast
from typing import Any

from healer.diagnostics.report import DiagnosticReport
from healer.patcher.base import BasePatcher
from healer.patcher.result import PatchResult
from healer.patcher.patterns import ALL_PATTERNS, PATTERN_DETECTOR_MAP
from healer.patcher.patterns.base_pattern import BasePattern


class PythonPatcher(BasePatcher):
    language = "python"

    SUPPORTED_PATTERNS = {
        "lazy_import",
        "try_finally",
        "add_timeout",
        "remove_dead",
        "close_resource",
    }

    PATTERN_NAMES = {
        "SlowImportDetector": "lazy_import",
        "slow_import": "lazy_import",
        "ErrorPathDetector": "try_finally",
        "error_path": "try_finally",
        "LatencyAnomalyDetector": "add_timeout",
        "latency_anomaly": "add_timeout",
        "DeadCodeDetector": "remove_dead",
        "dead_code": "remove_dead",
        "ResourceLeakDetector": "close_resource",
        "resource_leak": "close_resource",
        "SpanAnalyzer": "try_finally",
        "span_analyzer": "try_finally",
    }

    def patch(self, source_code: str, report: DiagnosticReport, source_path: str = "") -> PatchResult:
        pattern_name = self._select_pattern(report)
        if not pattern_name:
            return PatchResult(
                patcher="python_patcher",
                pattern="",
                source_path=source_path,
                original_code=source_code,
                success=False,
                error="No matching pattern for this report",
            )

        pattern = ALL_PATTERNS.get(pattern_name)
        if pattern is None:
            return PatchResult(
                patcher="python_patcher",
                pattern=pattern_name,
                source_path=source_path,
                original_code=source_code,
                success=False,
                error=f"Pattern '{pattern_name}' not found",
            )

        if not isinstance(pattern, BasePattern):
            return PatchResult(
                patcher="python_patcher",
                pattern=pattern_name,
                source_path=source_path,
                original_code=source_code,
                success=False,
                error=f"Pattern '{pattern_name}' is not a BasePattern instance",
            )

        if not pattern.can_apply(source_code, report):
            return PatchResult(
                patcher="python_patcher",
                pattern=pattern_name,
                source_path=source_path,
                original_code=source_code,
                success=False,
                error="Pattern cannot be applied (preconditions not met)",
            )

        try:
            patched_code, metadata = pattern.apply(source_code, report)

            if patched_code == source_code:
                return PatchResult(
                    patcher="python_patcher",
                    pattern=pattern_name,
                    source_path=source_path,
                    original_code=source_code,
                    patched_code=None,
                    success=False,
                    error="No changes made",
                    metadata=metadata,
                )

            return PatchResult(
                patcher="python_patcher",
                pattern=pattern_name,
                source_path=source_path,
                original_code=source_code,
                patched_code=patched_code,
                success=True,
                metadata=metadata,
            )
        except SyntaxError as e:
            return PatchResult(
                patcher="python_patcher",
                pattern=pattern_name,
                source_path=source_path,
                original_code=source_code,
                success=False,
                error=f"Syntax error: {e}",
            )
        except Exception as e:
            return PatchResult(
                patcher="python_patcher",
                pattern=pattern_name,
                source_path=source_path,
                original_code=source_code,
                success=False,
                error=str(e),
            )

    def get_supported_patterns(self) -> list[str]:
        return list(self.SUPPORTED_PATTERNS)

    def get_supported_detectors(self) -> list[str]:
        return list(self.PATTERN_NAMES.keys())

    def _select_pattern(self, report: DiagnosticReport) -> str | None:
        detector = report.detector
        pattern = self.PATTERN_NAMES.get(detector)
        if pattern:
            return pattern
        for pat, detectors in PATTERN_DETECTOR_MAP.items():
            for d in detectors:
                if d.lower() in detector.lower():
                    return pat
        return None

    def patch_file(self, filepath: str, report: DiagnosticReport) -> PatchResult:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        return self.patch(source, report, source_path=filepath)
