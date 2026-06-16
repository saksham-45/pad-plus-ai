"""
Experience API — просмотр накопленного опыта Experience Layer.
"""

from fastapi import APIRouter, Query
from typing import Optional
from collections import Counter
import logging

logger = logging.getLogger("padplus.experience")

router = APIRouter(prefix="/api/v1/admin/experiences", tags=["Experience"])


@router.get("")
async def get_experiences(
    limit: int = Query(50, ge=1, le=1000),
    interaction_type: Optional[str] = Query(None, description="Фильтр по типу"),
    offset: int = Query(0, ge=0),
):
    """Статистика и список записей опыта."""
    try:
        from core.experience.store import ExperienceStore
        store = ExperienceStore()
        all_records = store.load_all()

        total = len(all_records)
        if interaction_type:
            filtered = [r for r in all_records if r.get("interaction_type") == interaction_type]
        else:
            filtered = list(all_records)

        type_dist = dict(Counter(r.get("interaction_type", "unknown") for r in all_records))
        avg_significance = (
            round(sum(r.get("significance", 0) for r in all_records) / total, 3)
            if total > 0 else 0.0
        )

        records = filtered[offset:offset + limit]

        return {
            "total": total,
            "returned": len(records),
            "offset": offset,
            "limit": limit,
            "filter_type": interaction_type,
            "avg_significance": avg_significance,
            "type_distribution": type_dist,
            "records": records,
        }
    except Exception as e:
        logger.error("Failed to load experiences: %s", e)
        return {
            "total": 0,
            "returned": 0,
            "offset": 0,
            "limit": limit,
            "filter_type": interaction_type,
            "avg_significance": 0.0,
            "type_distribution": {},
            "records": [],
            "error": str(e),
        }


@router.get("/stats")
async def get_experience_stats():
    """Краткая сводка по опыту."""
    try:
        from core.experience.store import ExperienceStore
        store = ExperienceStore()
        all_records = store.load_all()

        total = len(all_records)
        type_dist = dict(Counter(r.get("interaction_type", "unknown") for r in all_records))
        avg_sig = round(sum(r.get("significance", 0) for r in all_records) / total, 3) if total > 0 else 0.0

        high_impact = sum(1 for r in all_records if r.get("significance", 0) >= 0.7)
        contradictions = sum(1 for r in all_records if r.get("interaction_type") == "contradiction")

        return {
            "total": total,
            "type_distribution": type_dist,
            "avg_significance": avg_sig,
            "high_impact_count": high_impact,
            "contradiction_count": contradictions,
        }
    except Exception as e:
        return {"total": 0, "type_distribution": {}, "avg_significance": 0.0, "error": str(e)}
