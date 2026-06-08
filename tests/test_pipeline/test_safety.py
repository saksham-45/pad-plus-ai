import pytest
from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.safety import SafetyPhase


async def test_safety_pass():
    mock_check = MagicMock()
    mock_check.action.value = "pass"
    mock_check.warning_message = None

    with patch("core.safety_layer.get_safety_layer") as mock_get:
        mock_safety = MagicMock()
        mock_safety.check_request.return_value = mock_check
        mock_get.return_value = mock_safety

        phase = SafetyPhase()
        ctx = PipelineContext(user_message="РџСЂРёРІРµС‚")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["blocked"] is False
    assert result.data["safety_passed"] is True


async def test_safety_block():
    mock_check = MagicMock()
    mock_check.action.value = "block"
    mock_check.warning_message = "Р—Р°Р±Р»РѕРєРёСЂРѕРІР°РЅРѕ"

    with patch("core.safety_layer.get_safety_layer") as mock_get:
        mock_safety = MagicMock()
        mock_safety.check_request.return_value = mock_check
        mock_get.return_value = mock_safety

        phase = SafetyPhase()
        ctx = PipelineContext(user_message="РїР»РѕС…РѕР№ Р·Р°РїСЂРѕСЃ")
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["blocked"] is True
    assert result.data["safety_passed"] is False


async def test_safety_degraded():
    with patch("core.safety_layer.get_safety_layer") as mock_get:
        mock_get.side_effect = Exception("safety unavailable")

        phase = SafetyPhase()
        ctx = PipelineContext(user_message="С‚РµСЃС‚")
        result = await phase.execute(ctx)

    assert result.success is False
    assert result.degradation is not None
    assert result.degradation.component == "safety"
