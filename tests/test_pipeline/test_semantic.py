import pytest
from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.semantic import SemanticPhase


@pytest.mark.asyncio
async def test_semantic_with_procedure():
    mock_proc = MagicMock()
    mock_proc.name = "greeting"
    mock_proc.id = "proc_1"
    mock_proc.procedure_steps = ["say hello", "introduce yourself", "ask how are they"]

    with patch("memory.semantic.get_semantic_memory") as mock_get:
        mock_sem = MagicMock()
        mock_sem.find_applicable_procedure.return_value = mock_proc
        mock_get.return_value = mock_sem

        phase = SemanticPhase()
        ctx = PipelineContext(user_message="Hello")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["procedure_name"] == "greeting"
    assert result.data["procedure_id"] == "proc_1"
    assert "say hello" in result.data["context"]


@pytest.mark.asyncio
async def test_semantic_no_procedure():
    with patch("memory.semantic.get_semantic_memory") as mock_get:
        mock_sem = MagicMock()
        mock_sem.find_applicable_procedure.return_value = None
        mock_get.return_value = mock_sem

        phase = SemanticPhase()
        ctx = PipelineContext(user_message="random text")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["procedure_name"] is None
    assert result.data["context"] == ""


@pytest.mark.asyncio
async def test_semantic_fallback():
    with patch("memory.semantic.get_semantic_memory") as mock_get:
        mock_get.side_effect = Exception("semantic unavailable")

        phase = SemanticPhase()
        ctx = PipelineContext(user_message="test")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["procedure_name"] is None
