"""Оркестратор Self-Healing — соединяет Diagnostics + Patcher + Verifier.

Режимы:
  - monitor — только диагностика, без исправлений
  - suggest — диагностика + генерация патчей, но без apply
  - auto — полный цикл: diagnose → patch → verify → apply/rollback
"""

from __future__ import annotations

import logging
import threading
import time
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, cast

from aethon.xray import start_trace, start_span, SpanKind
from healer.diagnostics.report import DiagnosticReport, ReportSeverity
from healer.diagnostics.runner import run_diagnostics, filter_reports, DETECTORS
from healer.meta.meta_learner import MetaLearner, HealingRecord
from healer.meta.strategies import AdaptiveStrategies


class HealerMode(str, Enum):
    MONITOR = "monitor"
    SUGGEST = "suggest"
    AUTO = "auto"


@dataclass
class HealingCycle:
    id: str = ""
    mode: HealerMode = HealerMode.MONITOR
    started_at: float = 0.0
    ended_at: float | None = None
    status: str = "pending"
    report_count: int = 0
    patched_files: list[str] = field(default_factory=list)
    applied_count: int = 0
    rolled_back: int = 0
    errors: list[str] = field(default_factory=list)
    summary: str = ""
    reports: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode.value,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "report_count": self.report_count,
            "patched_files": self.patched_files,
            "applied_count": self.applied_count,
            "rolled_back": self.rolled_back,
            "errors": self.errors,
            "summary": self.summary,
            "reports": self.reports,
        }


logger = logging.getLogger("healer.orchestrator")


