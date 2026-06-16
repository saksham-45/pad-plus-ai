"""
📦 Memory Package — Единый интерфейс для всех систем памяти

Этот модуль предоставляет единый доступ ко всем компонентам памяти:
- RAG (векторный поиск контекста)
- Fact Memory (факты через ChromaDB)
- Vector Memory (долговременная память через ChromaDB)
- SmartCache (кратковременный кэш через ChromaDB)
- Episodic Memory (эпизодическая память)
- Semantic Memory (семантическая/процедурная память)
- Persona (личность)
- User Persona (персонализированная личность)
- Roots Memory (фундаментальные принципы)

Все компоненты используют ChromaDB для векторного поиска.
"""

# Базовый интерфейс
from .base import MemoryInterface, MemoryRecord

# === Новые версии (ChromaDB) — основные ===
# Fact Memory (векторный поиск фактов)
from .fact_memory_chroma import FactMemoryChroma, get_fact_memory_chroma

# Vector Memory (долговременная память)
from .vector_memory_chroma import VectorMemoryChroma, get_vector_memory_chroma

# SmartCache (кратковременный кэш)
from .smartcache_chroma import SmartCacheChroma, get_smartcache_chroma

# === Другие компоненты памяти ===
from .rag import RAGMemory, get_rag
from .episodic import EpisodicMemory, get_episodic_memory
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
    
    # Новые версии (ChromaDB)
    "FactMemoryChroma",
    "get_fact_memory_chroma",
    "VectorMemoryChroma", 
    "get_vector_memory_chroma",
    "SmartCacheChroma",
    "get_smartcache_chroma",
    
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