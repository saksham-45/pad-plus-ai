import os
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from aethon.xray import (
    start_trace, start_span, SpanKind, store,
    trace_to_summary, HealthMetricsDTO,
    run_all_checks, run_all_audit_checks,
    validate_trace_causal_integrity,
)

DATA_DIR = Path(__file__).parent / "data"
TRACE_STORE_PATH = DATA_DIR / "trace_store"


def setup():
    os.makedirs(TRACE_STORE_PATH, exist_ok=True)
    store.configure_persistence(str(TRACE_STORE_PATH))
    print(f"[X-RAY] Data: {TRACE_STORE_PATH}")
    print(f"[X-RAY] Mode: {store.persist_path}")


def run_test_scenario():
    print("\n=== Сценарий A: нормальный запрос ===")
    trace = start_trace("user.query", metadata={"user_id": "42", "query": "привет"})

    span_safety = start_span(SpanKind.CUSTOM, "safety.check")
    time.sleep(0.01)
    span_safety.end("ok")

    span_intent = start_span(SpanKind.CUSTOM, "intent.router", parent_span_id=span_safety.span_id)
    time.sleep(0.02)
    span_intent.end("ok")

    span_rag = start_span(SpanKind.CUSTOM, "rag.search", parent_span_id=span_intent.span_id)
    time.sleep(0.05)
    span_rag.end("ok")

    span_generate = start_span(SpanKind.CUSTOM, "generate.response", parent_span_id=span_rag.span_id)
    time.sleep(0.03)
    span_generate.end("ok")

    trace.end("ok")

    summary = trace_to_summary(trace)
    print(f"  Trace: {summary.trace_id[:12]}...")
    print(f"  Status: {summary.status}")
    print(f"  Spans: {summary.span_count}")
    print(f"  Duration: {summary.duration_ms:.1f}ms")
    print(f"  Depth: {summary.depth}")

    integrity = validate_trace_causal_integrity(trace)
    print(f"  Causal integrity: {integrity['causal_integrity']}")
    print(f"  Violations: {integrity['violation_count']}")

    return trace


def run_scenario_b_failure():
    print("\n=== Сценарий B: ошибка + fallback ===")
    trace = start_trace("provider.call", metadata={"provider": "gigachat"})

    span_primary = start_span(SpanKind.PROVIDER_CALL, "gigachat.request")
    time.sleep(0.01)
    span_primary.end("error")

    span_fallback = start_span(SpanKind.PROVIDER_CALL, "openrouter.fallback")
    time.sleep(0.02)
    span_fallback.end("ok")

    trace.end("ok")

    summary = trace_to_summary(trace)
    print(f"  Trace: {summary.trace_id[:12]}...")
    print(f"  Status: {summary.status}")
    print(f"  Spans: {summary.span_count}")
    print(f"  Has errors: {summary.has_errors}")
    print(f"  Has fallback: {summary.has_fallback}")

    return trace


def run_scenario_c_late_span():
    print("\n=== Сценарий C: late span (после freeze) ===")
    trace = start_trace("late.span.test")
    span = start_span(SpanKind.CUSTOM, "normal.span")
    time.sleep(0.01)
    span.end("ok")
    trace.end("ok")

    span_late = start_span(SpanKind.CUSTOM, "late.span")
    time.sleep(0.005)
    span_late.end("ok")

    print(f"  Late span registered: {span_late.late}")
    print(f"  Total spans: {len(trace.spans)}")

    integrity = validate_trace_causal_integrity(trace)
    print(f"  Causal integrity: {integrity['causal_integrity']}")
    print(f"  Violations: {integrity['violation_count']}")
    for v in integrity['violations']:
        print(f"    [{v['severity']}] {v['type']}: {v['detail']}")

    return trace


def run_diagnostics():
    print("\n=== Диагностика ===")
    diag = store.diagnostics()
    print(f"  Active traces: {diag['active_traces']}")
    print(f"  Completed: {diag['completed_traces']}")
    print(f"  Orphans: {diag['orphan_spans']}")
    print(f"  Integrity: {diag['trace_integrity']}")
    print(f"  Causal violations: {diag['causal_violations']}")
    print(f"  Avg latency: {diag['average_latency_ms']:.1f}ms")

    health = HealthMetricsDTO(
        active_traces=diag['active_traces'],
        completed_traces=diag['completed_traces'],
        causal_violations=diag['causal_violations'],
        average_latency_ms=diag['average_latency_ms'],
        trace_integrity=diag['trace_integrity'],
    )
    print(f"  Health: {health.to_dict()}")
    return diag


def run_audit():
    print("\n=== Аудит консистентности ===")
    try:
        result = run_all_audit_checks()
        print(f"  All passed: {result['all_passed']}")
        for name, check in result['checks'].items():
            mark = "[OK]" if check.get('passed') else "[FAIL]"
            print(f"  {mark} {name}: {check.get('status', '?')}")
    except Exception as e:
        print(f"  Audit error: {e}")


def run_healer_diagnostics():
    print("\n===🧬 ФАЗА 1: ДИАГНОСТИКА HEALER ===")

    from healer.diagnostics.span_analyzer import SpanAnalyzer
    from healer.diagnostics.slow_import import SlowImportDetector
    from healer.diagnostics.error_path import ErrorPathDetector
    from healer.diagnostics.dead_code import DeadCodeDetector
    from healer.diagnostics.resource_leak import ResourceLeakDetector
    from healer.diagnostics.causal_violation import CausalViolationDetector
    from healer.diagnostics.latency_anomaly import LatencyAnomalyDetector
    from healer.diagnostics.report import ReportSeverity, ReportCategory

    detectors = [
        ("SpanAnalyzer", SpanAnalyzer()),
        ("SlowImportDetector", SlowImportDetector()),
        ("ErrorPathDetector", ErrorPathDetector()),
        ("DeadCodeDetector", DeadCodeDetector()),
        ("ResourceLeakDetector", ResourceLeakDetector()),
        ("CausalViolationDetector", CausalViolationDetector()),
        ("LatencyAnomalyDetector", LatencyAnomalyDetector()),
    ]

    total_reports = 0
    for name, detector in detectors:
        try:
            reports = detector.detect()
            total_reports += len(reports)
            if reports:
                print(f"\n  [{name}] {len(reports)} отчётов:")
                for r in reports:
                    icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🔥"}
                    sev_icon = icon.get(r.severity.value, "📋")
                    print(f"    {sev_icon} [{r.severity.value}] {r.message[:100]}")
                    if r.recommendation:
                        print(f"       → {r.recommendation[:120]}")
            else:
                print(f"  [{name}] ✅ чисто")
        except Exception as e:
            print(f"  [{name}] ❌ ошибка: {e}")

    print(f"\n  Итого: {total_reports} диагностических отчётов")
    return total_reports


if __name__ == "__main__":
    setup()

    run_test_scenario()
    run_scenario_b_failure()
    run_scenario_c_late_span()

    run_diagnostics()
    run_audit()

    print(f"\n=== Данные на диске ===")
    trace_dir = TRACE_STORE_PATH / "traces"
    if trace_dir.exists():
        files = list(trace_dir.glob("*.json"))
        print(f"  Файлов трейсов: {len(files)}")

    run_healer_diagnostics()

    print("\n[OK] X-RAY работает. Данные сохраняются на диск.")
