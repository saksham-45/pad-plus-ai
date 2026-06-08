from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.rag import RagPhase


async def test_rag_with_context():
    with patch("memory.rag.get_rag") as mock_get:
        mock_rag = MagicMock()
        mock_rag.get_context.return_value = "СЂРµР»РµРІР°РЅС‚РЅС‹Р№ РєРѕРЅС‚РµРєСЃС‚"
        mock_get.return_value = mock_rag

        phase = RagPhase()
        ctx = PipelineContext(user_message="РІРѕРїСЂРѕСЃ", context={"user_id": "user_1"})
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["rag_used"] is True
    assert result.data["sources"]["count"] == 1
    assert result.data["context"] == "СЂРµР»РµРІР°РЅС‚РЅС‹Р№ РєРѕРЅС‚РµРєСЃС‚"


async def test_rag_no_context():
    with patch("memory.rag.get_rag") as mock_get:
        mock_rag = MagicMock()
        mock_rag.get_context.return_value = None
        mock_get.return_value = mock_rag

        phase = RagPhase()
        ctx = PipelineContext(user_message="РІРѕРїСЂРѕСЃ")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["rag_used"] is False
    assert result.data["context"] == ""


async def test_rag_fallback():
    with patch("memory.rag.get_rag") as mock_get:
        mock_get.side_effect = Exception("rag unavailable")

        phase = RagPhase()
        ctx = PipelineContext(user_message="С‚РµСЃС‚")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["rag_used"] is False
