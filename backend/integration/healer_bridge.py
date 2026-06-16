"""
🔗 HealerBridge — мост между PAD+ и HEALER

Подключается к PAD+ TraceCollector и релеит события в HEALER TraceStore.
Позволяет запускать полный цикл диагностики и патчинга HEALER на PAD+ коде.
Не заменяет существующий backend/healing/ — работает параллельно.

Использование:
    from integration import get_healer_bridge
    bridge = get_healer_bridge()
    await bridge.start(collector)
"""

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("padplus.integration.healer_bridge")

# ── Путь к HEALER ────────────────────────────────────────────────
_HEALER_ROOT: Optional[Path] = None


def _resolve_healer_root() -> Path:
    """Определяет и добавляет HEALER в sys.path."""
    global _HEALER_ROOT
    if _HEALER_ROOT is not None:
        return _HEALER_ROOT

    candidates = [
        Path(__file__).resolve().parent.parent.parent / "HEALER",
        Path(__file__).resolve().parent.parent / "HEALER",
        Path.cwd() / "HEALER",
    ]
    # Ищем сверху вниз от корня проекта
    here = Path(__file__).resolve().parent
    for p in [here] + list(here.parents):
        candidate = p / "HEALER"
        if candidate.is_dir() and (candidate / "aethon").is_dir():
            _HEALER_ROOT = candidate
            break

    if _HEALER_ROOT is None:
        for c in candidates:
            if c.is_dir() and (c / "aethon").is_dir():
                _HEALER_ROOT = c
                break

    if _HEALER_ROOT is None:
        raise RuntimeError(
            "HEALER не найден. Ожидается директория HEALER/ с aethon.xray и healer/ модулями."
        )

    root_str = str(_HEALER_ROOT.resolve())
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
        logger.info("HEALER root добавлен в sys.path: %s", root_str)

    return _HEALER_ROOT.resolve()


# ── Мост ─────────────────────────────────────────────────────────


