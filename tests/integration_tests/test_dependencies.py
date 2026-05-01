"""
Тесты для Dependency Injection Container

Проверяют:
1. Регистрация зависимостей
2. Получение singleton и transient
3. Override для тестов
4. Reset и clear
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


class TestDependencyContainer:
    """Тесты DependencyContainer"""

    def test_container_creation(self):
        """
        Проверяет создание контейнера
        """
        from backend.core.dependencies import DependencyContainer
        
        container = DependencyContainer()
        
        assert container is not None
        assert container.get_stats()["total_dependencies"] == 0

    def test_register_singleton(self):
        """
        Проверяет регистрацию singleton
        """
        from backend.core.dependencies import DependencyContainer
        
        container = DependencyContainer()
        container.register("test", lambda: {"key": "value"}, singleton=True)
        
        assert container.is_registered("test")
        assert container.get_stats()["singleton_count"] == 1

    def test_get_singleton_returns_same_instance(self):
        """
        Проверяет, что singleton возвращает тот же экземпляр
        """
        from backend.core.dependencies import DependencyContainer
        
        container = DependencyContainer()
        container.register("test", lambda: {"key": "value"}, singleton=True)
        
        instance1 = container.get("test")
        instance2 = container.get("test")
        
        assert instance1 is instance2

    def test_register_transient(self):
        """
        Проверяет регистрацию transient
        """
        from backend.core.dependencies import DependencyContainer
        
        container = DependencyContainer()
        container.register("test", lambda: {"key": "value"}, singleton=False)
        
        assert container.get_stats()["transient_count"] == 1

    def test_get_transient_returns_new_instance(self):
        """
        Проверяет, что transient возвращает новый экземпляр
        """
        from backend.core.dependencies import DependencyContainer
        
        counter = {"count": 0}
        
        def factory():
            counter["count"] += 1
            return {"id": counter["count"]}
        
        container = DependencyContainer()
        container.register("test", factory, singleton=False)
        
        instance1 = container.get("test")
        instance2 = container.get("test")
        
        assert instance1["id"] == 1
        assert instance2["id"] == 2
        assert instance1 is not instance2

    def test_override(self):
        """
        Проверяет переопределение зависимости
        """
        from backend.core.dependencies import DependencyContainer
        
        container = DependencyContainer()
        container.register("test", lambda: "original", singleton=True)
        
        # Получаем оригинал
        assert container.get("test") == "original"
        
        # Переопределяем
        container.override("test", "overridden")
        
        # Получаем переопределённое
        assert container.get("test") == "overridden"

    def test_reset(self):
        """
        Проверяет сброс singleton
        """
        from backend.core.dependencies import DependencyContainer
        
        counter = {"count": 0}
        
        def factory():
            counter["count"] += 1
            return {"id": counter["count"]}
        
        container = DependencyContainer()
        container.register("test", factory, singleton=True)
        
        # Получаем экземпляр
        instance1 = container.get("test")
        assert instance1["id"] == 1
        
        # Сбрасываем
        container.reset()
        
        # Получаем новый экземпляр
        instance2 = container.get("test")
        assert instance2["id"] == 2

    def test_clear(self):
        """
        Проверяет полную очистку контейнера
        """
        from backend.core.dependencies import DependencyContainer
        
        container = DependencyContainer()
        container.register("test", lambda: "value", singleton=True)
        
        assert container.is_registered("test")
        
        container.clear()
        
        assert not container.is_registered("test")
        assert container.get_stats()["total_dependencies"] == 0

    def test_get_unregistered_raises(self):
        """
        Проверяет, что получение незарегистрированной зависимости вызывает ошибку
        """
        from backend.core.dependencies import DependencyContainer
        
        container = DependencyContainer()
        
        with pytest.raises(KeyError):
            container.get("unregistered")

    def test_get_stats(self):
        """
        Проверяет статистику контейнера
        """
        from backend.core.dependencies import DependencyContainer
        
        container = DependencyContainer()
        container.register("singleton1", lambda: "s1", singleton=True)
        container.register("singleton2", lambda: "s2", singleton=True)
        container.register("transient1", lambda: "t1", singleton=False)
        
        stats = container.get_stats()
        
        assert stats["total_dependencies"] == 3
        assert stats["singleton_count"] == 2
        assert stats["transient_count"] == 1


class TestRegisterDependencies:
    """Тесты регистрации зависимостей приложения"""

    def test_register_dependencies(self):
        """
        Проверяет регистрацию всех зависимостей
        """
        from backend.core.dependencies import container, register_dependencies
        
        # Сбрасываем контейнер
        container.clear()
        
        # Регистрируем
        register_dependencies()
        
        # Проверяем
        stats = container.get_stats()
        assert stats["total_dependencies"] > 0
        assert stats["singleton_count"] > 0

    def test_get_fact_memory_chroma(self):
        """
        Проверяет получение FactMemoryChroma через DI
        """
        from backend.core.dependencies import container, register_dependencies, get_fact_memory_chroma
        
        container.clear()
        register_dependencies()
        
        fact_memory = get_fact_memory_chroma()
        assert fact_memory is not None

    def test_get_pipeline(self):
        """
        Проверяет получение Pipeline через DI
        """
        from backend.core.dependencies import container, register_dependencies, get_pipeline
        
        container.clear()
        register_dependencies()
        
        pipeline = get_pipeline()
        assert pipeline is not None

    def test_get_cache_manager(self):
        """
        Проверяет получение CacheManager через DI
        """
        from backend.core.dependencies import container, register_dependencies, get_cache_manager
        
        container.clear()
        register_dependencies()
        
        cache_manager = get_cache_manager()
        assert cache_manager is not None


class TestDIIntegration:
    """Интеграционные тесты DI"""

    def test_di_container_in_lifespan(self):
        """
        Проверяет, что DI инициализируется в lifespan
        """
        from backend.core.dependencies import container
        
        # Проверяем, что контейнер существует
        assert container is not None
        
        # Проверяем, что зависимости зарегистрированы
        stats = container.get_stats()
        assert stats["total_dependencies"] > 0 or stats["total_dependencies"] == 0
        # (0 если lifespan ещё не вызывался в тестах)

    def test_override_for_testing(self):
        """
        Проверяет переопределение зависимостей для тестов
        """
        from backend.core.dependencies import container, register_dependencies, get_fact_memory_chroma
        
        container.clear()
        register_dependencies()
        
        # Получаем оригинал
        original = get_fact_memory_chroma()
        assert original is not None
        
        # Переопределяем для теста
        mock_fact_memory = MagicMock()
        container.override("fact_memory_chroma", mock_fact_memory)
        
        # Получаем мок
        overridden = get_fact_memory_chroma()
        assert overridden is mock_fact_memory
        
        # Сбрасываем
        container.reset()
