from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.response_guard import ResponseGuardPhase


async def test_response_guard_success():
    with patch("core.guard.response_guard.get_response_guard") as mock_g:
        with patch("core.guard.self_healing.get_self_healing_guard") as mock_sh:
            with patch("core.guard.tone_engine.get_tone_engine") as mock_te:
                with patch("core.guard.cognitive_layer.get_cognitive_layer") as mock_cl:
                    mock_guard = MagicMock()
                    mock_guard.process.return_value = "С‡РёСЃС‚С‹Р№ РѕС‚РІРµС‚"
                    mock_g.return_value = mock_guard

                    mock_sh_inst = MagicMock()
                    mock_sh.return_value = mock_sh_inst

                    mock_tone = MagicMock()
                    mock_tone.get_emotion_from_context.return_value = "warm"
                    mock_tone.apply.return_value = "С‚С‘РїР»С‹Р№ РѕС‚РІРµС‚"
                    mock_te.return_value = mock_tone

                    mock_cl_inst = MagicMock()
                    mock_cl_inst.enabled = False
                    mock_cl.return_value = mock_cl_inst

                    phase = ResponseGuardPhase()
                    ctx = PipelineContext(
                        user_message="РџСЂРёРІРµС‚",
                        context={
                            "response": "РџСЂРёРІРµС‚!",
                            "call_count": 0,
                            "confidence": 0.9,
                        },
                    )
                    result = await phase.execute(ctx)

    assert result.success
    assert result.data["response"] == "С‚С‘РїР»С‹Р№ РѕС‚РІРµС‚"


async def test_response_guard_fallback():
    with patch("core.guard.response_guard.get_response_guard") as mock_g:
        mock_g.side_effect = Exception("guard unavailable")

        phase = ResponseGuardPhase()
        ctx = PipelineContext(
            user_message="С‚РµСЃС‚",
            context={"response": "СЃС‹СЂРѕР№ РѕС‚РІРµС‚"},
        )
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["response"] == "СЃС‹СЂРѕР№ РѕС‚РІРµС‚"
