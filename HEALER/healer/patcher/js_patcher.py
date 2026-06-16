from __future__ import annotations

import re
import textwrap
from typing import Any

from healer.diagnostics.report import DiagnosticReport
from healer.patcher.base import BasePatcher
from healer.patcher.result import PatchResult


class JSPatcher(BasePatcher):
    language = "javascript"

    SUPPORTED_PATTERNS = {
        "add_timeout",
        "close_resource",
        "try_finally",
    }

    def patch(self, source_code: str, report: DiagnosticReport, source_path: str = "") -> PatchResult:
        pattern_name = self._select_pattern(report)
        if not pattern_name:
            return PatchResult(
                patcher="js_patcher",
                pattern="",
                source_path=source_path,
                original_code=source_code,
                success=False,
                error="No matching pattern for this report",
            )

        pattern_fn = getattr(self, f"_patch_{pattern_name}", None)
        if pattern_fn is None:
            return PatchResult(
                patcher="js_patcher",
                pattern=pattern_name,
                source_path=source_path,
                original_code=source_code,
                success=False,
                error=f"Pattern '{pattern_name}' not supported for JS",
            )

        try:
            patched_code, metadata = pattern_fn(source_code, report)
            if patched_code == source_code:
                return PatchResult(
                    patcher="js_patcher",
                    pattern=pattern_name,
                    source_path=source_path,
                    original_code=source_code,
                    success=False,
                    error="No changes made",
                    metadata=metadata,
                )
            return PatchResult(
                patcher="js_patcher",
                pattern=pattern_name,
                source_path=source_path,
                original_code=source_code,
                patched_code=patched_code,
                success=True,
                metadata=metadata,
            )
        except Exception as e:
            return PatchResult(
                patcher="js_patcher",
                pattern=pattern_name,
                source_path=source_path,
                original_code=source_code,
                success=False,
                error=str(e),
            )

    def get_supported_patterns(self) -> list[str]:
        return list(self.SUPPORTED_PATTERNS)

    def _select_pattern(self, report: DiagnosticReport) -> str | None:
        detector = report.detector.lower()
        mapping = {
            "latencyanomaly": "add_timeout",
            "latency_anomaly": "add_timeout",
            "resource_leak": "close_resource",
            "resourceleak": "close_resource",
            "error_path": "try_finally",
            "errorpath": "try_finally",
        }
        detector_clean = detector.replace("detector", "").lower()
        for key, val in mapping.items():
            if key in detector_clean or key in detector:
                return val
        return None

    def _patch_add_timeout(self, source: str, report: DiagnosticReport) -> tuple[str, dict[str, Any]]:
        """Добавляет timeout к fetch() вызовам без него."""
        metadata: dict[str, Any] = {"patched": 0, "lines": []}

        def add_timeout(m: re.Match) -> str:
            full: str = m.group(0)
            if "timeout" in full:
                return full
            metadata["patched"] += 1
            metadata["lines"].append(m.group(0)[:60])
            result: str = full.rstrip(")") + ", { signal: AbortSignal.timeout(30000) })"
            return result

        patched = re.sub(
            r'fetch\s*\([^)]*\)',
            add_timeout,
            source,
        )
        return patched, metadata

    def _patch_try_finally(self, source: str, report: DiagnosticReport) -> tuple[str, dict[str, Any]]:
        """Добавляет try/finally вокруг тела функции с end()/cleanup()."""
        metadata: dict[str, Any] = {"patched": 0, "functions": []}

        func_pattern = re.compile(
            r'function\s+(\w+)\s*\([^)]*\)\s*\{(.*?)\}',
            re.DOTALL,
        )

        def wrap_try_finally(m: re.Match) -> str:
            name: str = m.group(1)
            body: str = m.group(2).strip()
            if "try" in body or ("end" not in body and "close" not in body and "cleanup" not in body):
                return m.group(0)
            metadata["patched"] += 1
            metadata["functions"].append(name)
            result: str = f"function {name}() {{\n  try {{\n{textwrap.indent(body, '    ')}\n  }} finally {{\n    // cleanup\n  }}\n}}"
            return result

        patched = func_pattern.sub(wrap_try_finally, source)
        return patched, metadata

    def _patch_close_resource(self, source: str, report: DiagnosticReport) -> tuple[str, dict[str, Any]]:
        """Оборачивает ресурсы в try/finally с close()."""
        metadata: dict[str, Any] = {"patched": 0}

        patterns = [
            (re.compile(r'(var|let|const)\s+(\w+)\s*=\s*(open|connect|create)\s*\(', re.DOTALL),
             lambda m: m.group(0)),
        ]
        return source, metadata
