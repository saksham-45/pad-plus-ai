"""
🧠 X-Ray — система наблюдения и анализа AI

Компоненты:
- SystemState: состояние системы (load, confidence, errors)
- MetaLearner: мета-обучение (статистика стратегий)
- ReflectionLoop: рефлексия (анализ результатов)
- CognitiveState: когнитивные метрики
- TraceContext: трассировка выполнения
- EventBuffer: буфер событий
- Insights: аналитика и аномалии
- Broadcaster: WebSocket рассылка
- HistoryRecorder: запись сессий
- ThoughtVisualizer: визуализация мыслей
- TraceCollector: сбор трасс
- Tracer: трассировка

Примечание: XRayBrain был удалён.
"""

# === НОВЫЕ КОМПОНЕНТЫ BRAIN ===
from .system_state import SystemState, SystemStateManager, get_system_state_manager, reset_system_state
from .meta_learner import MetaLearner, StrategyStats, get_meta_learner, reset_meta_learner
from .reflection import ReflectionLoop, ReflectionResult, get_reflection_loop, reset_reflection_loop

# === СУЩЕСТВУЮЩИЕ КОМПОНЕНТЫ ===
from .tracer import XRayTracer, get_xray_tracer
from .history_recorder import XRayHistory, get_xray_history
from .cognitive_state import CognitiveState, CognitiveStateManager, get_cognitive_state_manager
from .event_buffer import EventBuffer, get_event_buffer
from .insights import InsightsEngine, get_insights_engine
from .broadcaster import XRayBroadcaster, get_xray_broadcaster
from .thought_visualizer import ThoughtVisualizer, get_thought_visualizer
from .trace_collector import XRayTraceCollector, get_trace_collector

__all__ = [
    # Brain components (НОВЫЕ)
    'SystemState', 'SystemStateManager', 'get_system_state_manager', 'reset_system_state',
    'MetaLearner', 'StrategyStats', 'get_meta_learner', 'reset_meta_learner',
    'ReflectionLoop', 'ReflectionResult', 'get_reflection_loop', 'reset_reflection_loop',
    # Existing components
    'XRayTracer', 'get_xray_tracer',
    'XRayHistory', 'get_xray_history',
    'CognitiveState', 'CognitiveStateManager', 'get_cognitive_state_manager',
    'EventBuffer', 'get_event_buffer',
    'InsightsEngine', 'get_insights_engine',
    'XRayBroadcaster', 'get_xray_broadcaster',
    'ThoughtVisualizer', 'get_thought_visualizer',
    'XRayTraceCollector', 'get_trace_collector',
]
