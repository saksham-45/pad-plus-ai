"""
Impulse API — REST-интерфейс к импульсному ядру PAD+

Позволяет:
- Получать текущий вектор импульсов
- Устанавливать веса (отдельные размерности или целиком)
- Работать со стеком (push/pop)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import logging

logger = logging.getLogger("padplus.impulse")

router = APIRouter(prefix="/api/v1/impulse", tags=["Impulse Core"])


# === Pydantic модели запросов/ответов ===

class DimensionOut(BaseModel):
    label: str
    question: str
    weight: float


class ImpulseOut(BaseModel):
    primary_question: str
    primary_label: str
    dimensions: list[DimensionOut]
    stack_depth: int
    created_at: str
    modified_at: str


class SetWeightsIn(BaseModel):
    weights: Dict[str, float]


class SetQuestionIn(BaseModel):
    question: str


class PushOut(BaseModel):
    success: bool
    stack_depth: int


class PopOut(BaseModel):
    success: bool
    stack_depth: int


class ImpulseStackOut(BaseModel):
    depth: int
    states: list[dict] = []


# === Эндпоинты ===

@router.get("", response_model=ImpulseOut)
async def get_impulse():
    """Получить текущее состояние импульсного ядра"""
    try:
        from scripts.impulse import get_impulse_core
        core = get_impulse_core()
        return ImpulseOut(
            primary_question=core.get_primary_question(),
            primary_label=core.get_primary_label(),
            dimensions=[DimensionOut(**d.to_dict()) for d in core.dimensions],
            stack_depth=core.stack_depth(),
            created_at=core.created_at,
            modified_at=core.modified_at,
        )
    except Exception as e:
        logger.error(f"Error getting impulse: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("", response_model=ImpulseOut)
async def set_impulse(weights: SetWeightsIn):
    """Установить веса импульсов (например: {"understand": 0.7, "create": 0.3})"""
    try:
        from scripts.impulse import set_impulse, get_impulse_core
        set_impulse(weights.weights)
        core = get_impulse_core()
        return ImpulseOut(
            primary_question=core.get_primary_question(),
            primary_label=core.get_primary_label(),
            dimensions=[DimensionOut(**d.to_dict()) for d in core.dimensions],
            stack_depth=core.stack_depth(),
            created_at=core.created_at,
            modified_at=core.modified_at,
        )
    except Exception as e:
        logger.error(f"Error setting impulse: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/question", response_model=ImpulseOut)
async def set_impulse_by_question(data: SetQuestionIn):
    """Установить импульс по строке вопроса (обратная совместимость)"""
    try:
        from scripts.impulse import set_impulse_by_question, get_impulse_core
        set_impulse_by_question(data.question)
        core = get_impulse_core()
        return ImpulseOut(
            primary_question=core.get_primary_question(),
            primary_label=core.get_primary_label(),
            dimensions=[DimensionOut(**d.to_dict()) for d in core.dimensions],
            stack_depth=core.stack_depth(),
            created_at=core.created_at,
            modified_at=core.modified_at,
        )
    except Exception as e:
        logger.error(f"Error setting impulse by question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/push", response_model=PushOut)
async def push_impulse():
    """Сохранить текущее состояние в стек и очистить"""
    try:
        from scripts.impulse import push_impulse, get_impulse_core
        push_impulse()
        core = get_impulse_core()
        return PushOut(success=True, stack_depth=core.stack_depth())
    except Exception as e:
        logger.error(f"Error pushing impulse: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pop", response_model=PopOut)
async def pop_impulse():
    """Восстановить предыдущее состояние из стека"""
    try:
        from scripts.impulse import pop_impulse, get_impulse_core
        success = pop_impulse()
        core = get_impulse_core()
        return PopOut(success=success, stack_depth=core.stack_depth())
    except Exception as e:
        logger.error(f"Error popping impulse: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/labels", response_model=dict)
async def get_impulse_labels():
    """Получить все известные метки импульсов"""
    try:
        from scripts.impulse import IMPULSE_LABELS
        return IMPULSE_LABELS
    except Exception as e:
        logger.error(f"Error getting labels: {e}")
        raise HTTPException(status_code=500, detail=str(e))
