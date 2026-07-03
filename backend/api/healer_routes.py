"""
🧬 Healer API Routes

Эндпоинты для управления системой самовосстановления HEALER
"""

from fastapi import APIRouter, Query
from typing import Dict, Any, Optional
import asyncio
import logging
from datetime import datetime

from healing.listener import get_healer
from healing.runner import run_diagnostics, filter_reports
from healing.report import DiagnosticReport

# HealerBridge (HEALER integration)
_bridge_available = False
_bridge_error: str = ""
try:
    from backend.integration import get_healer_bridge
    _bridge_available = True
except Exception as _be:
    _bridge_error = str(_be)

logger = logging.getLogger("padplus.api.healer")

router = APIRouter(prefix="/api/v1/healer", tags=["healer"])


@router.get("/status")
async def get_healer_status():
    """Текущий статус HealerListener (режим, циклы, история remediation)."""
    healer = get_healer()
    return {"status": "ok", "data": healer.get_status()}


@router.get("/mode")
async def get_healer_mode():
    """Текущий режим работы (monitor/suggest/auto)."""
    healer = get_healer()
    return {"status": "ok", "mode": healer.mode}


@router.post("/mode")
async def set_healer_mode(mode: str = Query(..., description="monitor|suggest|auto")):
    """Установить режим работы HealerListener."""
    valid = {"monitor", "suggest", "auto"}
    if mode not in valid:
        return {"status": "error", "message": f"Режим должен быть одним из: {', '.join(valid)}"}
    healer = get_healer()
    healer.mode = mode
    healer.remediation.set_mode(mode)
    logger.info(f"🧬 Healer режим изменён на: {mode}")
    return {"status": "ok", "mode": mode}


@router.post("/diagnose")
async def run_healer_diagnostics():
    """Запустить диагностику вручную. Возвращает все отчёты детекторов."""
    all_reports = run_diagnostics()
    result = [r.to_dict() for r in all_reports]
    return {"status": "ok", "count": len(result), "reports": result}


@router.get("/reports")
async def get_healer_reports(
    min_severity: str = Query("info", description="info|warning|error|critical"),
):
    """Последние отчёты диагностики, собранные HealerListener."""
    healer = get_healer()
    reports = healer.get_last_reports(min_severity)
    return {"status": "ok", "count": len(reports), "reports": reports}


@router.get("/remediation")
async def get_remediation_history():
    """История применённых remediate-действий."""
    healer = get_healer()
    return {"status": "ok", "history": healer.remediation.get_history()}


# === E-001: ToneEngine toggle ===

@router.get("/tone")
async def get_tone_status():
    """Статус ToneEngine (E-001)."""
    from core.guard.tone_engine import get_tone_engine
    te = get_tone_engine()
    return {"status": "ok", "data": te.get_stats()}


@router.post("/tone")
async def set_tone(enabled: bool = Query(..., description="true/false")):
    """Включить/отключить ToneEngine (E-001)."""
    from core.guard.tone_engine import get_tone_engine
    te = get_tone_engine()
    te.configure(enabled=enabled)
    return {"status": "ok", "enabled": enabled}


# === HealerBridge (HEALER integration) ===

@router.get("/bridge/status")
async def get_bridge_status():
    """Статус HealerBridge — моста PAD+ → HEALER."""
    if not _bridge_available:
        return {"status": "ok", "bridge": "not_available", "message": f"HEALER не найден: {_bridge_error}"}
    bridge = get_healer_bridge()
    return {"status": "ok", "bridge": "available", "data": bridge.get_status()}


@router.get("/bridge/mode")
async def get_bridge_mode():
    """Текущий режим HealerBridge."""
    if not _bridge_available:
        return {"status": "ok", "bridge": "not_available", "message": _bridge_error}
    bridge = get_healer_bridge()
    return {"status": "ok", "mode": bridge.mode}


@router.post("/bridge/mode")
async def set_bridge_mode(body: Dict[str, Any]):
    """Установить режим HealerBridge. Тело: {"mode": "monitor|suggest|auto"}"""
    mode = body.get("mode", "")
    valid = {"monitor", "suggest", "auto"}
    if mode not in valid:
        return {"status": "error", "message": f"Режим должен быть одним из: {', '.join(valid)}"}
    if not _bridge_available:
        return {"status": "error", "bridge": "not_available", "message": _bridge_error}
    bridge = get_healer_bridge()
    bridge.set_mode(mode)
    return {"status": "ok", "mode": mode}


@router.post("/bridge/diagnose")
async def run_bridge_diagnostics():
    """Запустить полную диагностику HEALER на PAD+ коде."""
    if not _bridge_available:
        return {"status": "error", "message": "HealerBridge не доступен"}
    bridge = get_healer_bridge()
    reports = bridge.run_diagnostics()
    return {"status": "ok", "count": len(reports), "reports": reports}


