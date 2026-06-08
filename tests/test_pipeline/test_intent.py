from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.intent import IntentPhase


async def test_intent_success():
    mock_route = MagicMock()
    mock_route.intent.value = "chat_general"
    mock_route.pipeline = [MagicMock(name="stage1"), MagicMock(name="stage2")]

    with patch("core.intent_router.get_router") as mock_get:
        mock_router = MagicMock()
        mock_router.route.return_value = mock_route
        mock_get.return_value = mock_router

        phase = IntentPhase()
        ctx = PipelineContext(user_message="РџСЂРёРІРµС‚")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["intent"] == "chat_general"
    assert len(result.data["pipeline_meta"]) == 2


async def test_intent_fallback():
    with patch("core.intent_router.get_router") as mock_get:
        mock_get.side_effect = Exception("router unavailable")

        phase = IntentPhase()
        ctx = PipelineContext(user_message="С‚РµСЃС‚")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["intent"] == "chat_general"
