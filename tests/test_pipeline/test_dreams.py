from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.dreams import DreamsPhase


async def test_dreams_success():
    with patch("core.dreams.get_dream_system") as mock_get:
        mock_dreams = MagicMock()
        mock_get.return_value = mock_dreams

        phase = DreamsPhase()
        ctx = PipelineContext(user_message="С‚РµСЃС‚")
        result = await phase.execute(ctx)

    assert result.success
    mock_dreams.record_activity.assert_called_once()


async def test_dreams_fallback():
    with patch("core.dreams.get_dream_system") as mock_get:
        mock_get.side_effect = Exception("dreams unavailable")

        phase = DreamsPhase()
        ctx = PipelineContext(user_message="С‚РµСЃС‚")
        result = await phase.execute(ctx)

    assert result.success
