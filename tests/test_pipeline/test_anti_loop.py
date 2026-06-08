import pytest
from unittest.mock import MagicMock

from core.pipeline import PipelineContext, PhaseResult
from core.pipeline.phases.anti_loop import AntiLoopPhase


async def test_no_block():
    executor = MagicMock()
    executor._check_anti_loop.return_value = None
    phase = AntiLoopPhase(executor)
    ctx = PipelineContext(user_message="РџСЂРёРІРµС‚")
    result = await phase.execute(ctx)
    assert result.success
    assert result.data["blocked"] is False


async def test_block_on_repeat():
    executor = MagicMock()
    executor._check_anti_loop.return_value = "РћР±РЅР°СЂСѓР¶РµРЅ С†РёРєР»"
    phase = AntiLoopPhase(executor)
    ctx = PipelineContext(user_message="РџСЂРёРІРµС‚")
    result = await phase.execute(ctx)
    assert result.success
    assert result.data["blocked"] is True
    assert "С†РёРєР»" in result.data["warning"]
