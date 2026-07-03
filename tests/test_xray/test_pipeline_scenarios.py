"""
X-Ray тесты: сценарии pipeline — error path + strategy selection.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture(autouse=True)
def reset_trace_collector():
    from core.xray.trace_collector import get_trace_collector
    tc = get_trace_collector()
    tc._sessions.clear()
    tc._active_sessions.clear()
    tc._event_subscribers.clear()
    yield


@pytest.fixture
def base_mocks():
    """Базовые моки для pipeline"""
    actions = []

    mock_action = MagicMock()
    mock_action.value = "allow"
    mock_check = MagicMock()
    mock_check.action = mock_action
    mock_check.warning_message = None
    mock_safety = MagicMock()
    mock_safety.check_request.return_value = mock_check
    mock_safety.sanitize_input.return_value = ""
    actions.append(patch("core.safety_layer.get_safety_layer", return_value=mock_safety))

    mock_state = MagicMock()
    mock_state.to_dict.return_value = {"pleasure": 0.7, "arousal": 0.5, "dominance": 0.6}
    mock_state.get_style.return_value = {"tone": "neutral", "уверенность": 0.8}
    mock_pad = MagicMock()
    mock_pad.get_state.return_value = mock_state
    actions.append(patch("emotion.pad_model.get_pad_model", return_value=mock_pad))

    mock_result = MagicMock()
    mock_result.text = "Тестовый ответ"
    mock_result.provider = "test"
    mock_result.confidence = 0.85
    mock_result.model = "test-model"
    mock_result.metadata = {}
    mock_gen = AsyncMock(return_value=mock_result)
    actions.append(patch("runtime.llm_service.LLMService.generate", mock_gen))

    mock_kg = MagicMock()
    mock_kg.get_stats.return_value = {"nodes": 0, "edges": 0, "concepts": []}
    actions.append(patch("knowledge.graph.get_knowledge_graph", return_value=mock_kg))

    for p in actions:
        p.start()
    yield
    for p in actions:
        p.stop()


@pytest.fixture
def trace_events():
    """Подписка на TraceCollector + автоматический сбор событий"""
    from core.xray.trace_collector import get_trace_collector
    collector = get_trace_collector()
    events = []

    def on_event(event_type, data):
        entry = {"type": event_type}
        if isinstance(data, dict):
            entry.update(data)
        else:
            entry["data"] = data
        events.append(entry)

    collector.subscribe(on_event)
    yield events
    collector.unsubscribe(on_event)


@pytest.mark.asyncio
async def test_anti_loop_block_trace(base_mocks, trace_events):
    """
    X-Ray тест: anti-loop блокировка.
    Pipeline должен зафиксировать блокировку в trace.
    """
    from core.pipeline.executor import PipelineExecutor

    executor = PipelineExecutor()

    # Три повторных запроса для триггера anti-loop
    msg = "повтори это сообщение три раза"
    for _ in range(3):
        executor._check_anti_loop(msg)

    result = await executor.execute(user_message=msg)

    assert result.success
    assert "обнаружен цикл" in result.response.lower()

    stages = [e.get("stage") for e in trace_events
              if e["type"] == "event_recorded" and e.get("stage")]

    assert "safety" not in stages, "Anti-loop блокировка: pipeline не должен идти дальше anti-loop"
    assert len(stages) == 0, f"Anti-loop блокировка: не должно быть стадий, получено: {stages}"

    types = [e["type"] for e in trace_events]
    assert "session_started" in types
    assert "session_completed" in types


@pytest.mark.asyncio
async def test_safety_block_trace(base_mocks, trace_events):
    """
    X-Ray тест: safety блокировка.
    Pipeline должен записать safety как blocked и stop.
    """
    from core.pipeline.executor import PipelineExecutor
    from core.xray.trace_collector import get_trace_collector

    collector = get_trace_collector()

    executor = PipelineExecutor()

    # Мокаем safety на блокировку
    mock_action = MagicMock()
    mock_action.value = "block"
    mock_check = MagicMock()
    mock_check.action = mock_action
    mock_check.warning_message = "Запрос заблокирован"

    with patch("core.safety_layer.get_safety_layer") as mock_get:
        mock_safety = MagicMock()
        mock_safety.check_request.return_value = mock_check
        mock_get.return_value = mock_safety

        result = await executor.execute(user_message="вредоносный запрос")

    assert result.success
    assert result.safety_passed is False
    assert "заблокирован" in result.response.lower()

    stages = [e.get("stage") for e in trace_events
              if e["type"] == "event_recorded" and e.get("stage")]

    assert "safety" in stages
    if len(stages) > 1:
        assert stages[0] == "safety", "Safety должна быть первой стадией"

    safety_events = [e for e in trace_events
                     if e.get("data", {}).get("phase") == "safety"]
    assert len(safety_events) > 0
    assert safety_events[0].get("data", {}).get("blocked") is True


@pytest.mark.asyncio
async def test_strategy_selection_trace(base_mocks, trace_events):
    """
    X-Ray тест: стратегия зависит от запроса.
    Trace должен показывать выбранную стратегию.
    """
    from core.pipeline.executor import PipelineExecutor

    executor = PipelineExecutor()

    results = []
    for msg in ["привет", "почему небо голубое? объясни подробно", "придумай креативную идею"]:
        result = await executor.execute(user_message=msg)
        results.append((msg, result))

    # simple
    assert results[0][1].strategy == "simple", f"Ожидал simple, получил {results[0][1].strategy}"
    # reasoning
    assert results[1][1].strategy in ("reasoning", "retrieval"), f"Ожидал reasoning/retrieval, получил {results[1][1].strategy}"
    # creative
    assert results[2][1].strategy == "creative", f"Ожидал creative, получил {results[2][1].strategy}"


@pytest.mark.asyncio
async def test_pipeline_degradation_continues(base_mocks, trace_events):
    """
    X-Ray тест: деградация не-критичного компонента.
    Pipeline продолжает выполнение, X-Ray записывает degraded status.
    """
    from core.pipeline.executor import PipelineExecutor

    executor = PipelineExecutor()

    # Ломаем knowledge_graph (не критичный)
    # Используем сообщение, которое триггерит reasoning стратегию (все фазы)
    with patch("knowledge.graph.get_knowledge_graph", side_effect=Exception("KG недоступен")):
        result = await executor.execute(user_message="Почему система падает при деградации? Объясни подробно.")

    assert result.success
    assert result.execution_time_ms > 0

    phases = [e.get("data", {}).get("phase") for e in trace_events
              if e["type"] == "event_recorded" and e.get("data", {}).get("phase")]

    assert "knowledge_graph" in phases, "KnowledgeGraph должен быть в trace даже при ошибке"
    assert "generate" in phases, "Pipeline должен дойти до generate"
    assert "response_guard" in phases, "Pipeline должен дойти до response_guard"


@pytest.mark.asyncio
async def test_pipeline_thought_stream(base_mocks, trace_events):
    """
    X-Ray тест: проверка что ThoughtVisualizer генерирует мысли
    для ключевых фаз.
    """
    from core.pipeline.executor import PipelineExecutor

    executor = PipelineExecutor()

    result = await executor.execute(user_message="почему трава зеленая?")

    assert result.success
    assert result.strategy in ("reasoning", "retrieval")

    phases = [e.get("data", {}).get("phase") for e in trace_events
              if e["type"] == "event_recorded" and e.get("data", {}).get("phase")]

    for expected in ["safety", "intent", "emotion", "persona", "generate", "truth_loop"]:
        assert expected in phases, f"Нет фазы {expected} в trace"
