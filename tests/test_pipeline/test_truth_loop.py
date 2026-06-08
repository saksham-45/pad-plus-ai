from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.truth_loop import TruthLoopPhase


async def test_truth_loop_with_claims():
    with patch("core.truth_loop.get_truth_loop") as mock_get:
        mock_truth = MagicMock()
        mock_truth.extract_claims.return_value = ["СѓС‚РІРµСЂР¶РґРµРЅРёРµ1"]
        mock_truth.verify_claims.return_value = {
            "overall_confidence": 0.85,
            "verified_claims": [{"claim": "СѓС‚РІРµСЂР¶РґРµРЅРёРµ1", "confidence": 0.9}],
        }
        mock_get.return_value = mock_truth

        phase = TruthLoopPhase()
        ctx = PipelineContext(
            user_message="С‚РµСЃС‚",
            context={
                "response": "Р—РµРјР»СЏ РєСЂСѓРіР»Р°СЏ",
                "sources": {
                    "rag": {"count": 2, "confidence": 0.8},
                    "facts": {"count": 0},
                    "episodic": {"count": 0},
                    "llm": {"model": "gpt-4", "provider": "openai"},
                },
            },
        )
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["truth_confidence"] == 0.85
    assert result.data["claims_verified"] == 1


async def test_truth_loop_no_response():
    phase = TruthLoopPhase()
    ctx = PipelineContext(user_message="С‚РµСЃС‚", context={"sources": {}})
    result = await phase.execute(ctx)

    assert result.success
    assert result.data["truth_confidence"] == 0.5
    assert result.data["claims_verified"] == 0
