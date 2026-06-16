"""
🛡️ Guard — контроль идентичности и качества ответов (v2.0)

Многоступенчатая система обработки ответов:
1. ResponseGuard — базовая очистка и контроль идентичности
2. Self-Healing Guard — самообучающийся контроль ошибок
3. Tone Engine — адаптивный эмоциональный тон
4. Cognitive Layer — объяснение процесса мышления
5. SecurityPatterns — расширенные паттерны безопасности
"""

from .response_guard import ResponseGuard, get_response_guard, reset_response_guard
from .self_healing import (
    SelfHealingGuard, 
    get_self_healing_guard, 
    reset_self_healing_guard,
    GuardErrorDetector,
    GuardMemory,
    ErrorType,
    adapt_guard
)
from .tone_engine import (
    ToneEngine, 
    get_tone_engine, 
    reset_tone_engine,
    apply_emotional_tone,
    TONE_MAP
)
from .cognitive_layer import (
    CognitiveLayer, 
    get_cognitive_layer, 
    reset_cognitive_layer,
    build_cognition,
    explain_thinking,
    CognitionData,
    SourceInfo,
    StrategyType,
    STRATEGY_DESCRIPTIONS
)
from .security_patterns import (
    SecurityPatterns,
    SecurityThreat,
    get_security_patterns,
    reset_security_patterns
)

__all__ = [
    # ResponseGuard
    "ResponseGuard",
    "get_response_guard",
    "reset_response_guard",
    
    # Self-Healing
    "SelfHealingGuard",
    "get_self_healing_guard",
    "reset_self_healing_guard",
    "GuardErrorDetector",
    "GuardMemory",
    "ErrorType",
    "adapt_guard",
    
    # Tone Engine
    "ToneEngine",
    "get_tone_engine",
    "reset_tone_engine",
    "apply_emotional_tone",
    "TONE_MAP",
    
    # Cognitive Layer
    "CognitiveLayer",
    "get_cognitive_layer",
    "reset_cognitive_layer",
    "build_cognition",
    "explain_thinking",
    "CognitionData",
    "SourceInfo",
    "StrategyType",
    "STRATEGY_DESCRIPTIONS",
    
    # Security Patterns
    "SecurityPatterns",
    "SecurityThreat",
    "get_security_patterns",
    "reset_security_patterns",
]
