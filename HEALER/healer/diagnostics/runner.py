"""CLI-раннер для диагностики HEALER на реальных данных.

Использование:
    python -m healer.diagnostics.runner
    python -m healer.diagnostics.runner --path data/trace_store --output report.json
    python -m healer.diagnostics.runner --watch --interval 30
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # fmt: skip
from pathlib import Path
from typing import Any, cast

# ── Детекторы ─────────────────────────────────────────────────
from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
from healer.diagnostics.span_analyzer import SpanAnalyzer
from healer.diagnostics.slow_import import SlowImportDetector
from healer.diagnostics.error_path import ErrorPathDetector
from healer.diagnostics.dead_code import DeadCodeDetector
from healer.diagnostics.resource_leak import ResourceLeakDetector
from healer.diagnostics.causal_violation import CausalViolationDetector
from healer.diagnostics.latency_anomaly import LatencyAnomalyDetector
from healer.diagnostics.js_source import JSSourceDetector
from healer.diagnostics.high_memory import HighMemoryDetector


DETECTORS: list[tuple[str, Any]] = [
    ("SpanAnalyzer", SpanAnalyzer()),
    ("SlowImportDetector", SlowImportDetector()),
    ("ErrorPathDetector", ErrorPathDetector()),
    ("DeadCodeDetector", DeadCodeDetector()),
    ("ResourceLeakDetector", ResourceLeakDetector()),
    ("CausalViolationDetector", CausalViolationDetector()),
    ("LatencyAnomalyDetector", LatencyAnomalyDetector()),
    ("JSSourceDetector", JSSourceDetector()),
    ("HighMemoryDetector", HighMemoryDetector()),
]

SEVERITY_ORDER = ["critical", "error", "warning", "info"]
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITY_ORDER)}

SEVERITY_ICONS = {
    "info": "ℹ️",
    "warning": "⚠️",
    "error": "❌",
    "critical": "🔥",
}


def filter_reports(reports: list[DiagnosticReport], min_severity: str) -> list[DiagnosticReport]:
    """Фильтрует отчёты по минимальному уровню severity."""
    min_rank = SEVERITY_RANK.get(min_severity, 3)
    return [r for r in reports if SEVERITY_RANK.get(r.severity.value if isinstance(r.severity, ReportSeverity) else r.severity, 3) <= min_rank]


EVENT_ICONS = {
    "diagnostics_start": "🔍",
    "detector_start": "  ▶",
    "detector_found": "    ⚡",
    "detector_done": "  ✅",
    "diagnostics_done": "📊",
}


def print_event(event: dict) -> None:
    """Печатает streaming-событие в консоль."""
    etype = event.get("type", "")
    icon = EVENT_ICONS.get(etype, "•")
    det = event.get("detector", "")
    msg = event.get("message", "")
    dur = event.get("duration_ms")
    cnt = event.get("reports_count")
    err = event.get("error")
    if etype == "diagnostics_start":
        detectors = event.get("detectors", [])
        print(f"\n  🔍 Диагностика: {len(detectors)} детекторов")
    elif etype == "detector_start":
        print(f"    ▶ {det}...")
    elif etype == "detector_found":
        r = event.get("report", {})
        sev = r.get("severity", "")
        loc = r.get("location", "")[:60]
        msg_short = (r.get("message", "") or "")[:80]
        print(f"      ⚡ [{sev}] {msg_short}")
        if loc:
            print(f"          📍 {loc}")
    elif etype == "detector_done":
        parts = [f"  ✅ {det}"]
        if cnt is not None:
            parts.append(f"{cnt} reports")
        if dur is not None:
            parts.append(f"{dur:.0f}ms")
        if err:
            parts.append(f"ERROR: {err}")
        print(f"    {' — '.join(parts)}")
    elif etype == "diagnostics_done":
        print(f"\n  📊 Всего: {event.get('total_reports', 0)} отчётов")


def load_trace_store(trace_path: str) -> None:
    """Загружает trace_store с диска в project-specific store X-RAY."""
    from aethon.xray.trace_store import store

    ts = store.get(trace_path)
    if not ts.persist_enabled:
        ts.configure_persistence(trace_path)
    store.set_active(trace_path)


def run_diagnostics(
    compat_mode: bool = False,
    event_callback: Any = None,
) -> list[DiagnosticReport] | list[dict]:
    """Запускает все детекторы, возвращает список отчётов.

    Args:
        compat_mode: если True — возвращает list[dict] (для обратной совместимости).
        event_callback: опциональный callable(event: dict) для streaming событий
                        в реальном времени. Вызывается для каждого этапа диагностики.

    События event_callback:
        diagnostics_start  — начало цикла
        detector_start     — старт детектора
        detector_found     — найден report
        detector_done      — детектор завершён
        diagnostics_done   — вся диагностика завершена
    """
    ts = time.time

    def _emit(event_type: str, **kwargs):
        if event_callback:
            event_callback({"type": event_type, "timestamp": ts(), **kwargs})

    _emit("diagnostics_start", detectors=[n for n, _ in DETECTORS])

    all_reports: list[DiagnosticReport] = []
    for name, detector in DETECTORS:
        t0 = ts()
        _emit("detector_start", detector=name)
        try:
            reports = detector.detect()
            for r in reports:
                r.detector = name
                all_reports.append(r)
                _emit("detector_found", detector=name, report=r.to_dict())
            _emit("detector_done", detector=name,
                  reports_count=len(reports), duration_ms=(ts() - t0) * 1000)
        except Exception as exc:
            all_reports.append(DiagnosticReport(
                detector=name,
                severity=ReportSeverity.ERROR,
                category=ReportCategory.MAINTAINABILITY,
                message=f"Ошибка выполнения: {exc}",
                details={"error": str(exc)},
            ))
            _emit("detector_done", detector=name,
                  reports_count=0, duration_ms=(ts() - t0) * 1000, error=str(exc))

    _emit("diagnostics_done", total_reports=len(all_reports))

    if compat_mode:
        return [r.to_dict() for r in all_reports]
    return all_reports


def print_console_report(reports: list[DiagnosticReport]) -> None:
    """Красивый вывод в консоль."""
    if not reports:
        print("\n  ✅ Проблем не найдено")
        return

    by_severity: dict[str, list[DiagnosticReport]] = {}
    for r in reports:
        sev = r.severity.value if isinstance(r.severity, ReportSeverity) else str(r.severity)
        by_severity.setdefault(sev, []).append(r)

    for sev in ("critical", "error", "warning", "info"):
        lst = by_severity.get(sev)
        if not lst:
            continue
        icon = SEVERITY_ICONS.get(sev, "📋")
        print(f"\n  {icon} [{sev.upper()}] — {len(lst)} шт.")
        for r in lst:
            msg = (r.message or "—")[:120]
            loc = r.location or ""
            rec = r.recommendation or ""
            det = r.detector or ""
            print(f"    [{det}] {msg}")
            if loc:
                print(f"      📍 {loc}")
            if rec:
                print(f"      → {rec[:120]}")

    print(f"\n  ─────────────────────────────")
    print(f"  Всего: {len(reports)} диагностических отчётов")
    crit_count = len(by_severity.get("critical", []))
    err_count = len(by_severity.get("error", []))
    warn_count = len(by_severity.get("warning", []))
    if crit_count:
        print(f"  🔥 Критических: {crit_count}")
    if err_count:
        print(f"  ❌ Ошибок: {err_count}")
    if warn_count:
        print(f"  ⚠️  Предупреждений: {warn_count}")


def print_summary_table(reports: list[DiagnosticReport]) -> None:
    """Сводная таблица по детекторам."""
    from collections import Counter

    detector_counts: Counter[str] = Counter()
    detector_severity: dict[str, Counter[str]] = {}

    for r in reports:
        det = r.detector or "unknown"
        sev = r.severity.value if isinstance(r.severity, ReportSeverity) else str(r.severity)
        detector_counts[det] += 1
        detector_severity.setdefault(det, Counter())[sev] += 1

    if not detector_counts:
        return

    print(f"\n  {'Детектор':<30} {'Всего':>6} {'🔥':>4} {'❌':>4} {'⚠️':>4} {'ℹ️':>4}")
    print(f"  {'─'*30} {'─'*6} {'─'*4} {'─'*4} {'─'*4} {'─'*4}")
    for det, total in detector_counts.most_common():
        sv = detector_severity.get(det, Counter())
        print(f"  {det:<30} {total:>6} {sv.get('critical', 0):>4} "
              f"{sv.get('error', 0):>4} {sv.get('warning', 0):>4} {sv.get('info', 0):>4}")


def save_json_report(reports: list[DiagnosticReport], output_path: str) -> None:
    """Сохраняет отчёт в JSON."""
    from aethon.xray.trace_store import store

    store_stats = store.stats if hasattr(store, 'stats') else {}

    report = {
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "detector_count": len(DETECTORS),
            "report_count": len(reports),
            "trace_store": {
                "active_traces": store_stats.get("active_traces", 0),
                "completed_traces": store_stats.get("completed_traces", 0),
                "orphan_spans": store_stats.get("orphan_spans", 0),
            },
        },
        "reports": [r.to_dict() for r in reports],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  📄 Отчёт сохранён: {output_path}")


def save_html_report(reports: list[DiagnosticReport], output_path: str | None = None) -> str:
    """Генерирует самодостаточный HTML-отчёт. Без внешних зависимостей."""
    from collections import Counter

    sev_order = ["critical", "error", "warning", "info"]
    sev_colors = {"critical": "#dc3545", "error": "#fd7e14", "warning": "#ffc107", "info": "#0dcaf0"}
    sev_icons = {"critical": "🔥", "error": "❌", "warning": "⚠️", "info": "ℹ️"}

    by_severity: dict[str, list[DiagnosticReport]] = {}
    det_counts: Counter[str] = Counter()
    for r in reports:
        sev = r.severity.value if isinstance(r.severity, ReportSeverity) else str(r.severity)
        by_severity.setdefault(sev, []).append(r)
        det_counts[r.detector or "unknown"] += 1

    rows = ""
    for r in reports:
        sev = r.severity.value if isinstance(r.severity, ReportSeverity) else str(r.severity)
        color = sev_colors.get(sev, "#6c757d")
        icon = sev_icons.get(sev, "•")
        loc = (r.location or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        msg = (r.message or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rec = (r.recommendation or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        det = (r.detector or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rows += f"""<tr>
