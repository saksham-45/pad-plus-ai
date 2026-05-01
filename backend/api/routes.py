"""
API Routes — LiteLLM Only

Минимальный набор endpoints для совместимости
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def api_root():
    """Корневой эндпоинт"""
    return {
        "name": "PAD+ AI API",
        "version": "4.0 (LiteLLM)",
        "message": "Use /api/v1/* endpoints"
    }
