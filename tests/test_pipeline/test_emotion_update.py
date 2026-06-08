from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.emotion_update import EmotionUpdatePhase


async def test_emotion_update_success():
    with patch("emotion.pad_model.get_pad_model") as mock_get:
        mock_pad = MagicMock()
        mock_get.return_value = mock_pad

        phase = EmotionUpdatePhase()
        ctx = PipelineContext(
            user_message="СЃРїР°СЃРёР±Рѕ",
            context={"response": "Р’СЃРµРіРґР° РїРѕР¶Р°Р»СѓР№СЃС‚Р°!"},
        )
        result = await phase.execute(ctx)

    assert result.success
    mock_pad.apply_event.assert_called_once_with("new_knowledge", 0.2)


async def test_emotion_update_error():
    with patch("emotion.pad_model.get_pad_model") as mock_get:
        mock_get.side_effect = Exception("pad unavailable")

        phase = EmotionUpdatePhase()
        ctx = PipelineContext(user_message="С‚РµСЃС‚", context={})
        result = await phase.execute(ctx)

    assert result.success