<td><span class="badge" style="background:{color}">{icon} {sev}</span></td>
<td>{det}</td>
<td>{msg[:200]}</td>
<td>{loc}</td>
<td>{rec[:200]}</td>
</tr>\n"""

    summary_rows = ""
    for sev in sev_order:
        lst = by_severity.get(sev, [])
        if not lst:
            continue
        color = sev_colors.get(sev, "#6c757d")
        icon = sev_icons.get(sev, "•")
        summary_rows += f"""<tr><td><span class="badge" style="background:{color}">{icon} {sev.upper()}</span></td><td>{len(lst)}</td></tr>\n"""

    det_rows = ""
    for det, total in det_counts.most_common():
        det_rows += f"<tr><td>{det}</td><td>{total}</td></tr>\n"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head><meta charset="utf-8"><title>HEALER Diagnostic Report</title>
<style>
body{{font-family:-apple-system,sans-serif;margin:20px;background:#f8f9fa;color:#212529}}
h1{{color:#1a1a2e;border-bottom:2px solid #1a1a2e;padding-bottom:8px}}
h2{{color:#16213e;margin-top:24px}}
table{{width:100%;border-collapse:collapse;margin:12px 0;background:#fff;border-radius:6px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.12)}}
th,td{{padding:8px 12px;text-align:left;border-bottom:1px solid #dee2e6}}
th{{background:#1a1a2e;color:#fff;font-weight:600}}
tr:hover{{background:#f1f3f5}}
.badge{{display:inline-block;padding:2px 8px;border-radius:10px;color:#fff;font-size:12px;font-weight:600}}
.summary{{display:flex;gap:16px;flex-wrap:wrap;margin:12px 0}}
.stat{{background:#fff;border-radius:6px;padding:12px 20px;box-shadow:0 1px 3px rgba(0,0,0,.12);flex:1;min-width:120px;text-align:center}}
.stat-value{{font-size:28px;font-weight:700;color:#1a1a2e}}
.stat-label{{font-size:12px;color:#6c757d;margin-top:4px}}
.meta{{color:#6c757d;font-size:13px;margin:8px 0}}
.footer{{margin-top:24px;padding:12px;background:#fff;border-radius:6px;box-shadow:0 1px 3px rgba(0,0,0,.12);text-align:center;color:#6c757d;font-size:12px}}
</style></head>
<body>
<h1>🔍 HEALER Diagnostic Report</h1>
<div class="meta">Generated: {now} &middot; Detectors: {len(DETECTORS)} &middot; Reports: {len(reports)}</div>

<div class="summary">
<div class="stat"><div class="stat-value">{len(reports)}</div><div class="stat-label">Total Reports</div></div>
<div class="stat"><div class="stat-value">{len(by_severity.get('critical', []))}</div><div class="stat-label">Critical</div></div>
<div class="stat"><div class="stat-value">{len(by_severity.get('error', []))}</div><div class="stat-label">Errors</div></div>
<div class="stat"><div class="stat-value">{len(by_severity.get('warning', []))}</div><div class="stat-label">Warnings</div></div>
</div>

<h2>📊 By Severity</h2>
<table><thead><tr><th>Severity</th><th>Count</th></tr></thead><tbody>{summary_rows}</tbody></table>

<h2>📋 By Detector</h2>
<table><thead><tr><th>Detector</th><th>Count</th></tr></thead><tbody>{det_rows}</tbody></table>

<h2>📄 All Reports</h2>
<table><thead><tr><th>Severity</th><th>Detector</th><th>Message</th><th>Location</th><th>Recommendation</th></tr></thead><tbody>{rows}</tbody></table>

<div class="footer">HEALER Self-Healing Module &mdash; Zero external dependencies</div>
</body></html>"""

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n  📄 HTML-отчёт сохранён: {output_path}")
    return html


