"""
Feedback API — сбор обратной связи от пользователя.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger("padplus.feedback")

router = APIRouter(prefix="/api/v1/feedback", tags=["Feedback"])


class FeedbackCreate(BaseModel):
    dialog_id: Optional[str] = None
    message_id: Optional[str] = None
    rating: int  # 1 like, -1 dislike
    comment: Optional[str] = None


class FeedbackStats(BaseModel):
    total_ratings: int = 0
    positive: int = 0
    negative: int = 0


@router.post("")
async def submit_feedback(
    data: FeedbackCreate,
    authorization: Optional[str] = Header(None)
):
    """Отправить оценку ответа"""
    if data.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="Рейтинг должен быть 1 (нравится) или -1 (не нравится)")

    try:
        from core.supabase_client import get_supabase
        supabase = get_supabase()

        user_id = None
        if authorization and authorization.startswith("Bearer "):
            try:
                token = authorization[7:]
                user_resp = supabase.auth.get_user(token)
                if user_resp and user_resp.user:
                    user_id = user_resp.user.id
            except Exception as e:
                logger.warning(f"{__name__} error: {e}")

        record = {
            "rating": data.rating,
            "comment": data.comment,
            "dialog_id": data.dialog_id,
            "message_id": data.message_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
        }

        supabase.table("feedback").insert(record).execute()
        return {"success": True, "message": "Спасибо за оценку!"}
    except Exception as e:
        logger.error(f"Feedback save error: {e}")
        return {"success": False, "message": "Ошибка сохранения оценки"}


@router.get("/stats")
async def get_feedback_stats():
    """Статистика обратной связи"""
    try:
        from core.feedback_system import get_feedback_system
        mem = get_feedback_system()
        stats = mem.get_stats() if hasattr(mem, 'get_stats') else {}
        return {
            "total_ratings": stats.get("total_ratings", stats.get("total", 0)),
            "positive": stats.get("positive", stats.get("likes", 0)),
            "negative": stats.get("negative", stats.get("dislikes", 0)),
        }
    except Exception as e:
        logger.warning("Ошибка получения статистики feedback: %s", e)
        return {"total_ratings": 0, "positive": 0, "negative": 0}
