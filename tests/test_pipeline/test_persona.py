from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.persona import PersonaPhase


async def test_persona_with_user():
    mock_persona = MagicMock()
    mock_persona.get_context_for_prompt.return_value = "РєРѕРЅС‚РµРєСЃС‚ Р»РёС‡РЅРѕСЃС‚Рё"

    with patch("memory.user_persona.get_user_persona_manager") as mock_get:
        mock_mgr = MagicMock()
        mock_mgr.get_persona.return_value = mock_persona
        mock_get.return_value = mock_mgr

        phase = PersonaPhase()
        ctx = PipelineContext(
            user_message="РџСЂРёРІРµС‚",
            context={"user_id": "user_1", "intent": "chat_general"},
        )
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["context"] == "РєРѕРЅС‚РµРєСЃС‚ Р»РёС‡РЅРѕСЃС‚Рё"
    assert result.data["user_id"] == "user_1"
    mock_persona.record_interaction.assert_called_once()


async def test_persona_without_user():
    with patch("memory.persona.get_persona") as mock_get:
        mock_p = MagicMock()
        mock_p.get_persona_context.return_value = "РѕР±С‰Р°СЏ Р»РёС‡РЅРѕСЃС‚СЊ"
        mock_get.return_value = mock_p

        phase = PersonaPhase()
        ctx = PipelineContext(user_message="РџСЂРёРІРµС‚")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["context"] == "РѕР±С‰Р°СЏ Р»РёС‡РЅРѕСЃС‚СЊ"
    assert result.data["user_id"] is None
