import asyncio
import logging
import traceback
from datetime import datetime

logger = logging.getLogger("padplus.health")


async def check_impulse():
    try:
        from scripts.impulse import get_impulse_core
        core = get_impulse_core()
        return {
            "status": "ok",
            "primary_label": core.get_primary_label(),
            "stack_depth": core.stack_depth(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_emotion():
    try:
        from emotion.pad_model import get_pad_model
        pad = get_pad_model()
        state = pad.get_state()
        return {
            "status": "ok",
            "tone": state.get_style().get("tone", "unknown"),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_memory():
    results = {}
    checks = {
        "rag": ("memory.rag", "get_rag", "get_stats"),
        "episodic": ("memory.episodic", "get_episodic_memory", "get_stats"),
        "semantic": ("memory.semantic", "get_semantic_memory", "get_stats"),
        "persona": ("memory.persona", "get_persona", "get_stats"),
        "roots": ("memory.roots", "get_roots_memory", "get_stats"),
        "hygiene": ("memory.hygiene", "get_hygiene", "get_stats"),
    }
    for name, (module_path, factory, method) in checks.items():
        try:
            mod = __import__(module_path, fromlist=[factory])
            instance = getattr(mod, factory)()
            stats = getattr(instance, method)() if hasattr(instance, method) else {}
            results[name] = {"status": "ok", "size": len(stats) if isinstance(stats, (list, dict)) else str(stats)[:50]}
        except Exception as e:
            results[name] = {"status": "error", "error": str(e)[:80]}
    return results


async def check_xray():
    try:
        from core.xray import (
            get_trace_collector, get_thought_visualizer,
            get_xray_broadcaster, get_xray_history
        )
        return {
            "status": "ok",
            "trace_collector": "ok" if get_trace_collector() else "error",
            "broadcaster": "ok" if get_xray_broadcaster() else "error",
            "history": "ok" if get_xray_history() else "error",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_pipeline():
    try:
        from core.pipeline import get_pipeline
        pipe = get_pipeline()
        return {"status": "ok", "phases": len(pipe.phases) if hasattr(pipe, 'phases') else "available"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_healer():
    try:
        from api.healer_routes import router
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_database():
    try:
        from core.supabase_client import check_database_connection
        connected = check_database_connection()
        return {"status": "ok" if connected else "disconnected"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_providers():
    try:
        from runtime.llm_service import get_llm_service
        llm = get_llm_service()
        providers = llm.list_providers() if hasattr(llm, 'list_providers') else []
        return {"status": "ok", "count": len(providers)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def deep_health():
    start = datetime.now()

    checks = {
        "impulse": check_impulse(),
        "emotion": check_emotion(),
        "xray": check_xray(),
        "pipeline": check_pipeline(),
        "healer": check_healer(),
        "database": check_database(),
        "providers": check_providers(),
    }

    memory_check = check_memory()
    results = {}

    for name, coro in checks.items():
        try:
            results[name] = await asyncio.wait_for(coro, timeout=5)
        except asyncio.TimeoutError:
            results[name] = {"status": "timeout"}

    try:
        results["memory"] = await asyncio.wait_for(memory_check, timeout=10)
    except asyncio.TimeoutError:
        results["memory"] = {"status": "timeout"}

    elapsed = (datetime.now() - start).total_seconds()

    all_ok = all(
        v.get("status") == "ok"
        for k, v in results.items()
        if isinstance(v, dict) and k != "memory"
    )

    critical_failed = any(
        results.get(c, {}).get("status") == "error"
        for c in ["impulse", "emotion", "pipeline", "database"]
    )

    return {
        "status": "healthy" if all_ok else ("unhealthy" if critical_failed else "degraded"),
        "timestamp": start.isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "checks": results,
    }
