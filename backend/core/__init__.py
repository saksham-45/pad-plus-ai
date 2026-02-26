"""Core module — ядро системы"""
from .anti_directive import ANTI_DIRECTIVE, check_integrity
from .health_monitor import CognitiveHealthMonitor, get_health_monitor
from .meta_controller import (
    MetaCognitiveController, get_meta_controller,
    ProcessingStrategy, CognitiveState
)
