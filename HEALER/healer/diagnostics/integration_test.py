"""Интеграционный тест: генерирует синтетические трейсы с известными
проблемами, прогоняет все детекторы и проверяет, что проблемы найдены.

Запуск:
    python -m healer.diagnostics.integration_test
    python -m healer.diagnostics.integration_test --verbose

Это НЕ unit-тесты. Это проверка на реальных данных.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # fmt: skip

from aethon.xray import store, start_trace, start_span, SpanKind
from aethon.xray.trace import Trace
from aethon.xray.span import Span


# ── Синтетические сценарии с известными проблемами ──────────

def make_slow_imports() -> str:
    """Создаёт трейс с медленными импортами."""
    trace_id = "synth_slow_import"
    trace = Trace(
        trace_id=trace_id, name="test.slow_import",
        started_at=time.time(), status="ok",
    )
    for i in range(3):
        span = Span(
            span_id=f"import_{i}", trace_id=trace_id,
            kind="import", name=f"import.heavy_module_{i}",
            started_at=time.time() - (3 - i) * 0.5,
            ended_at=time.time() - (3 - i) * 0.5 + 0.2,
            duration_ms=200.0 + i * 100,
            status="ok",
        )
        trace.spans.append(span)
    trace.ended_at = time.time()
    trace.duration_ms = 1500.0
    store._completed[trace_id] = trace
    store._persist_trace_snapshot(trace)
    return trace_id


def make_error_without_fallback() -> str:
    """Создаёт трейс с ошибкой без fallback — ErrorPathDetector."""
    trace_id = "synth_no_fallback"
    trace = Trace(
        trace_id=trace_id, name="test.no_fallback",
        started_at=time.time(), status="error",
    )
    span = Span(
        span_id="err_primary", trace_id=trace_id,
        kind="provider_call", name="openai.request",
        started_at=time.time() - 1,
        ended_at=time.time() - 0.5,
        duration_ms=500.0,
        status="error",
    )
    trace.spans.append(span)
    trace.ended_at = time.time()
    trace.duration_ms = 1000.0
    store._completed[trace_id] = trace
    store._persist_trace_snapshot(trace)
    return trace_id


def make_unended_span() -> str:
    """Создаёт активный трейс с незавершённым span — ResourceLeak."""
    trace_id = "synth_unended"
    trace = Trace(
        trace_id=trace_id, name="test.unended_span",
        started_at=time.time() - 60,
        status="active",
    )
    span = Span(
        span_id="open_conn", trace_id=trace_id,
        kind="provider_call", name="db.connection",
        started_at=time.time() - 55,
        ended_at=None,
        status="ok",
    )
    trace.spans.append(span)
    store._active[trace_id] = trace
    return trace_id


def make_deep_trace() -> str:
    """Создаёт трейс с глубиной > 10 — SpanAnalyzer."""
    trace_id = "synth_deep"
    trace = Trace(
        trace_id=trace_id, name="test.deep_trace",
        started_at=time.time(), status="ok",
    )
    for i in range(15):
        parent = f"deep_{i - 1}" if i > 0 else None
        span = Span(
            span_id=f"deep_{i}", trace_id=trace_id,
            kind="custom", name=f"nested.call.{i}",
            started_at=time.time() - (15 - i) * 0.01,
            ended_at=time.time() - (15 - i) * 0.01 + 0.005,
            duration_ms=5.0,
            status="ok",
            parent_span_id=parent,
            depth=i,
            logical_ts=i,
        )
        trace.spans.append(span)
    trace.ended_at = time.time()
    trace.duration_ms = 150.0
    store._completed[trace_id] = trace
    store._persist_trace_snapshot(trace)
    return trace_id


def make_duplicate_span_id() -> str:
    """Создаёт трейс с дубликатом span_id."""
    trace_id = "synth_dup_span"
    trace = Trace(
        trace_id=trace_id, name="test.duplicate_span",
        started_at=time.time(), status="ok",
    )
    for i in range(3):
        span = Span(
            span_id="DUPLICATE_ID", trace_id=trace_id,
            kind="custom", name=f"dup_{i}",
            started_at=time.time() - (3 - i) * 0.01,
            ended_at=time.time() - (3 - i) * 0.01 + 0.005,
            duration_ms=5.0,
            status="ok",
        )
        trace.spans.append(span)
    trace.ended_at = time.time()
    trace.duration_ms = 30.0
    store._completed[trace_id] = trace
    store._persist_trace_snapshot(trace)
    return trace_id


def make_missing_parent() -> str:
    """Создаёт трейс со span, ссылающимся на несуществующий parent."""
    trace_id = "synth_missing_parent"
    trace = Trace(
        trace_id=trace_id, name="test.missing_parent",
        started_at=time.time(), status="ok",
    )
    span = Span(
        span_id="orphan_child", trace_id=trace_id,
        kind="custom", name="orphan.child",
        started_at=time.time() - 0.1,
        ended_at=time.time(),
        duration_ms=100.0,
        status="ok",
        parent_span_id="nonexistent_parent",
    )
    trace.spans.append(span)
    trace.ended_at = time.time()
    trace.duration_ms = 200.0
    store._completed[trace_id] = trace
    store._persist_trace_snapshot(trace)
    return trace_id


def make_latency_outlier() -> str:
    """Создаёт трейсы с равномерной латентностью и один выброс."""
    base_time = time.time()
    for i in range(10):
        tid = f"synth_latency_normal_{i}"
        trace = Trace(
            trace_id=tid, name="test.latency_normal",
            started_at=base_time - 10 + i,
            status="ok",
        )
        span = Span(
            span_id=f"norm_{i}", trace_id=tid,
            kind="provider_call", name="normal.api",
            started_at=base_time - 10 + i,
            ended_at=base_time - 10 + i + 0.05,
            duration_ms=50.0,
            status="ok",
        )
        trace.spans.append(span)
        trace.ended_at = base_time - 10 + i + 0.05
        trace.duration_ms = 50.0
        store._completed[tid] = trace
        store._persist_trace_snapshot(trace)

    tid = "synth_latency_outlier"
    trace = Trace(
        trace_id=tid, name="test.latency_outlier",
        started_at=base_time, status="ok",
    )
    span = Span(
        span_id="slow_api", trace_id=tid,
        kind="provider_call", name="slow.api",
        started_at=base_time,
        ended_at=base_time + 5,
        duration_ms=5000.0,
        status="ok",
    )
    trace.spans.append(span)
    trace.ended_at = base_time + 5
    trace.duration_ms = 5000.0
    store._completed[tid] = trace
    store._persist_trace_snapshot(trace)
    return tid


def make_causal_violation() -> str:
    """Создаёт трейс с child до parent (нарушение времени)."""
    trace_id = "synth_causal_bad"
    now = time.time()
    trace = Trace(
        trace_id=trace_id, name="test.causal_violation",
        started_at=now, status="ok",
    )
    child = Span(
        span_id="child_first", trace_id=trace_id,
        kind="custom", name="child.span",
        started_at=now - 1.0,
        ended_at=now - 0.5,
        duration_ms=500.0,
        status="ok",
        parent_span_id="parent_later",
        logical_ts=2, depth=1,
    )
    parent = Span(
        span_id="parent_later", trace_id=trace_id,
        kind="custom", name="parent.span",
        started_at=now,
        ended_at=now + 0.5,
        duration_ms=500.0,
        status="ok",
        logical_ts=1, depth=0,
    )
    trace.spans = [parent, child]
    trace.ended_at = now + 0.5
    trace.duration_ms = 1500.0
    store._completed[trace_id] = trace
    store._persist_trace_snapshot(trace)
    return trace_id


# ── Сценарии, которые НЕ должны давать отчётов ─────────────

def make_clean_trace() -> str:
    """Идеальный трейс — никаких проблем."""
    trace_id = "synth_clean"
    trace = Trace(
        trace_id=trace_id, name="test.clean",
        started_at=time.time(), status="ok",
    )
    for i in range(5):
        parent = f"clean_{i - 1}" if i > 0 else None
        span = Span(
            span_id=f"clean_{i}", trace_id=trace_id,
            kind="custom", name=f"clean.step.{i}",
            started_at=time.time() - (5 - i) * 0.01,
            ended_at=time.time() - (5 - i) * 0.01 + 0.005,
            duration_ms=5.0,
            status="ok",
            parent_span_id=parent,
            depth=i,
            logical_ts=i,
        )
        trace.spans.append(span)
    trace.ended_at = time.time()
    trace.duration_ms = 50.0
    store._completed[trace_id] = trace
    store._persist_trace_snapshot(trace)
    return trace_id


# Маппинг: short_name → полное имя детектора (как в отчёте)
DETECTOR_NAMES = {
    "slow_import": "SlowImportDetector",
    "error_path": "ErrorPathDetector",
    "span_analyzer": "SpanAnalyzer",
    "resource_leak": "ResourceLeakDetector",
    "causal_violation": "CausalViolationDetector",
    "latency_anomaly": "LatencyAnomalyDetector",
    "dead_code": "DeadCodeDetector",
}

SCENARIOS_WITH_ISSUES = {
    "slow_import": (make_slow_imports, ["slow_import"]),
    "error_no_fallback": (make_error_without_fallback, ["error_path"]),
    "unended_span": (make_unended_span, ["resource_leak", "span_analyzer"]),
    "deep_trace": (make_deep_trace, ["span_analyzer"]),
    "duplicate_span_id": (make_duplicate_span_id, ["span_analyzer"]),
    "missing_parent": (make_missing_parent, ["span_analyzer"]),
    "latency_outlier": (make_latency_outlier, ["latency_anomaly"]),
    "causal_violation": (make_causal_violation, ["causal_violation"]),
}

CLEAN_SCENARIOS = {
    "clean_trace": (make_clean_trace, []),
}


def run_integration_test(verbose: bool = False) -> list[dict[str, Any]]:
    """Полный интеграционный тест на синтетических данных."""
    from healer.diagnostics.span_analyzer import SpanAnalyzer
    from healer.diagnostics.slow_import import SlowImportDetector
    from healer.diagnostics.error_path import ErrorPathDetector
    from healer.diagnostics.resource_leak import ResourceLeakDetector
    from healer.diagnostics.causal_violation import CausalViolationDetector
    from healer.diagnostics.latency_anomaly import LatencyAnomalyDetector
    from healer.diagnostics.dead_code import DeadCodeDetector
    from healer.diagnostics.report import ReportSeverity, ReportCategory

    results: list[dict[str, Any]] = []

    def _check(tid: str, expected_detectors: list[str], scenario_name: str, tmpdir: str) -> dict:
        from healer.diagnostics.runner import run_diagnostics, filter_reports

        all_reports = run_diagnostics()
        reports = filter_reports(all_reports, "info")

        full_names = {DETECTOR_NAMES.get(d, d).lower() for d in expected_detectors}
        actual_detectors = {r["detector"].lower() for r in reports}

        found = [d for d in expected_detectors if DETECTOR_NAMES.get(d, d).lower() in actual_detectors]
        missed = [d for d in expected_detectors if DETECTOR_NAMES.get(d, d).lower() not in actual_detectors]

        result = {
            "scenario": scenario_name,
            "trace_id": tid,
            "expected_detectors": expected_detectors,
            "found_detectors": found,
            "missed_detectors": missed,
            "report_count": len(reports),
            "passed": len(missed) == 0,
        }

        if verbose:
            print(f"\n  [{scenario_name}] {tid}")
            print(f"    Ожидалось: {expected_detectors}")
            print(f"    Найдено:   {found}")
            print(f"    Пропущено: {missed}")
            print(f"    Отчётов:   {len(reports)}")
            for r in reports:
                print(f"      [{r['detector']}] {r['message'][:80]}")
            print(f"    Статус:    {'ПРОЙДЕН' if result['passed'] else 'ПРОВАЛЕН'}")

        return result

    for name, (fn, expected) in SCENARIOS_WITH_ISSUES.items():
        with tempfile.TemporaryDirectory(prefix="healer_int_") as tmpdir:
            store.clear()
            store.configure_persistence(tmpdir)
            tid = fn()
            result = _check(tid, expected, name, tmpdir)
            results.append(result)

    for name, (fn, expected) in CLEAN_SCENARIOS.items():
        with tempfile.TemporaryDirectory(prefix="healer_int_") as tmpdir:
            store.clear()
            store.configure_persistence(tmpdir)
            tid = fn()
            result = _check(tid, expected, name, tmpdir)
            results.append(result)

    return results


def print_summary(results: list[dict]) -> None:
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    total = len(results)

    print(f"\n{'='*60}")
    print(f"  ИНТЕГРАЦИОННЫЙ ТЕСТ HEALER")
    print(f"{'='*60}")

    for r in results:
        icon = "✅" if r["passed"] else "❌"
        status = "ПРОЙДЕН" if r["passed"] else "ПРОВАЛЕН"
        print(f"\n  {icon} [{status}] {r['scenario']}")
        print(f"      trace: {r['trace_id']}")
        print(f"      ожидалось: {r['expected_detectors']}")
        print(f"      найдено:   {r['found_detectors']}")
        if r["missed_detectors"]:
            print(f"      ❌ ПРОПУЩЕНО: {r['missed_detectors']}")

    print(f"\n  ─────────────────────────────")
    print(f"  Всего: {total}")
    print(f"  ✅ Пройдено: {passed}")
    if failed:
        print(f"  ❌ Провалено: {failed}")
    print(f"  {'' if failed else '🎯'} Результат: {'ВСЁ ОК' if failed == 0 else 'ЕСТЬ ПРОБЛЕМЫ'}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HEALER Integration Test — проверка детекторов на синтетических данных",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")
    parser.add_argument("--json", "-j", action="store_true", help="Вывод в JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    results = run_integration_test(verbose=args.verbose)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_summary(results)

    failed = sum(1 for r in results if not r["passed"])
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
