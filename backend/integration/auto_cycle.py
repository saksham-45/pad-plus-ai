"""
🔄 AutoCycleScheduler — фоновые автоматические циклы HEALER

Запускает healer_bridge.run_patch_cycle() по таймеру.
Результаты каждого цикла транслируются в WebSocket.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Optional

logger = logging.getLogger("padplus.integration.auto_cycle")


class AutoCycleScheduler:
    """Планировщик автоматических healing-циклов.

    Использование:
        scheduler = AutoCycleScheduler(run_fn=bridge.run_patch_cycle)
        scheduler.set_broadcast_fn(lambda msg: ...)
        await scheduler.start(interval_sec=300)
        ...
        await scheduler.stop()
    """

    def __init__(
        self,
        run_fn: Optional[Callable[[], dict]] = None,
        broadcast_fn: Optional[Callable[[dict], None]] = None,
    ):
        self._run_fn = run_fn
        self._broadcast_fn = broadcast_fn
        self._task: Optional[asyncio.Task] = None
        self._enabled = False
        self._interval_sec: float = 300  # 5 minutes default
        self._running = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def interval_sec(self) -> float:
        return self._interval_sec

    @property
    def running(self) -> bool:
        return self._running

    def set_run_fn(self, fn: Callable[[], dict]) -> None:
        self._run_fn = fn

    def set_broadcast_fn(self, fn: Callable[[dict], None]) -> None:
        self._broadcast_fn = fn

    async def start(self, interval_sec: float = 300) -> None:
        """Запускает фоновый цикл с указанным интервалом (секунды)."""
        if self._task is not None and not self._task.done():
            logger.warning("AutoCycleScheduler уже запущен")
            return

        self._interval_sec = max(30, interval_sec)  # минимум 30 секунд
        self._enabled = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("🔄 AutoCycleScheduler запущен (interval=%ds)", self._interval_sec)

    async def stop(self) -> None:
        """Останавливает фоновый цикл."""
        self._enabled = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("🔄 AutoCycleScheduler остановлен")

    async def reconfigure(self, interval_sec: float) -> None:
        """Меняет интервал на лету (перезапускает задачу)."""
        was_enabled = self._enabled
        if self._enabled:
            await self.stop()
        self._interval_sec = max(30, interval_sec)
        if was_enabled:
            await self.start(self._interval_sec)
        logger.info("🔄 AutoCycleScheduler reconfigured (interval=%ds)", self._interval_sec)

    def get_status(self) -> dict:
        return {
            "enabled": self._enabled,
            "interval_sec": self._interval_sec,
            "running": self._running,
        }

    def _broadcast(self, msg: dict) -> None:
        if self._broadcast_fn:
            try:
                self._broadcast_fn(msg)
            except Exception as exc:
                logger.warning("AutoCycle broadcast error: %s", exc)

    async def _run_loop(self) -> None:
        """Основной цикл: ждёт → запускает диагностику → ждёт → ..."""
        while self._enabled:
            self._running = False
            try:
                await asyncio.sleep(self._interval_sec)
            except asyncio.CancelledError:
                break

            if not self._enabled:
                break

            self._running = True
            self._broadcast({
                "type": "healer_bridge_auto_cycle_start",
                "data": {"interval_sec": self._interval_sec},
                "timestamp": datetime.now().isoformat(),
            })

            try:
                if self._run_fn:
                    result = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, self._run_fn),
                        timeout=max(60, self._interval_sec - 5),
                    )
                    status = result.get("status") if isinstance(result, dict) else "done"
                    reports = result.get("reports") if isinstance(result, dict) else []
                else:
                    result = {"status": "error", "message": "run_fn not set"}
                    status = "error"
                    reports = []

                self._broadcast({
                    "type": "healer_bridge_auto_cycle_complete",
                    "data": {
                        "status": status,
                        "reports": reports,
                        "result": result,
                    },
                    "timestamp": datetime.now().isoformat(),
                })
                logger.info("🔄 AutoCycle завершён (status=%s)", status)
            except asyncio.TimeoutError:
                logger.warning("🔄 AutoCycle TIMEOUT (%ds)", self._interval_sec)
                self._broadcast({
                    "type": "healer_bridge_auto_cycle_complete",
                    "data": {"status": "timeout", "reports": []},
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as exc:
                logger.error("🔄 AutoCycle error: %s", exc)
                self._broadcast({
                    "type": "healer_bridge_auto_cycle_complete",
                    "data": {"status": "error", "message": str(exc), "reports": []},
                    "timestamp": datetime.now().isoformat(),
                })
            finally:
                self._running = False
