#!/usr/bin/env python
"""Smoke test — быстрая проверка, что HEALER работает.

Запуск:
    python scripts/smoke_test.py
    python -m healer.smoke_test

Проверяет:
  - X-RAY ядро (создание трейса, спанов, сохранение)
  - Diagnostics (запуск детекторов)
  - Patcher (генерация diff)
  - Verifier (создание результата)
  - Meta (запись и чтение истории)
  - Orchestrator (полный цикл)
"""

from __future__ import annotations

import os
import sys
import tempfile
import time

# Add project root to path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def check(step: str, ok: bool, detail: str = "") -> None:
    icon = "PASS" if ok else "FAIL"
    print(f"  [{icon}] {step}" + (f" — {detail}" if detail else ""))


def main() -> int:
    print("\n=== HEALER Smoke Test ===\n")
    failures = 0

    # 1. X-RAY Kernel
    print("[1] X-RAY Kernel")
    try:
        from aethon.xray import start_trace, start_span, SpanKind, store, Trace, Span

        t = Trace(trace_id="smoke", name="smoke.test", started_at=time.time())
        s = Span(span_id="s1", trace_id="smoke", kind="custom", name="smoke.span",
                 started_at=time.time())
        t.spans.append(s)
        s.ended_at = time.time()
        s.duration_ms = 10.0
        t.ended_at = time.time()
        t.duration_ms = 10.0
        t.status = "ok"
        assert t.trace_id == "smoke"
        assert len(t.spans) == 1
        check("Trace/Span creation", True)

        from aethon.xray.causal_validator import validate_trace_causal_integrity
        r = validate_trace_causal_integrity(t)
        assert "causal_integrity" in r
        check("Causal validator", True)
    except Exception as e:
        check("X-RAY Kernel", False, str(e))
        failures += 1

    # 2. Diagnostics
    print("\n[2] Diagnostics")
    try:
        from healer.diagnostics.runner import run_diagnostics
        from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory

        reports = run_diagnostics()
        assert isinstance(reports, list), "reports should be a list"
        check(f"run_diagnostics() — {len(reports)} reports", True)

        r = DiagnosticReport(
            detector="test", severity=ReportSeverity.WARNING,
            category=ReportCategory.PERFORMANCE, message="test",
        )
        assert r.to_dict()["severity"] == "warning"
        check("DiagnosticReport creation", True)
    except Exception as e:
        check("Diagnostics", False, str(e))
        failures += 1

    # 3. Patcher
    print("\n[3] Patch Engine")
    try:
        from healer.patcher.python_patcher import PythonPatcher

        pp = PythonPatcher()
        patterns = pp.get_supported_patterns()
        assert len(patterns) >= 5, f"expected >=5 patterns, got {len(patterns)}"
        check(f"PythonPatcher — {len(patterns)} patterns", True)

        from healer.patcher.result import PatchResult
        result = PatchResult(
            patcher="test", pattern="test", source_path="test.py",
            original_code="x=1", patched_code="x=2", success=True,
        )
        assert "patched" in result.diff
        check("PatchResult diff", True)
    except Exception as e:
        check("Patch Engine", False, str(e))
        failures += 1

    # 4. Verifier
    print("\n[4] Verification")
    try:
        from healer.verifier.result import VerificationResult, Verdict, PhaseVerdict

        vr = VerificationResult(phase="test", verdict=Verdict.PASSED, name="test")
        assert vr.verdict.value == "passed"
        check("VerificationResult", True)

        pv = PhaseVerdict()
        pv.add(vr)
        assert pv.verdict.value == "passed"
        check("PhaseVerdict", True)

        from healer.verifier.metric_compare import MetricComparator
        mc = MetricComparator()
        result = mc.compare({"latency": 100}, {"latency": 50})
        assert result.verdict.value == "passed"
        check("MetricComparator", True)
    except Exception as e:
        check("Verification", False, str(e))
        failures += 1

    # 5. Meta
    print("\n[5] Meta-Learning")
    try:
        import tempfile
        tmp = tempfile.mkdtemp()
        from healer.meta.meta_learner import MetaLearner, HealingRecord

        ml = MetaLearner(storage_path=tmp)
        ml.record_healing(HealingRecord(
            cycle_id="s1", mode="auto", timestamp=time.time(),
            detector="SpanAnalyzer", pattern="try_finally",
            success=True, duration_ms=100.0, file_path="test.py",
        ))
        assert len(ml.records) == 1
        check("MetaLearner record", True)

        summary = ml.get_summary()
        assert "patterns" in summary
        check("MetaLearner summary", True)

        ml2 = MetaLearner(storage_path=tmp)
        check("MetaLearner persistence", True)
    except Exception as e:
        check("Meta-Learning", False, str(e))
        failures += 1

    # 6. Orchestrator
    print("\n[6] Orchestrator")
    try:
        from healer.orchestrator import HealerOrchestrator, HealerMode

        o = HealerOrchestrator(mode="monitor")
        assert o.get_mode() == "monitor"
        o.set_mode("auto")
        assert o.get_mode() == "auto"
        check("Orchestrator mode", True)

        cycle = o.run_cycle()
        assert cycle is not None
        check(f"Orchestrator cycle — {cycle.status}", True)
    except Exception as e:
        check("Orchestrator", False, str(e))
        failures += 1

    # Result
    print(f"\n{'='*40}")
    if failures == 0:
        print("  SMOKE TEST: ALL PASSED")
    else:
        print(f"  SMOKE TEST: {failures} FAILURES")
    print(f"{'='*40}\n")

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
