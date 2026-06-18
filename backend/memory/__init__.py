"""
📦 Memory Package — Единый интерфейс для всех систем памяти

- RAG (векторный поиск контекста)
- Episodic Memory (эпизодическая память)
- Semantic Memory (семантическая/процедурная память)
- Persona (личность)
- User Persona (персонализированная личность)
- Roots Memory (фундаментальные принципы)
"""

# Базовый интерфейс
from .base import MemoryInterface, MemoryRecord

# Условный импорт RAG в зависимости от конфигурации
try:
    from core.config_manager import get_database_url
    db_url = get_database_url()
    if db_url and db_url.startswith('postgresql'):
        from .rag_postgres import RAGMemory, get_rag
    else:
        from .rag import RAGMemory, get_rag
except ImportError:
    from .rag import RAGMemory, get_rag

# Условный импорт EpisodicMemory в зависимости от конфигурации
try:
    from core.config_manager import get_database_url
    db_url = get_database_url()
    if db_url and db_url.startswith('postgresql'):
        from .episodic_postgres import EpisodicMemory, get_episodic_memory
    else:
        from .episodic import EpisodicMemory, get_episodic_memory
except ImportError:
    from .episodic import EpisodicMemory, get_episodic_memory

# Условный импорт SemanticMemory в зависимости от конфигурации
try:
    from core.config_manager import get_database_url
    db_url = get_database_url()
    if db_url and db_url.startswith('postgresql'):
        from .semantic_postgres import SemanticMemory, get_semantic_memory
    else:
        from .semantic import SemanticMemory, get_semantic_memory
except ImportError:
    from .semantic import SemanticMemory, get_semantic_memory

from .persona import PersonaMemory, get_persona

# Алиас для совместимости
Persona = PersonaMemory
from .user_persona import UserPersona, get_user_persona_manager
from .roots import RootsMemory, get_roots_memory

# === Утилиты ===
from .hygiene import MemoryHygiene, get_hygiene

# Алиас для совместимости
get_memory_hygiene = get_hygiene
from .consolidation import MemoryConsolidator, get_consolidator

__all__ = [
    # Базовый интерфейс
    "MemoryInterface",
    "MemoryRecord",
    
    # Другие компоненты
    "RAGMemory",
    "get_rag",
    "EpisodicMemory",
    "get_episodic_memory",
    "SemanticMemory",
    "get_semantic_memory",
    "Persona",
    "get_persona",
    "UserPersona",
    "get_user_persona_manager",
    "RootsMemory",
    "get_roots_memory",
    
    # Утилиты
    "MemoryHygiene",
    "get_memory_hygiene",
    "MemoryConsolidator",
    "get_consolidator",
]