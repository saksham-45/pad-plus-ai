from unittest.mock import MagicMock

from core.pipeline import PipelineContext, PipelineResult
from core.pipeline.phases.metrics import MetricsPhase


async def test_metrics_success():
    executor = MagicMock()
    result_obj = PipelineResult(success=True)

    phase = MetricsPhase(executor)
    ctx = PipelineContext(
        user_message="С‚РµСЃС‚",
        context={
            "start_time": 0,
            "pipeline_result": result_obj,
        },
    )
    phase_result = await phase.execute(ctx)

    assert phase_result.success
    executor._record_metrics.assert_called_once_with(0, result_obj)


async def test_metrics_no_result():
    executor = MagicMock()
    phase = MetricsPhase(executor)
    ctx = PipelineContext(
        user_message="С‚РµСЃС‚",
        context={},
    )
    phase_result = await phase.execute(ctx)

    assert phase_result.success
