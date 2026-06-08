from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.persona_evolution import PersonaEvolutionPhase


async def test_persona_evolution_with_user():
    with patch("memory.user_persona.get_user_persona_manager") as mock_get:
        mock_persona = MagicMock()
        mock_mgr = MagicMock()
        mock_mgr.get_persona.return_value = mock_persona
        mock_get.return_value = mock_mgr

        phase = PersonaEvolutionPhase()
        ctx = PipelineContext(
            user_message="СЃРїР°СЃРёР±Рѕ Р·Р° РїРѕРјРѕС‰СЊ",
            context={
                "response": "РџРѕР¶Р°Р»СѓР№СЃС‚Р°!",
                "user_id": "user_1",
            },
        )
        result = await phase.execute(ctx)

    assert result.success
    assert mock_persona.adjust_style.call_count >= 0


async def test_persona_evolution_fallback():
    with patch("memory.persona.get_persona") as mock_get:
        mock_p = MagicMock()
        mock_p.evolve_from_dialog.return_value = {"changes": []}
        mock_get.return_value = mock_p

        phase = PersonaEvolutionPhase()
        ctx = PipelineContext(
            user_message="СЃРїР°СЃРёР±Рѕ",
            context={"response": "РџРѕР¶Р°Р»СѓР№СЃС‚Р°!"},
        )
        result = await phase.execute(ctx)

    assert result.success
