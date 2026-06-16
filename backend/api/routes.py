"""
API Routes — LLM Service (OpenRouter & GigaChat)

Минимальный набор endpoints для совместимости
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/api/info")
async def api_root():
    """Корневой эндпоинт API"""
    return {
        "name": "PAD+ AI API",
        "version": "4.0",
        "message": "Use /api/v1/* endpoints"
    }