@router.post("/bridge/cycle")
async def run_bridge_cycle():
    """Запустить полный healing cycle HEALER (diagnose → patch → verify)."""
    if not _bridge_available:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "error", "bridge": "not_available", "message": _bridge_error or "HealerBridge не инициализирован"},
        )
    bridge = get_healer_bridge()
    _capture_main_loop()
    logger.info("🔍 DEBUG broadcast state: _ws_manager=%s _main_loop=%s",
                type(_ws_manager).__name__ if _ws_manager else None,
                _main_loop is not None)

    def _on_event(etype: str, data: dict):
        logger.info("HEALER event: %s — %s", etype, data)
        broadcast_ws({
            "type": f"healer_bridge_{etype}",
            "data": data,
            "timestamp": datetime.now().isoformat(),
        })

    bridge.on_event(_on_event)

    broadcast_ws({
        "type": "healer_bridge_diag_started",
        "data": {"mode": bridge.mode},
        "timestamp": datetime.now().isoformat(),
    })
    logger.info("🔍 DEBUG diag_started broadcast done")

    try:
            result = await asyncio.wait_for(
                asyncio.get_running_loop().run_in_executor(None, bridge.run_patch_cycle),
                timeout=60.0,
            )
    except asyncio.TimeoutError:
        logger.error("⏰ HealerBridge cycle TIMEOUT (60s)")
        result = {"status": "timeout", "message": "Цикл диагностики превысил 60 секунд"}
    except Exception as exc:
        logger.error("❌ HealerBridge cycle error: %s", exc)
        result = {"status": "error", "message": str(exc)}

    broadcast_ws({
        "type": "healer_bridge_cycle_complete",
        "data": {
            "status": result.get("status") if isinstance(result, dict) else "done",
            "reports": result.get("reports") if isinstance(result, dict) else [],
            "result": result,
        },
        "timestamp": datetime.now().isoformat(),
    })

    # Broadcast рефлексии после цикла
    try:
        from healing.reflection_loop import reflect
        cycle_data = {
            "status": result.get("status") if isinstance(result, dict) else "done",
            "reports": result.get("reports") if isinstance(result, dict) else [],
            "timestamp": datetime.now().isoformat(),
            "duration_ms": result.get("duration_ms", 0) if isinstance(result, dict) else 0,
        }
        reflection = reflect([cycle_data])
        broadcast_ws({
            "type": "healer_bridge_reflection",
            "data": reflection,
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        logger.debug("Reflection broadcast skipped: %s", e)

    return {"status": "ok", "cycle": result}


@router.get("/bridge/orchestrator")
async def get_bridge_orchestrator_status():
    """Статус HEALER Orchestrator (история циклов, meta)."""
    if not _bridge_available:
        return {"status": "error", "message": "HealerBridge не доступен"}
    bridge = get_healer_bridge()
    orc = bridge.get_orchestrator()
    if orc is None:
        return {"status": "ok", "orchestrator": None}
    return {
        "status": "ok",
        "data": orc.get_status(),
        "history": orc.get_history(limit=5),
    }


@router.get("/bridge/reports/latest")
async def get_latest_reports(min_severity: str = "info"):
    """Отчёты последнего цикла HEALER диагностики."""
    if not _bridge_available:
        return {"status": "error", "message": "HealerBridge не доступен"}
    bridge = get_healer_bridge()
    reports = bridge.get_last_reports(min_severity)
    return {"status": "ok", "count": len(reports), "reports": reports}


@router.get("/bridge/reflection/latest")
async def get_latest_reflection():
    """Последняя рефлексия HEALER.

    В текущей версии ReflectionLoop возвращает агрегированные данные (stats/learnings/changes)
    на основании внутренних циклов диагностики.
    """
    # В bridge пока нет источника “latest reflection”, поэтому fallback:
    # запускаем diagnostics с auto_reflect и отдаём learnings/changes.
    try:
        reports = run_diagnostics(session_id="", auto_reflect=True, event_callback=None)
    except Exception:
        reports = []

    # ReflectionLoop считает агрегированную рефлексию на основании cycles.
    # Сейчас run_diagnostics возвращает только reports, поэтому строим минимальный cycle.
    try:
        from healing.reflection_loop import reflect

        cycle = {
            "status": "success",
            "reports": [r.to_dict() for r in reports],
            "timestamp": datetime.now().isoformat(),
            "duration_ms": 0,
        }
        reflection = reflect([cycle])
    except Exception:
        reflection = {"learnings": [], "changes": [], "stats": {"total_cycles": 1}}

    return {"status": "ok", "reflection": reflection}


# === Changes & Rollback ===


@router.get("/bridge/changes")
async def get_changes(status: str = "applied"):
    """Список применённых/откаченных изменений HEALER."""
    try:
        from healing.changes_store import get_changes_store
        store = get_changes_store()
        return {"status": "ok", "changes": store.get_by_status(status), "total": len(store.get_all())}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/bridge/rollback/{patch_id}")
async def rollback_patch(patch_id: str):
    """Откатить применённый патч HEALER по patch_id."""
    try:
        from healing.changes_store import get_changes_store
        store = get_changes_store()
        success = store.rollback(patch_id)
        return {"status": "ok" if success else "error", "rolled_back": success}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# === AutoCycle Scheduler ===

_auto_cycle_scheduler: Optional[Any] = None


def _init_auto_scheduler(bridge_instance=None):
    """Инициализирует глобальный AutoCycleScheduler (если ещё не создан)."""
    global _auto_cycle_scheduler
    if _auto_cycle_scheduler is not None:
        return
    from backend.integration.auto_cycle import AutoCycleScheduler
    _auto_cycle_scheduler = AutoCycleScheduler()
    if bridge_instance:
        _auto_cycle_scheduler.set_run_fn(bridge_instance.run_patch_cycle)


@router.get("/bridge/auto-cycle")
async def get_auto_cycle_status():
    """Статус AutoCycleScheduler."""
    if not _bridge_available:
        return {"status": "error", "message": "HealerBridge не доступен"}
    if _auto_cycle_scheduler is None:
        return {"status": "ok", "enabled": False, "interval_sec": 300, "running": False}
    return {"status": "ok", **_auto_cycle_scheduler.get_status()}


@router.post("/bridge/auto-cycle")
async def enable_auto_cycle(body: Dict[str, Any]):
    """Включить автоциклы. Тело: {"interval_sec": 300, "mode": "monitor"}"""
    if not _bridge_available:
        return {"status": "error", "message": "HealerBridge не доступен"}
    bridge = get_healer_bridge()

    _init_auto_scheduler(bridge)

    interval = body.get("interval_sec", 300)
    mode = body.get("mode")
    if mode:
        bridge.set_mode(mode)

    await _auto_cycle_scheduler.start(interval_sec=interval)
    return {"status": "ok", **_auto_cycle_scheduler.get_status()}


@router.delete("/bridge/auto-cycle")
async def disable_auto_cycle():
    """Выключить автоциклы."""
    if _auto_cycle_scheduler is None:
        return {"status": "ok", "message": "AutoCycle не был запущен"}
    await _auto_cycle_scheduler.stop()
    return {"status": "ok", **_auto_cycle_scheduler.get_status()}


@router.put("/bridge/auto-cycle")
async def reconfigure_auto_cycle(body: Dict[str, Any]):
    """Изменить настройки автоциклов. Тело: {"interval_sec": 600}"""
    if _auto_cycle_scheduler is None:
        return {"status": "error", "message": "AutoCycle не инициализирован"}
    interval = body.get("interval_sec", 300)
    mode = body.get("mode")
    if mode:
        bridge = get_healer_bridge()
        bridge.set_mode(mode)
    await _auto_cycle_scheduler.reconfigure(interval_sec=interval)
    return {"status": "ok", **_auto_cycle_scheduler.get_status()}


# ── WS Manager injection ───────────────────────────────────────────

_ws_manager: Any = None
_main_loop: Any = None  # кешируется при первом broadcast_ws


def set_ws_manager(manager: Any) -> None:
    """Внедряет WebSocket manager для broadcast'а из routes."""
    global _ws_manager
    _ws_manager = manager


def _capture_main_loop() -> None:
    """Кеширует главный event loop (вызывать только из async-контекста)."""
    global _main_loop
    if _main_loop is None:
        _main_loop = asyncio.get_running_loop()


def broadcast_ws(msg: dict) -> None:
    """Broadcast через внедрённый WS manager (из любого потока)."""
    mgr = _ws_manager

    if mgr is None:
        try:
            import __main__ as _main_mod
            mgr = getattr(_main_mod, "manager", None)
        except Exception as e:
            logger.warning(f"Operation failed: {e}")
    if mgr is None:
        logger.warning("🔍 broadcast_ws: mgr is None")
        return
    if _main_loop is None:
        logger.warning("🔍 broadcast_ws: _main_loop is None")
        return

    conn_count = len(getattr(mgr, "active_connections", []))
    logger.info("🔍 broadcast_ws: sending %s, connections=%d", msg.get("type"), conn_count)

    try:
        asyncio.run_coroutine_threadsafe(mgr.broadcast(msg), _main_loop)
    except Exception as exc:
        logger.error("🔍 broadcast_ws error: %s", exc)
