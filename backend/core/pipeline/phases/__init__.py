"""
Pipeline phases registry.
"""

from .anti_loop import AntiLoopPhase
from .safety import SafetyPhase
from .intent import IntentPhase
from .rag import RagPhase
from .knowledge_graph import KnowledgeGraphPhase
from .episodic import EpisodicPhase
from .semantic import SemanticPhase
from .emotion import EmotionPhase
from .persona import PersonaPhase
from .roots import RootsPhase
from .identity import IdentityPhase
from .generate import GeneratePhase
from .truth_loop import TruthLoopPhase
from .save_episode import SaveEpisodePhase
from .emotion_update import EmotionUpdatePhase
from .persona_evolution import PersonaEvolutionPhase
from .events import EventsBroadcastPhase
from .health import HealthMonitorPhase
from .reflection import ReflectionPhase
from .dreams import DreamsPhase
from .metrics import MetricsPhase
from .response_guard import ResponseGuardPhase

__all__ = [
    "AntiLoopPhase",
    "SafetyPhase",
    "IntentPhase",
    "RagPhase",
    "KnowledgeGraphPhase",
    "EpisodicPhase",
    "SemanticPhase",
    "EmotionPhase",
    "PersonaPhase",
    "RootsPhase",
    "IdentityPhase",
    "GeneratePhase",
    "TruthLoopPhase",
    "SaveEpisodePhase",
    "EmotionUpdatePhase",
    "PersonaEvolutionPhase",
    "EventsBroadcastPhase",
    "HealthMonitorPhase",
    "ReflectionPhase",
    "DreamsPhase",
    "MetricsPhase",
    "ResponseGuardPhase",
]
