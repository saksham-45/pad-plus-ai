"""
Tests for ReflectionPhase — core.meta_controller may not exist.
"""

import pytest

from core.pipeline import PipelineContext
from core.pipeline.phases.reflection import ReflectionPhase


async def test_reflection_success():
    phase = ReflectionPhase()
    ctx = PipelineContext(
        user_message="test",
        context={
            "pipeline_success": True,
            "strategy": "simple",
            "execution_time_ms": 500,
        },
    )
    result = await phase.execute(ctx)
    assert result.success


async def test_reflection_fallback():
    phase = ReflectionPhase()
    ctx = PipelineContext(user_message="test", context={})
    result = await phase.execute(ctx)
    assert result.success
