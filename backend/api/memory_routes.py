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
        from memory.episodic import get_episodic_memory
        mem = get_episodic_memory()
        stats = mem.get_stats() if hasattr(mem, 'get_stats') else {}
        result["episodic"] = {
            "total_episodes": stats.get("total_episodes", stats.get("total_episodic_memory", 0)),
            "dialogs": stats.get("dialogs", stats.get("total_dialogs", 0)),
            "topics": stats.get("topics", []),
        }
    except Exception as e:
        result["episodic"] = {"status": "unavailable", "error": str(e)[:100]}

    # Semantic memory
    try:
        from memory.semantic import get_semantic_memory
        mem = get_semantic_memory()
        stats = mem.get_stats() if hasattr(mem, 'get_stats') else {}
        result["semantic"] = {
            "concepts": stats.get("concepts", stats.get("total_concepts", 0)),
            "procedures": stats.get("procedures", stats.get("total_procedures", 0)),
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
            "total_principles": stats.get("total_principles", stats.get("total_roots", 0)),
            "preview": ctx[:300] if ctx else "",
        }
    except Exception as e:
        result["roots"] = {"status": "unavailable", "error": str(e)[:100]}

    # RAG stats
    try:
        from memory.rag import get_rag
        mem = get_rag()
        stats = mem.get_stats() if hasattr(mem, 'get_stats') else {}
        result["rag"] = {
            "documents": stats.get("documents", stats.get("total_documents", 0)),
            "queries_today": stats.get("queries_today", 0),
        }
    except Exception as e:
        result["rag"] = {"status": "unavailable", "error": str(e)[:100]}

    # Persona
    try:
        from memory.persona import get_persona
        mem = get_persona()
        stats = mem.get_stats() if hasattr(mem, 'get_stats') else {}
        result["persona"] = {
            "traits": stats.get("traits", stats.get("traits_count", 0)),
        }
    except Exception as e:
        result["persona"] = {"status": "unavailable", "error": str(e)[:100]}

    # Meta-learner
    try:
        from core.xray.meta_learner import get_meta_learner
        mem = get_meta_learner()
        stats = mem.get_stats() if hasattr(mem, 'get_stats') else {}
        result["meta_learner"] = {
            "total_trials": stats.get("total_trials", 0),
            "strategies": stats.get("strategies", {}),
        }
    except Exception as e:
        result["meta_learner"] = {"status": "unavailable", "error": str(e)[:100]}

    # Feedback
    try:
        from core.feedback_system import get_feedback_system
        mem = get_feedback_system()
        stats = mem.get_stats() if hasattr(mem, 'get_stats') else {}
        result["feedback"] = {
            "total_ratings": stats.get("total_ratings", 0),
            "positive": stats.get("positive", 0),
            "negative": stats.get("negative", 0),
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
