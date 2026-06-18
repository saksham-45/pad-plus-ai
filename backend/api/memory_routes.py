"""
Memory Dashboard — единая точка сбора статистики всех систем памяти.

Агрегирует: эпизоды, семантика, консолидация, RAG, roots, persona, meta-learner, feedback.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
import logging

logger = logging.getLogger("padplus.memory_dashboard")

router = APIRouter(prefix="/api/v1/memory", tags=["Memory Dashboard"])


@router.get("/dashboard")
async def get_memory_dashboard():
    """Агрегированная статистика всех систем памяти"""
    result = {}

    # Episodic memory
    try:
        from memory import get_episodic_memory
        mem = get_episodic_memory()
        stats = mem.get_stats() if hasattr(mem, 'get_stats') else {}
        by_topic = stats.get("by_topic", {})
        result["episodic"] = {
            "total_episodes": stats.get("total_episodes", 0),
            "total_relations": stats.get("total_relations", 0),
            "avg_significance": stats.get("avg_significance", 0),
            "topics": list(by_topic.keys())[:8],
        }
    except Exception as e:
        result["episodic"] = {"status": "unavailable", "error": str(e)[:100]}

    # Semantic memory
    try:
        from memory import get_semantic_memory
        mem = get_semantic_memory()
        stats = mem.get_stats() if hasattr(mem, 'get_stats') else {}
        by_type = stats.get("by_type", {})
        procedures = stats.get("procedures", {})
        result["semantic"] = {
            "total_knowledge": stats.get("total_knowledge", 0),
            "concepts": by_type.get("conceptual", 0),
            "procedures": procedures.get("count", 0) if isinstance(procedures, dict) else 0,
            "avg_confidence": stats.get("avg_confidence", 0),
        }
    except Exception as e:
        result["semantic"] = {"status": "unavailable", "error": str(e)[:100]}

    # Roots (core principles)
    try:
        from memory.roots import get_roots_memory
        mem = get_roots_memory()
        stats = mem.get_stats() if hasattr(mem, 'get_stats') else {}
        ctx = mem.export_for_context(max_items=5) if hasattr(mem, 'export_for_context') else ""
        result["roots"] = {
            "total_principles": stats.get("total_roots", stats.get("total_principles", 0)),
            "by_category": stats.get("by_category", {}),
            "immutable_count": stats.get("immutable_count", 0),
            "preview": ctx[:500] if ctx else "",
        }
    except Exception as e:
        result["roots"] = {"status": "unavailable", "error": str(e)[:100]}

    # RAG stats
    try:
        from memory.rag import get_rag
        mem = get_rag()
        stats = mem.get_stats() if hasattr(mem, 'get_stats') else {}
        result["rag"] = {
            "total_dialogs": stats.get("total_dialogs", 0),
        }
    except Exception as e:
        result["rag"] = {"status": "unavailable", "error": str(e)[:100]}

    # Persona
    try:
        from memory.persona import get_persona
        mem = get_persona()
        stats = mem.get_stats() if hasattr(mem, 'get_stats') else {}
        result["persona"] = {
            "traits": stats.get("traits_count", 0),
            "users_known": stats.get("users_known", 0),
            "total_interactions": stats.get("total_interactions", 0),
        }
    except Exception as e:
        result["persona"] = {"status": "unavailable", "error": str(e)[:100]}

    # Meta-learner
    try:
        from core.xray.meta_learner import get_meta_learner
        mem = get_meta_learner()
        stats = mem.get_stats() if hasattr(mem, 'get_stats') else {}
        strategies_dict = stats.get("strategies", {})
        result["meta_learner"] = {
            "total_decisions": stats.get("total_decisions", 0),
            "total_success": stats.get("total_success", 0),
            "overall_success_rate": stats.get("overall_success_rate", 0),
            "strategies_count": len(strategies_dict) if isinstance(strategies_dict, dict) else 0,
        }
    except Exception as e:
        result["meta_learner"] = {"status": "unavailable", "error": str(e)[:100]}

    # Feedback
    try:
        from core.feedback_system import get_feedback_system
        mem = get_feedback_system()
        stats = mem.get_stats() if hasattr(mem, 'get_stats') else {}
        result["feedback"] = {
            "total_feedback": stats.get("total_feedback", 0),
            "positive": stats.get("positive_count", 0),
            "negative": stats.get("negative_count", 0),
            "satisfaction_rate": stats.get("satisfaction_rate", 0),
        }
    except Exception as e:
        result["feedback"] = {"status": "unavailable", "error": str(e)[:100]}

    return result


@router.post("/consolidation/trigger")
async def trigger_consolidation():
    """Ручной запуск консолидации памяти"""
    try:
        from memory.consolidation import get_consolidator
        consolidator = get_consolidator()
        result = consolidator.run_scheduled_consolidation()
        return {"success": True, "message": "Консолидация запущена", "details": str(result)[:200]}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}