class HealerBridge:
    """Мост между PAD+ и HEALER. Неблокирующий, best-effort.

    Режимы работы:
      - monitor — только сбор событий и диагностика
      - suggest — диагностика + генерация патчей (без apply)
      - auto — полный цикл: диагностика → патч → верификация → apply/rollback
    """

    def __init__(self, mode: str = "monitor"):
        healer_root = _resolve_healer_root()

        # Импорт HEALER модулей (после добавления в sys.path)
        from healer.orchestrator import HealerOrchestrator
        from healer.diagnostics.runner import run_diagnostics, filter_reports
        from healer.meta.meta_learner import MetaLearner

        self._run_diagnostics = run_diagnostics
        self._filter_reports = filter_reports

        self.mode = mode
        self.project_path = healer_root.parent.resolve()
        self._collector: Optional[Any] = None
        self._subscribed = False
        self._callbacks: list[Callable] = []
        self._started = False

        # Оркестратор создаётся сразу — не зависит от подписки
        self._orchestrator = HealerOrchestrator(
            project_path=str(self.project_path),
            mode=self.mode,
        )

        logger.info(
            "HealerBridge инициализирован (mode=%s, project=%s)",
            mode, self.project_path,
        )

    # ── Lifecycle ────────────────────────────────────────────────

    def start(self, collector: Any) -> None:
        """Подключается к TraceCollector и запускает релей событий."""
        if self._started:
            logger.warning("HealerBridge уже запущен")
            return

        self._collector = collector

        # Подписываемся на события TraceCollector
        try:
            collector.subscribe(self._on_trace_event)
            self._subscribed = True
            logger.info("HealerBridge подписан на TraceCollector")
        except Exception as e:
            logger.warning("HealerBridge subscribe error: %s", e)

        self._started = True

    def stop(self) -> None:
        """Отписывается и останавливает HEALER."""
        if self._orchestrator:
            try:
                self._orchestrator.stop()
            except Exception as e:
                logger.warning(f"Operation failed: {e}")
        if self._collector and self._subscribed:
            try:
                self._collector.unsubscribe(self._on_trace_event)
                self._subscribed = False
            except Exception as e:
                logger.warning(f"Operation failed: {e}")
        self._started = False
        logger.info("HealerBridge остановлен")

    def set_mode(self, mode: str) -> None:
        """Меняет режим работы (monitor/suggest/auto)."""
        self.mode = mode
        if self._orchestrator:
            self._orchestrator.set_mode(mode)
        logger.info("HealerBridge mode → %s", mode)

    # ── Event relay: PAD+ TraceCollector → HEALER ───────────────

    def _on_trace_event(self, event_type: str, data: dict) -> None:
        """Обработчик событий от PAD+ TraceCollector.

        Релеит ключевые события в HEALER TraceStore
        как HEALER-спаны. Best-effort, не блокирует.
        """
        if not self._orchestrator:
            return

        try:
            if event_type == "session_started":
                self._on_session_started(data)
            elif event_type == "event_recorded":
                self._on_event_recorded(data)
            elif event_type == "session_completed":
                self._on_session_completed(data)
        except Exception as e:
            logger.debug("HealerBridge event relay error: %s", e)

    def _on_session_started(self, data: dict) -> None:
        """Создаёт HEALER-трейс при старте сессии PAD+."""
        try:
            from aethon.xray import start_trace

            trace = start_trace(
                name=f"padplus.{data.get('request_id', 'unknown')[:12]}",
                trace_id=data.get("request_id", ""),
                metadata={
                    "source": "padplus",
                    "user_message": data.get("user_message", ""),
                    "timestamp": data.get("timestamp", ""),
                },
            )
            # Не закрываем — закроется при session_completed
            _ = trace  # хранится в HEALER ContextVar
        except Exception as e:
            logger.warning(f"Operation failed: {e}")
    def _on_event_recorded(self, data: dict) -> None:
        """Создаёт HEALER-спан при эвенте стадии PAD+."""
        try:
            from aethon.xray import start_span, SpanKind

            stage = data.get("stage", "unknown")
            status = data.get("status", "ok")
            duration = data.get("duration_ms", 0)

            span = start_span(
                kind=SpanKind.CORE_ORCHESTRATE,
                name=f"padplus.{stage}",
                metadata={
                    "stage": stage,
                    "duration_ms": duration,
                    "status": status,
                    "error": data.get("error"),
                },
            )
            span.end(status)
        except Exception as e:
            logger.warning(f"Operation failed: {e}")
    def _on_session_completed(self, data: dict) -> None:
        """Закрывает HEALER-трейс при завершении сессии PAD+."""
        try:
            from aethon.xray.trace import get_current_trace_id, set_current_trace_id
            from aethon.xray import store

            tid = data.get("request_id")
            if not tid:
                return

            trace = store.get_trace(tid)
            if trace:
                trace.end("ok" if data.get("completed", False) else "error")
        except Exception as e:
            logger.warning(f"Operation failed: {e}")
    # ── Diagnostics ──────────────────────────────────────────────

    def run_diagnostics(
        self,
        event_callback: Optional[Callable[[str, dict], None]] = None,
    ) -> list[dict]:
        """Запускает HEALER-диагностику на PAD+ коде.

        Returns:
            Список DiagnosticReport в виде dict.
        """
        try:
            reports = self._run_diagnostics(event_callback=event_callback)
            return [r.to_dict() for r in reports]
        except Exception as e:
            logger.error("HealerBridge diagnostics error: %s", e)
            return []

    # ── Full healing cycle ───────────────────────────────────────

    def run_patch_cycle(
        self,
        diagnostics_callback: Optional[Callable[[str, dict], None]] = None,
    ) -> dict:
        """Запускает полный healing cycle HEALER.

        Returns:
            dict с полями HealingCycle + reports.
        """
        if not self._orchestrator:
            return {"status": "error", "errors": ["Orchestrator not initialized"], "reports": []}

        try:
            def _diag_callback(event: dict):
                """HEALER diagnostics runner шлёт event как один словарь {'type': ..., ...}."""
                etype = event.get("type", "unknown")
                data = {k: v for k, v in event.items() if k != "type" and k != "timestamp"}
                logger.debug("_diag_callback вызван: type=%s callbacks=%d", etype, len(self._callbacks))
                if diagnostics_callback:
                    diagnostics_callback(etype, data)
                for cb in self._callbacks:
                    try:
                        cb(etype, data)
                    except Exception as exc:
                        logger.warning("HealerBridge callback error: %s", exc)

            logger.info("🔥 HealerBridge: запуск run_cycle (mode=%s)", self.mode)
            cycle = self._orchestrator.run_cycle(
                quiet=False,
                diagnostics_callback=_diag_callback,
            )
            logger.info("🔥 HealerBridge: run_cycle завершён (status=%s, reports=%d)",
                        cycle.status, cycle.report_count)
            result = cycle.to_dict()
            result["reports"] = cycle.reports
            return result
        except Exception as e:
            logger.error("HealerBridge patch cycle error: %s", e)
            return {"status": "error", "errors": [str(e)], "reports": []}

    def get_last_reports(self, min_severity: str = "info") -> list[dict]:
        """Возвращает отчёты последнего цикла, отфильтрованные по severity."""
        if not self._orchestrator:
            return []
        try:
            sev_order = {"info": 0, "warning": 1, "error": 2, "critical": 3}
            min_rank = sev_order.get(min_severity, 0)
            reports = self._orchestrator._last_reports or []
            return [
                r.to_dict() for r in reports
                if sev_order.get(r.severity.value if hasattr(r.severity, 'value') else str(r.severity), 0) >= min_rank
            ]
        except Exception as e:
            logger.error("get_last_reports error: %s", e)
            return []

    # ── Status ───────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Возвращает статус HEALER-моста."""
        healer_status = {}
        if self._orchestrator:
            try:
                healer_status = self._orchestrator.get_status()
            except Exception as e:
                logger.warning(f"Operation failed: {e}")
        return {
            "mode": self.mode,
            "started": self._started,
            "subscribed": self._subscribed,
            "project": str(self.project_path),
            **healer_status,
        }

    def on_event(self, callback: Callable) -> None:
        """Подписывает внешний обработчик на события HEALER."""
        self._callbacks.append(callback)
        if self._orchestrator:
            self._orchestrator.on_event(callback)

    def get_orchestrator(self):
        """Возвращает HEALER Orchestrator для прямого доступа."""
        return self._orchestrator


# ── Global instance ──────────────────────────────────────────────

_bridge: Optional[HealerBridge] = None


def get_healer_bridge(mode: str | None = None) -> HealerBridge:
    """Возвращает глобальный экземпляр HealerBridge.

    Args:
        mode: Если bridge уже создан и mode передан — режим обновляется.
              Если bridge не создан — создаётся с указанным mode.
    """
    global _bridge
    if _bridge is None:
        _bridge = HealerBridge(mode=mode or "monitor")
    if mode is not None:
        _bridge.set_mode(mode)
    return _bridge