def run_one_cycle(
    trace_path: str,
    output: str | None = None,
    reports: list[DiagnosticReport] | None = None,
    all_reports: list[DiagnosticReport] | None = None,
    fmt: str = "table",
) -> list[DiagnosticReport]:
    """Один полный цикл диагностики."""
    if reports is None:
        load_trace_store(trace_path)
        all_reports = cast("list[DiagnosticReport]", run_diagnostics())
        reports = all_reports

    if fmt == "json":
        reports_dict = [r.to_dict() for r in reports]
        text = json.dumps({"reports": reports_dict}, ensure_ascii=False, indent=2)
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(text)
        else:
            sys.stdout.buffer.write(text.encode("utf-8"))
            sys.stdout.buffer.write(b"\n")
        return reports

    if fmt == "html":
        html = save_html_report(reports, output_path=output)
        if not output:
            sys.stdout.buffer.write(html.encode("utf-8"))
            sys.stdout.buffer.write(b"\n")
        return reports

    # fmt == "table" (default)
    print(f"\n{'='*60}")
    print(f"  ДИАГНОСТИКА HEALER — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Данные: {trace_path}")
    total = len(all_reports) if all_reports else len(reports)
    filtered = len(reports)
    if filtered < total:
        print(f"  Отфильтровано: {total} → {filtered}")
    print(f"{'='*60}")

    print_console_report(reports)
    print_summary_table(reports)

    if output:
        ext = Path(output).suffix.lower()
        if ext == ".html":
            save_html_report(reports, output)
        else:
            save_json_report(reports, output)

    return reports


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HEALER Diagnostics — запуск диагностики на реальных X-RAY данных",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python -m healer.diagnostics.runner
  python -m healer.diagnostics.runner --path /path/to/trace_store
  python -m healer.diagnostics.runner --path data/trace_store --output report.json
  python -m healer.diagnostics.runner --watch --interval 60 --output report.json
        """,
    )
    parser.add_argument(
        "--path", "-p",
        default=None,
        help="Путь к папке trace_store (по умолчанию data/trace_store)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Сохранить отчёт в JSON-файл",
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Режим непрерывного мониторинга",
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=60,
        help="Интервал проверки в секундах (по умолчанию 60)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Тихий режим — только JSON в stdout (то же что --format json)",
    )
    parser.add_argument(
        "--format", "-f",
        default="table",
        choices=["json", "html", "table"],
        help="Формат вывода: json, html, table (по умолчанию table). --quiet переопределяет в json",
    )
    parser.add_argument(
        "--min-severity", "-s",
        default="info",
        choices=["info", "warning", "error", "critical"],
        help="Минимальный уровень severity для отчёта (по умолчанию info)",
    )
    parser.add_argument(
        "--fail-on",
        default="error",
        choices=["never", "warning", "error", "critical"],
        help="При каком severity возвращать exit code 1 (для CI/CD)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    trace_path = args.path
    if trace_path is None:
        trace_path = str(Path(__file__).parent.parent.parent / "data" / "trace_store")

    if not os.path.isdir(trace_path):
        print(f"❌ Папка не найдена: {trace_path}", file=sys.stderr)
        return 1

    load_trace_store(trace_path)

    fmt = "json" if args.quiet else args.format
    cb = None if fmt == "json" else print_event
    all_reports = cast("list[DiagnosticReport]", run_diagnostics(event_callback=cb))
    reports = filter_reports(all_reports, args.min_severity)

    if fmt == "json":
        reports_dict = [r.to_dict() for r in reports]
        text = json.dumps({"reports": reports_dict}, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text)
        else:
            sys.stdout.buffer.write(text.encode("utf-8"))
            sys.stdout.buffer.write(b"\n")
    elif args.watch:
        _watch_loop(trace_path, args, fmt)
    else:
        run_one_cycle(trace_path, args.output, reports, all_reports, fmt=fmt)

    exit_code = _compute_exit_code(reports, args.fail_on)
    return exit_code


def _watch_loop(trace_path: str, args: argparse.Namespace, fmt: str = "table") -> None:
    """Цикл непрерывного мониторинга."""
    cycle = 0
    cb = None if fmt == "json" else print_event
    all_reports: list[DiagnosticReport] | None = None
    reports: list[DiagnosticReport] | None = None
    try:
        while True:
            cycle += 1
            if cycle > 1:
                print(f"\n{'─'*60}")
                print(f"  Цикл #{cycle} — ожидание {args.interval}с...")
                time.sleep(args.interval)
                load_trace_store(trace_path)
                all_reports = cast("list[DiagnosticReport]", run_diagnostics(event_callback=cb))
                reports = filter_reports(all_reports, args.min_severity)
            run_one_cycle(trace_path, args.output, reports, all_reports, fmt=fmt)
    except KeyboardInterrupt:
        print("\n\n  ⏹  Мониторинг остановлен")


def _compute_exit_code(reports: list[DiagnosticReport], fail_on: str) -> int:
    """Вычисляет exit code для CI/CD."""
    if fail_on == "never":
        return 0
    fail_rank = SEVERITY_RANK.get(fail_on, 1)
    for r in reports:
        sev = r.severity.value if isinstance(r.severity, ReportSeverity) else str(r.severity)
        if SEVERITY_RANK.get(sev, 3) <= fail_rank:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
