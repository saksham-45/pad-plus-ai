"""
🗄️ Dependency Injection Container для PAD+ AI

Контейнер для управления зависимостями и их жизненным циклом.
Поддерживает singleton и transient зависимости.

Использование:
    from core.dependencies import container, get_fact_memory_chroma

    # В роутах FastAPI
    @router.post("/chat")
    async def chat(
        fact_memory: FactMemoryChroma = Depends(get_fact_memory_chroma)
    ):
        ...
"""

from __future__ import annotations
from typing import TypeVar, Callable, Dict, Any, Optional, Type
from contextlib import contextmanager
import logging

logger = logging.getLogger("padplus.dependencies")

T = TypeVar('T')


class DependencyContainer:
    """
    🗄️ Контейнер зависимостей
    
    Поддерживает:
    - Singleton: один экземпляр на всё приложение
    - Transient: новый экземпляр при каждом запросе
    - Override: переопределение для тестов
    """
    
    def __init__(self):
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._instances: Dict[str, Any] = {}
        self._singletons: Dict[str, bool] = {}
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def register(
        self,
        name: str,
        factory: Callable[[], T],
        singleton: bool = True
    ) -> None:
        """
        Регистрирует зависимость
        
        Args:
            name: Имя зависимости
            factory: Фабрика для создания экземпляра
            singleton: True для singleton, False для transient
        """
        self._factories[name] = factory
        self._singletons[name] = singleton
        
        if singleton:
            self._instances[name] = None
        
        self._logger.debug(f"📦 Registered dependency: {name} (singleton={singleton})")
    
    def get(self, name: str) -> T:
        """
        Получает зависимость
        
        Args:
            name: Имя зависимости
        
        Returns:
            Экземпляр зависимости
        
        Raises:
            KeyError: Если зависимость не зарегистрирована
        """
        if name not in self._factories:
            raise KeyError(f"Dependency '{name}' not registered")
        
        # Для singleton возвращаем кэшированный экземпляр
        if self._singletons.get(name, True):
            if self._instances.get(name) is None:
                self._instances[name] = self._factories[name]()
            return self._instances[name]
        
        # Для transient создаём новый экземпляр
        return self._factories[name]()
    
    def override(self, name: str, instance: T) -> None:
        """
        Переопределяет зависимость (для тестов)
        
        Args:
            name: Имя зависимости
            instance: Экземпляр для переопределения
        """
        self._instances[name] = instance
        self._logger.debug(f"🔄 Overridden dependency: {name}")
    
    def reset(self) -> None:
        """Сбрасывает все singleton зависимости"""
        for name in self._singletons:
            if self._singletons[name]:
                self._instances[name] = None
        self._logger.debug("🔄 Reset all singleton dependencies")
    
    def clear(self) -> None:
        """Полностью очищает контейнер"""
        self._factories.clear()
        self._instances.clear()
        self._singletons.clear()
        self._logger.debug("🗑️ Cleared all dependencies")
    
    def is_registered(self, name: str) -> bool:
        """Проверяет, зарегистрирована ли зависимость"""
        return name in self._factories
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику контейнера"""
        return {
            "total_dependencies": len(self._factories),
            "singleton_count": sum(1 for v in self._singletons.values() if v),
            "transient_count": sum(1 for v in self._singletons.values() if not v),
            "initialized_count": sum(1 for v in self._instances.values() if v is not None)
        }


# Глобальный контейнер
container = DependencyContainer()


def register_dependencies() -> None:
    """Регистрирует все зависимости приложения"""
    from memory.fact_memory_chroma import FactMemoryChroma
    from memory.vector_memory_chroma import VectorMemoryChroma
    from memory.smartcache_chroma import SmartCacheChroma
    from memory.episodic import EpisodicMemory
    from memory.rag import RAGMemory
    from memory.semantic import SemanticMemory
    from memory.persona import PersonaMemory
    from memory.roots import RootsMemory
    from runtime.litellm_service import LiteLLMService
    from core.pipeline import PipelineExecutor
    from core.cache_manager import CacheManager
    from core.safety_layer import SafetyLayer
    from core.intent_router import IntentRouter
    from core.monitoring import MonitoringSystem
    from core.health_monitor import CognitiveHealthMonitor
    from emotion.pad_model import PADModel
    
    # === Hardening компоненты (P0/P1/P2) ===
    from core.db_circuit_breaker import DBCircuitBreaker
    from core.metrics_collector import MetricsCollector
    from core.logging_config import setup_logging
    
    # Настройка логирования
    setup_logging(level="INFO", json_format=False)
    
    # Memory
    container.register("fact_memory_chroma", lambda: FactMemoryChroma(), singleton=True)
    container.register("vector_memory_chroma", lambda: VectorMemoryChroma(), singleton=True)
    container.register("smartcache_chroma", lambda: SmartCacheChroma(), singleton=True)
    container.register("episodic_memory", lambda: EpisodicMemory(), singleton=True)
    container.register("rag_memory", lambda: RAGMemory(), singleton=True)
    container.register("semantic_memory", lambda: SemanticMemory(), singleton=True)
    container.register("persona_memory", lambda: PersonaMemory(), singleton=True)
    container.register("roots_memory", lambda: RootsMemory(), singleton=True)
    
    # Services
    container.register("litellm_service", lambda: LiteLLMService(), singleton=True)
    container.register("pipeline", lambda: PipelineExecutor(), singleton=True)
    container.register("cache_manager", lambda: CacheManager(), singleton=True)
    
    # Core
    container.register("safety_layer", lambda: SafetyLayer(), singleton=True)
    container.register("intent_router", lambda: IntentRouter(), singleton=True)
    container.register("monitoring_system", lambda: MonitoringSystem(), singleton=True)
    container.register("health_monitor", lambda: CognitiveHealthMonitor(), singleton=True)
    container.register("emotion_model", lambda: PADModel(), singleton=True)
    
    # === Hardening компоненты ===
    container.register("db_circuit_breaker", lambda: DBCircuitBreaker(), singleton=True)
    container.register("metrics_collector", lambda: MetricsCollector(), singleton=True)
    # MemoryManager удалён в v3.2
    
    logger.info(f"✅ Registered {container.get_stats()['total_dependencies']} dependencies")


# ============================================================================
# FastAPI Depends функции
# ============================================================================

def get_fact_memory_chroma() -> FactMemoryChroma:
    """Получает FactMemoryChroma"""
    return container.get("fact_memory_chroma")


def get_vector_memory_chroma() -> VectorMemoryChroma:
    """Получает VectorMemoryChroma"""
    return container.get("vector_memory_chroma")


def get_smartcache_chroma() -> SmartCacheChroma:
    """Получает SmartCacheChroma"""
    return container.get("smartcache_chroma")


def get_episodic_memory() -> EpisodicMemory:
    """Получает EpisodicMemory"""
    return container.get("episodic_memory")


def get_rag_memory() -> RAGMemory:
    """Получает RAGMemory"""
    return container.get("rag_memory")


def get_semantic_memory() -> SemanticMemory:
    """Получает SemanticMemory"""
    return container.get("semantic_memory")


def get_persona_memory() -> PersonaMemory:
    """Получает PersonaMemory"""
    return container.get("persona_memory")


def get_roots_memory() -> RootsMemory:
    """Получает RootsMemory"""
    return container.get("roots_memory")


def get_litellm_service() -> LiteLLMService:
    """Получает LiteLLMService"""
    return container.get("litellm_service")


def get_pipeline() -> PipelineExecutor:
    """Получает PipelineExecutor"""
    return container.get("pipeline")


def get_cache_manager() -> CacheManager:
    """Получает CacheManager"""
    return container.get("cache_manager")


def get_safety_layer() -> SafetyLayer:
    """Получает SafetyLayer"""
    return container.get("safety_layer")


def get_intent_router() -> IntentRouter:
    """Получает IntentRouter"""
    return container.get("intent_router")


def get_monitoring_system() -> MonitoringSystem:
    """Получает MonitoringSystem"""
    return container.get("monitoring_system")


def get_health_monitor() -> CognitiveHealthMonitor:
    """Получает CognitiveHealthMonitor"""
    return container.get("health_monitor")


def get_emotion_model() -> PADModel:
    """Получает PADModel"""
    return container.get("emotion_model")
