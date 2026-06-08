from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.roots import RootsPhase


async def test_roots_success():
    with patch("memory.roots.get_roots_memory") as mock_get:
        mock_roots = MagicMock()
        mock_roots.export_for_context.return_value = "РєРѕСЂРЅРµРІС‹Рµ РїСЂРёРЅС†РёРїС‹: ..."
        mock_get.return_value = mock_roots

        phase = RootsPhase()
        ctx = PipelineContext(user_message="С‚РµСЃС‚")
        result = await phase.execute(ctx)

    assert result.success
    assert "РєРѕСЂРЅРµРІС‹Рµ РїСЂРёРЅС†РёРїС‹" in result.data["context"]


async def test_roots_fallback():
    with patch("memory.roots.get_roots_memory") as mock_get:
        mock_get.side_effect = Exception("roots unavailable")

        phase = RootsPhase()
        ctx = PipelineContext(user_message="С‚РµСЃС‚")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["context"] == ""