class HealerOrchestrator:
    """Управляет полным циклом самовосстановления."""

    def __init__(self, project_path: str | None = None, mode: str = "monitor"):
        self.project_path = Path(project_path).resolve() if project_path else None
        self.mode = HealerMode(mode)
        self.history: list[HealingCycle] = []
        self.current_cycle: HealingCycle | None = None
        self._running = False
        self._stop_event = threading.Event()
        self._callbacks: list[Any] = []
        self.meta = MetaLearner()
        self.strategies = AdaptiveStrategies(self.meta)
        self._last_reports: list[DiagnosticReport] = []

        self._load_patchers()

    def set_mode(self, mode: str) -> None:
        self.mode = HealerMode(mode)

    def get_mode(self) -> str:
        return self.mode.value

    def stop(self) -> None:
        """Signal the orchestrator to stop after current phase completes."""
        self._stop_event.set()
        self._running = False

    def on_event(self, callback: Any) -> None:
        self._callbacks.append(callback)

    def _emit(self, event: str, data: dict[str, Any]) -> None:
        for cb in self._callbacks:
            try:
                cb(event, data)
            except Exception as e:
                logger.warning("Ошибка в callback HEALER: %s", e)

    def _load_patchers(self) -> None:
        self.patchers: dict[str, Any] = {}
        try:
            from healer.patcher.python_patcher import PythonPatcher
            pp = PythonPatcher()
            for d in pp.get_supported_detectors():
                self.patchers[d] = pp
        except ImportError:
            logger.warning("PythonPatcher не загружен (опциональный модуль)")

        try:
            from healer.patcher.cache_cleaner import CacheCleanerPatcher
            cp = CacheCleanerPatcher()
            for d in cp.get_supported_detectors():
                self.patchers[d] = cp
        except ImportError:
            logger.warning("CacheCleanerPatcher не загружен")

    def run_cycle(self, trace_path: str | None = None, quiet: bool = False,
                  diagnostics_callback: Any = None) -> HealingCycle:
        self._stop_event.clear()
        self._running = True
        cycle_id = f"cycle_{int(time.time() * 1000)}"
        self.current_cycle = HealingCycle(
            id=cycle_id, mode=self.mode,
            started_at=time.time(), status="running",
        )

        trace = start_trace(f"healer.cycle.{cycle_id}", metadata={
            "mode": self.mode.value, "project": str(self.project_path or trace_path or ""),
        })

        try:
            if self._stop_event.is_set():
                raise KeyboardInterrupt("graceful shutdown")

            target = trace_path or (str(self.project_path) if self.project_path else None)
            if not target:
                self.current_cycle.status = "error"
                self.current_cycle.errors.append("No target path")
                self.current_cycle.ended_at = time.time()
                self.history.append(self.current_cycle)
                if trace: trace.end("error")
                self._running = False
                return self.current_cycle

            from aethon.xray.trace_store import store
            ts = store.get(target)
            if not ts.persist_enabled:
                ts.configure_persistence(target)
            store.set_active(target)

            # ── Phase 1: Diagnostics ──
            diag_span = start_span(SpanKind.DIAGNOSTIC, "healer.diagnostics.run")
            all_reports = cast("list[DiagnosticReport]", run_diagnostics(event_callback=diagnostics_callback))
            reports = filter_reports(all_reports, "warning")
            if diag_span: diag_span.end("ok")

            if self._stop_event.is_set():
                raise KeyboardInterrupt("graceful shutdown after diagnostics")

            self.current_cycle.report_count = len(reports)
            self._last_reports = reports
            self.current_cycle.reports = [r.to_dict() for r in reports]
            self._emit("diagnostics", {"reports": len(reports), "total": len(all_reports)})

            if not reports:
                self.current_cycle.status = "ok"
                self.current_cycle.summary = "Проблем не найдено"
                self.current_cycle.ended_at = time.time()
                self.history.append(self.current_cycle)
                if trace: trace.end("ok")
                self._running = False
                return self.current_cycle

            if self.mode == HealerMode.MONITOR:
                self.current_cycle.status = "ok"
                self.current_cycle.summary = f"Найдено {len(reports)} проблем (monitor — без исправлений)"
                self.current_cycle.ended_at = time.time()
                self.history.append(self.current_cycle)
                if trace: trace.end("ok")
                self._running = False
                return self.current_cycle

            # ── Phase 2: Patch ──
            if self._stop_event.is_set():
                raise KeyboardInterrupt("graceful shutdown before patch")

            patch_span = start_span(SpanKind.DIAGNOSTIC, "healer.patcher.run")
            patched_any = False
            for report in reports:
                if self._stop_event.is_set():
                    break
                if self.mode == HealerMode.AUTO:
                    ok = self._apply_patch_for(report)
                    if ok: patched_any = True
                elif self.mode == HealerMode.SUGGEST:
                    ok = self._generate_patch_only(report)
                    if ok: patched_any = True
            if patch_span: patch_span.end("ok" if patched_any else "skip")

            # ── Phase 3: Verification (only in auto mode) ──
            if self.mode == HealerMode.AUTO and self.current_cycle.patched_files:
                if self._stop_event.is_set():
                    raise KeyboardInterrupt("graceful shutdown before verification")
                verify_span = start_span(SpanKind.DIAGNOSTIC, "healer.verifier.run")
                try:
                    from healer.verifier.test_runner import TestRunner
                    test_result = TestRunner(str(self.project_path) if self.project_path else ".").run()
                    if test_result.verdict.value == "passed":
                        self.current_cycle.summary = f"Патчи применены, тесты пройдены"
                    else:
                        self.current_cycle.summary = f"Патчи откачены: {test_result.message}"
                        self._rollback_all()
                        self.current_cycle.status = "rolled_back"
                    if verify_span: verify_span.end("ok")
                except Exception as e:
                    if verify_span: verify_span.end("error")
                    self.current_cycle.errors.append(str(e))

            if not self.current_cycle.status or self.current_cycle.status == "running":
                self.current_cycle.status = "ok"
            self.current_cycle.ended_at = time.time()
            self._record_meta()
            self.history.append(self.current_cycle)
            if trace: trace.end(self.current_cycle.status)

        except KeyboardInterrupt:
            if self.current_cycle:
                self.current_cycle.status = "interrupted"
                self.current_cycle.summary = "Остановлен по сигналу graceful shutdown"
                self.current_cycle.ended_at = time.time()
                self.history.append(self.current_cycle)
            if trace: trace.end("interrupted")
        except Exception as e:
            self.current_cycle.status = "error"
            self.current_cycle.errors.append(str(e))
            self.current_cycle.ended_at = time.time()
            self.history.append(self.current_cycle)
            if trace: trace.end("error")
        finally:
            self._running = False

        return self.current_cycle

    def _apply_patch_for(self, report: DiagnosticReport) -> bool:
        patcher = self.patchers.get(report.detector)
        if not patcher:
            return False

        source_path = self._guess_source_path(report)
        if not source_path:
            return False

        try:
            result = patcher.patch_file(str(source_path), report)
            if result.success:
                ok = result.apply(backup=True)
                self.current_cycle.patched_files.append(str(source_path))
                if ok:
                    self.current_cycle.applied_count += 1
                    if result.restart_required:
                        self._write_restart_flag()
                    self._emit("patch_applied", {"file": str(source_path), "pattern": result.pattern})
                    return True
        except Exception as e:
            logger.warning("Ошибка применения патча для %s: %s", source_path, e)
        return False

    def _write_restart_flag(self) -> None:
        """Write .restart_required flag file for external systems."""
        flag = self.project_path / ".restart_required" if self.project_path else Path(".restart_required")
        try:
            flag.write_text("restart_required", encoding="utf-8")
            self._emit("restart_required", {"message": "HEALER needs restart to apply changes"})
        except OSError as e:
            logger.warning("Не удалось записать restart-флаг: %s", e)

    def check_restart_required(self) -> bool:
        flag = self.project_path / ".restart_required" if self.project_path else Path(".restart_required")
        return flag.exists()

    def _generate_patch_only(self, report: DiagnosticReport) -> bool:
        patcher = self.patchers.get(report.detector)
        if not patcher:
            return False

        source_path = self._guess_source_path(report)
        if not source_path:
            return False

        try:
            result = patcher.patch_file(str(source_path), report)
            if result.success:
                self.current_cycle.patched_files.append(str(source_path))
                self._emit("patch_generated", {"file": str(source_path), "diff": result.diff})
                return True
        except Exception as e:
            logger.warning("Ошибка генерации патча для %s: %s", source_path, e)
        return False

    def _rollback_all(self) -> None:
        from healer.verifier.rollback import RollbackEngine
        engine = RollbackEngine()
        for f in self.current_cycle.patched_files:
            r = engine.rollback(f)
            if r.verdict.value == "passed":
                self.current_cycle.rolled_back += 1

    def _dict_to_report(self, d: dict) -> DiagnosticReport:
        sev_map = {"info": ReportSeverity.INFO, "warning": ReportSeverity.WARNING,
                   "error": ReportSeverity.ERROR, "critical": ReportSeverity.CRITICAL}
        from healer.diagnostics.report import ReportCategory
        return DiagnosticReport(
            detector=d.get("detector", ""),
            severity=sev_map.get(d.get("severity", "info"), ReportSeverity.INFO),
            category=ReportCategory.PERFORMANCE,
            trace_id=d.get("trace_id"),
            span_id=d.get("span_id"),
            location=d.get("location", ""),
            message=d.get("message", ""),
            recommendation=d.get("recommendation", ""),
        )

    def _guess_source_path(self, report: DiagnosticReport) -> Path | None:
        if self.project_path and self.project_path.is_dir():
            return self.project_path / "viewer.py"
        return None

    def _record_meta(self) -> None:
        if not self.current_cycle:
            return
        c = self.current_cycle
        duration = ((c.ended_at or time.time()) - c.started_at) * 1000

        for f in c.patched_files:
            for report in self._last_reports or []:
                if self._guess_source_path(report) == Path(f):
                    record = HealingRecord(
                        cycle_id=c.id,
                        mode=c.mode.value,
                        timestamp=c.started_at,
                        detector=report.detector or "unknown",
                        pattern="applied",
                        success=c.status == "ok",
                        duration_ms=duration,
                        file_path=f,
                    )
                    self.meta.record_healing(record)

    def get_history(self, limit: int = 10) -> list[dict]:
        return [c.to_dict() for c in self.history[-limit:]]

    def get_status(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "running": self._running,
            "cycles_total": len(self.history),
            "last_cycle": self.history[-1].to_dict() if self.history else None,
            "meta": self.meta.get_summary(),
        }
