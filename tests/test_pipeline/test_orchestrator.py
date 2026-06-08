"""
Integration tests for PipelineExecutor.
"""

import pytest

from core.pipeline import PipelineExecutor, PipelineResult


@pytest.mark.slow
async def test_orchestrator_execute_full():
    executor = PipelineExecutor()
    result = await executor.execute(
        user_message="Hello",
        context={"user_id": "test"},
        session_id="session_1",
        api_key=None,
        provider=None,
    )
    assert isinstance(result, PipelineResult)
    assert result.success
    assert result.strategy in ("simple", "retrieval", "reasoning")
    assert result.intent == "chat_general"


async def test_orchestrator_anti_loop_blocks():
    executor = PipelineExecutor()
    executor._anti_loop_history = ["test"] * 4
    result = await executor.execute(user_message="test", context={})
    assert result.success
    assert "loop" in result.response.lower() or "цикл" in result.response.lower()


async def test_orchestrator_strategy_detection():
    executor = PipelineExecutor()
    assert executor._determine_strategy("Hello") == "simple"
    assert executor._determine_strategy("почему небо голубое и почему оно меняет цвет в разное время суток") == "reasoning"
    assert executor._determine_strategy("придумай историю") == "creative"
    assert executor._determine_strategy("запомни этот факт") == "learning"
    assert executor._determine_strategy("How are you?") == "simple"


async def test_orchestrator_get_stats():
    executor = PipelineExecutor()
    stats = executor.get_stats()
    assert stats["version"] == "4.0"
    assert stats["state"] == "healthy"
    assert stats["total_calls"] >= 0
