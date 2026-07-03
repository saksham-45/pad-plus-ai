"""
Первый X-Ray монолит тест — полный прогон pipeline с захватом TraceCollector.

Проверяет: pipeline выполняется целиком, TraceCollector записывает все стадии,
стадии идут в правильном порядке, длительности разумные.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture(autouse=True)
def reset_trace_collector():
    """Сбрасывает TraceCollector перед каждым тестом"""
    from core.xray.trace_collector import get_trace_collector
    tc = get_trace_collector()
    tc._sessions.clear()
    tc._active_sessions.clear()
    tc._event_subscribers.clear()
    yield


@pytest.fixture
def mock_ext_deps():
    """Мокает внешние зависимости для чистого прогона pipeline"""
    actions = []

    # Safety
    mock_action = MagicMock()
    mock_action.value = "allow"

    mock_check = MagicMock()
    mock_check.action = mock_action
    mock_check.warning_message = None

    mock_safety = MagicMock()
    mock_safety.check_request.return_value = mock_check
    mock_safety.sanitize_input.return_value = ""
    p1 = patch("core.safety_layer.get_safety_layer", return_value=mock_safety)
    actions.append(p1)

    # Emotion PAD
    mock_state = MagicMock()
    mock_state.to_dict.return_value = {
        "pleasure": 0.7, "arousal": 0.5, "dominance": 0.6
    }
    mock_state.get_style.return_value = {
        "tone": "neutral", "уверенность": 0.8
    }
    mock_pad = MagicMock()
    mock_pad.get_state.return_value = mock_state
    p2 = patch("emotion.pad_model.get_pad_model", return_value=mock_pad)
    actions.append(p2)

    # LLM service
    mock_result = MagicMock()
    mock_result.text = "Тестовый ответ от AI"
    mock_result.provider = "test"
    mock_result.confidence = 0.85
    mock_result.model = "test-model"
    mock_result.metadata = {}

    mock_gen = AsyncMock(return_value=mock_result)
    p3 = patch("runtime.llm_service.LLMService.generate", mock_gen)
    actions.append(p3)

    # Knowledge graph
    mock_kg = MagicMock()
    mock_kg.get_stats.return_value = {
        "nodes": 0, "edges": 0, "concepts": []
    }
    p4 = patch("knowledge.graph.get_knowledge_graph", return_value=mock_kg)
    actions.append(p4)

    for p in actions:
        p.start()
    yield
    for p in actions:
        p.stop()


@pytest.mark.asyncio
async def test_pipeline_full_trace(mock_ext_deps):
    """
    X-Ray тест: полный цикл pipeline.
    Проверяет что TraceCollector записывает ВСЕ стадии.
    """
    from core.xray.trace_collector import get_trace_collector
    from core.pipeline.executor import PipelineExecutor

    collector = get_trace_collector()

    # Подписываемся на TraceCollector
    events = []

    def on_xray_event(event_type, data):
        entry = {"type": event_type}
        if isinstance(data, dict):
            entry.update(data)
        else:
            entry["data"] = data
        events.append(entry)

    collector.subscribe(on_xray_event)

    # Создаём executor
    executor = PipelineExecutor()

    # Выполняем pipeline
    result = await executor.execute(
        user_message="Почему PAD+ использует когнитивную архитектуру? Объясни подробно и проанализируй все компоненты.",
        api_key="test-key",
        provider="test",
    )

    # Отписываемся
    collector.unsubscribe(on_xray_event)

    # === АССЕРТЫ ===

    # 1. Pipeline успешно завершился
    assert result.success, (
        f"Pipeline не завершился успешно\n"
        f"  response: {result.response[:200]}\n"
        f"  errors: {result.errors}"
    )

    # 2. TraceCollector получил события
    assert len(events) > 0, "TraceCollector не получил ни одного события"

    # 3. Типы событий
    event_types = [e["type"] for e in events]
    assert "session_started" in event_types, "Нет session_started"
    assert "session_completed" in event_types, "Нет session_completed"

    # 4. Абстрактные стадии (TraceStage) записаны
    stages = [
        e.get("stage")
        for e in events
        if e["type"] == "event_recorded" and e.get("stage")
    ]

    assert "safety" in stages, "Нет TraceStage safety"
    assert "intent" in stages, "Нет TraceStage intent"
    assert "retrieve" in stages, "Нет TraceStage retrieve"
    assert "persona" in stages, "Нет TraceStage persona"
    assert "generate" in stages, "Нет TraceStage generate"
    assert "verify" in stages, "Нет TraceStage verify"
    assert "remember" in stages, "Нет TraceStage remember"
    assert "emit" in stages, "Нет TraceStage emit"

    # 5. Конкретные фазы pipeline записаны (по именам)
    phases = [
        e.get("data", {}).get("phase")
        for e in events
        if e["type"] == "event_recorded" and e.get("data", {}).get("phase")
    ]

    expected_phases = [
        "safety", "intent", "rag", "knowledge_graph",
        "episodic", "semantic", "emotion", "persona", "roots",
        "identity", "generate", "truth_loop", "save_episode",
        "emotion_update", "persona_evolution", "events_broadcast",
        "health", "reflection", "dreams", "metrics", "response_guard",
    ]

    for phase in expected_phases:
        assert phase in phases, f"Нет фазы pipeline: {phase}"

    # 6. Порядок фаз совпадает с ожидаемым
    for i, phase in enumerate(phases):
        if i < len(expected_phases):
            assert phase == expected_phases[i], (
                f"Неправильный порядок на позиции {i}: "
                f"ожидался {expected_phases[i]}, получен {phase}"
            )

    # 7. Все длительности неотрицательные
    for e in events:
        if e["type"] == "event_recorded":
            dur = e.get("duration_ms", 0)
            assert dur >= 0, f"Отрицательная длительность {dur}ms в {e.get('stage')}"

    # 8. Pipeline result filled
    assert result.intent != "", "intent не заполнен"
    assert result.strategy != "", "strategy не заполнен"
    assert result.execution_time_ms > 0, "execution_time_ms не заполнен"

    # 9. Дамп trace — чтобы видеть всю картину
    print(f"\n=== X-RAY TRACE: {len(phases)} phases ===")
    for e in events:
        if e["type"] == "event_recorded":
            stage = e.get("stage", "?")
            phase = e.get("data", {}).get("phase", "?")
            dur = e.get("duration_ms", 0)
            status = e.get("status", "?")
            print(f"  {stage:12s} | {phase:20s} | {dur:8.1f}ms | {status}")
    print(f"  Strategy: {result.strategy} | Intent: {result.intent} | "
          f"Total: {result.execution_time_ms:.0f}ms")
