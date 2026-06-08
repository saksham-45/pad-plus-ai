"""
Knowledge Graph API — доступ к графу знаний.
"""

from fastapi import APIRouter, Query
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("padplus.knowledge")

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge Graph"])


@router.get("/search")
async def search_concepts(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100)
):
    """Поиск концепций в графе знаний"""
    try:
        from knowledge.graph import get_knowledge_graph
        graph = get_knowledge_graph()
        concepts = graph.find_concepts(q, limit=limit)
        return {
            "query": q,
            "concepts": [c.to_dict() for c in concepts],
            "total": len(concepts),
        }
    except Exception as e:
        logger.error(f"Knowledge graph search error: {e}")
        return {"query": q, "concepts": [], "total": 0, "error": str(e)}


@router.get("/related/{concept_id}")
async def get_related_concepts(
    concept_id: str,
    depth: int = Query(default=1, ge=1, le=3)
):
    """Связанные концепции"""
    try:
        from knowledge.graph import get_knowledge_graph
        graph = get_knowledge_graph()
        related = graph.get_related(concept_id, depth=depth)
        concept = graph.get_concept(concept_id)
        return {
            "concept": concept.to_dict() if concept else None,
            "related": [r.to_dict() for r in related],
            "total": len(related),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/stats")
async def get_knowledge_stats():
    """Статистика графа знаний"""
    try:
        from knowledge.graph import get_knowledge_graph
        graph = get_knowledge_graph()
        stats = graph.get_stats()
        return stats
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}


@router.get("/graph")
async def get_full_graph(limit: int = Query(default=50, ge=1, le=200)):
    """Полный граф для визуализации"""
    try:
        from knowledge.graph import get_knowledge_graph
        graph = get_knowledge_graph()
        full = graph.to_dict()
        nodes = full.get("concepts", [])[:limit]
        edges = full.get("relations", [])
        edge_ids = {n["id"] for n in nodes}
        edges = [e for e in edges if e.get("source_id") in edge_ids and e.get("target_id") in edge_ids][:limit * 2]
        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}
