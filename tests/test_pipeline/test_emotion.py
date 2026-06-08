from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.emotion import EmotionPhase


async def test_emotion_success():
    mock_state = MagicMock()
    mock_state.to_dict.return_value = {"СѓРґРѕРІРѕР»СЊСЃС‚РІРёРµ": 0.7, "РІРѕР·Р±СѓР¶РґРµРЅРёРµ": 0.5}
    mock_state.get_style.return_value = {"tone": "warm", "verbosity": "medium"}

    with patch("emotion.pad_model.get_pad_model") as mock_get:
        mock_pad = MagicMock()
        mock_pad.get_state.return_value = mock_state
        mock_get.return_value = mock_pad

        phase = EmotionPhase()
        ctx = PipelineContext(user_message="РџСЂРёРІРµС‚")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["state"]["СѓРґРѕРІРѕР»СЊСЃС‚РІРёРµ"] == 0.7
    assert result.data["style"]["tone"] == "warm"


async def test_emotion_fallback():
    with patch("emotion.pad_model.get_pad_model") as mock_get:
        mock_get.side_effect = Exception("pad unavailable")

        phase = EmotionPhase()
        ctx = PipelineContext(user_message="С‚РµСЃС‚")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["state"] == {}
    assert result.data["style"] == {}
