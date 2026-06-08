from unittest.mock import MagicMock, patch

from core.pipeline import PipelineContext
from core.pipeline.phases.health import HealthMonitorPhase


async def test_health_success():
    with patch("core.health_monitor.get_health_monitor") as mock_get:
        mock_health = MagicMock()
        mock_health.assess_health.return_value = {"overall_score": 0.85}
        mock_get.return_value = mock_health

        phase = HealthMonitorPhase()
        ctx = PipelineContext(
            user_message="С‚РµСЃС‚",
            context={
                "pipeline_success": True,
                "rag_used": True,
            },
        )
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["health_score"] == 0.85
    mock_health.record_event.assert_called()


async def test_health_fallback():
    with patch("core.health_monitor.get_health_monitor") as mock_get:
        mock_get.side_effect = Exception("health unavailable")

        phase = HealthMonitorPhase()
        ctx = PipelineContext(user_message="С‚РµСЃС‚", context={})
        result = await phase.execute(ctx)

    assert result.success
    assert result.data["health_score"] == 0.0
