import pytest
from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.episodic import EpisodicPhase


@pytest.mark.asyncio
async def test_episodic_with_similar():
    mock_ep = MagicMock()
    mock_ep.topic = "greeting"
    mock_ep.user_message = "Hello, how are you?"
    mock_ep.ai_response = "Hello! I'm fine!"

    with patch("memory.episodic.get_episodic_memory") as mock_get:
        mock_mem = MagicMock()
        mock_mem.search_episodes.return_value = [mock_ep]
        mock_get.return_value = mock_mem

        phase = EpisodicPhase()
        ctx = PipelineContext(user_message="Hello", context={"user_id": "user_1"})
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["count"] == 1
    assert "greeting" in result.data["context"]


@pytest.mark.asyncio
async def test_episodic_no_similar():
    with patch("memory.episodic.get_episodic_memory") as mock_get:
        mock_mem = MagicMock()
        mock_mem.search_episodes.return_value = None
        mock_get.return_value = mock_mem

        phase = EpisodicPhase()
        ctx = PipelineContext(user_message="new query")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["context"] == ""
    assert result.data["count"] == 0


@pytest.mark.asyncio
async def test_episodic_fallback():
    with patch("memory.episodic.get_episodic_memory") as mock_get:
        mock_get.side_effect = Exception("episodic unavailable")

        phase = EpisodicPhase()
        ctx = PipelineContext(user_message="test")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["context"] == ""
