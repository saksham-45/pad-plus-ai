"""
📡 Sentry Webhook Routes

Принимает webhook-уведомления от Sentry при новых ошибках,
запускает HEALER диагностику и помечает issue тегами.
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("padplus.api.sentry")

router = APIRouter(prefix="/api/v1/sentry", tags=["sentry"])


@router.get("/webhook")
async def verify_sentry_webhook(request: Request):
    """Sentry отправляет GET с ?sentry_challenge=... для верификации эндпоинта."""
    challenge = request.query_params.get("sentry_challenge")
    if challenge:
        return JSONResponse(content={"challenge": challenge})
    return {"status": "ok"}


@router.post("/webhook")
async def handle_sentry_webhook(request: Request):
    """Webhook от Sentry при новой ошибке (action=created)."""
    try:
        payload = await request.json()
    except Exception:
        return {"handled": False, "error": "invalid json"}

    from core.sentry_healer_bridge import handle_sentry_webhook as bridge_handler

    result = await bridge_handler(payload)

    return result
