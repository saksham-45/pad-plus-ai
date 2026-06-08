from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.events import EventsBroadcastPhase


async def test_events_broadcast():
    with patch("core.event_bus.get_event_bus") as mock_get:
        mock_bus = MagicMock()
        mock_get.return_value = mock_bus

        phase = EventsBroadcastPhase()
        ctx = PipelineContext(
            user_message="С‚РµСЃС‚",
            context={
                "confidence": 0.8,
                "rag_used": True,
                "intent": "chat_general",
            },
        )
        result = await phase.execute(ctx)

    assert result.success
    assert mock_bus.emit.call_count == 2


async def test_events_fallback():
    with patch("core.event_bus.get_event_bus") as mock_get:
        mock_get.side_effect = Exception("event bus unavailable")

        phase = EventsBroadcastPhase()
        ctx = PipelineContext(user_message="С‚РµСЃС‚", context={})
        result = await phase.execute(ctx)

    assert result.success
