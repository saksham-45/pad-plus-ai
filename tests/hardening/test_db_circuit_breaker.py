"""
🧪 Тесты для DB Circuit Breaker

Проверяет:
- Состояния Circuit Breaker (closed/open/half_open)
- Fallback механизм
- Восстановление после ошибок
- Статистика
"""

import pytest
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Добавляем backend в path для импортов
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from core.db_circuit_breaker import (
    DBCircuitBreaker,
    CircuitState,
    get_db_circuit_breaker,
    reset_db_circuit_breaker,
)


@pytest.fixture
def circuit_breaker():
    """Создает новый Circuit Breaker для каждого теста"""
    return DBCircuitBreaker(
        failure_threshold=3,
        recovery_timeout=1,  # 1 секунда для быстрых тестов
        fallback_enabled=True,
    )


@pytest.fixture
def global_circuit_breaker():
    """Сбрасывает глобальный Circuit Breaker"""
    reset_db_circuit_breaker()
    yield get_db_circuit_breaker()
    reset_db_circuit_breaker()


class TestCircuitBreakerStates:
    """Тесты состояний Circuit Breaker"""
    
    def test_initial_state_is_closed(self, circuit_breaker):
        """Начальное состояние — closed"""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.is_closed
        assert not circuit_breaker.is_open
    
    def test_opens_after_threshold_failures(self, circuit_breaker):
        """Открывается после достижения порога ошибок"""
        async def failing_operation(**kwargs):
            raise Exception("DB error")
        
        async def fallback(**kwargs):
            return "fallback_value"
        
        # Выполняем операцию с ошибками
        async def run_test():
            for i in range(3):
                try:
                    await circuit_breaker.execute(
                        operation="test_op",
                        func=failing_operation,
                        fallback=fallback,
                    )
                except Exception:
                    pass
            
            # После 3 ошибок circuit должен открыться
            assert circuit_breaker.state == CircuitState.OPEN
            assert circuit_breaker.is_open
        
        asyncio.run(run_test())
    
    def test_transitions_to_half_open_after_timeout(self, circuit_breaker):
        """Переходит в half_open после таймаута восстановления"""
        circuit_breaker._state = CircuitState.OPEN
        circuit_breaker._opened_at = datetime.now() - timedelta(seconds=2)
        
        # Проверяем состояние — должно перейти in half_open
        assert circuit_breaker.state == CircuitState.HALF_OPEN


class TestCircuitBreakerExecution:
    """Тесты выполнения операций"""
    
    def test_successful_execution(self, circuit_breaker):
        """Успешное выполнение операции"""
        async def successful_operation(**kwargs):
            return "success"
        
        async def run_test():
            result = await circuit_breaker.execute(
                operation="test_op",
                func=successful_operation,
            )
            assert result == "success"
            assert circuit_breaker.is_closed
        
        asyncio.run(run_test())
    
    def test_fallback_on_open_circuit(self, circuit_breaker):
        """Использует fallback когда circuit открыт"""
        circuit_breaker._state = CircuitState.OPEN
        
        async def any_operation(**kwargs):
            raise Exception("Should not be called")
        
        async def fallback(**kwargs):
            return "fallback_value"
        
        async def run_test():
            result = await circuit_breaker.execute(
                operation="test_op",
                func=any_operation,
                fallback=fallback,
            )
            assert result == "fallback_value"
        
        asyncio.run(run_test())
    
    def test_raises_when_no_fallback_and_open(self, circuit_breaker):
        """Бросает исключение когда нет fallback и circuit открыт"""
        circuit_breaker._state = CircuitState.OPEN
        
        async def any_operation(**kwargs):
            raise Exception("Should not be called")
        
        async def run_test():
            with pytest.raises(Exception) as exc_info:
                await circuit_breaker.execute(
                    operation="test_op",
                    func=any_operation,
                    fallback=None,
                )
            assert "DB unavailable" in str(exc_info.value)
        
        asyncio.run(run_test())
    
    def test_closes_after_successful_half_open_operation(self, circuit_breaker):
        """Закрывается после успешной операции в half_open состоянии"""
        circuit_breaker._state = CircuitState.HALF_OPEN
        
        async def successful_operation(**kwargs):
            return "success"
        
        async def run_test():
            result = await circuit_breaker.execute(
                operation="test_op",
                func=successful_operation,
            )
            assert result == "success"
            assert circuit_breaker.state == CircuitState.CLOSED
        
        asyncio.run(run_test())


class TestFallbackCache:
    """Тесты fallback кэша"""
    
    def test_cache_and_retrieve_fallback(self, circuit_breaker):
        """Кэширование и получение fallback значения"""
        circuit_breaker.cache_for_fallback("test_key", {"data": [1, 2, 3]})
        
        result = circuit_breaker.get_from_fallback("test_key")
        assert result == {"data": [1, 2, 3]}
    
    def test_fallback_expires_after_ttl(self, circuit_breaker):
        """Fallback значение истекает после TTL"""
        # Кэшируем с TTL 1 секунда
        circuit_breaker.cache_for_fallback("test_key", "value", ttl=1)
        
        # Ждем 2 секунды
        import time
        time.sleep(2)
        
        # Значение должно истечь
        result = circuit_breaker.get_from_fallback("test_key")
        assert result is None


class TestCircuitBreakerStats:
    """Тесты статистики"""
    
    def test_stats_tracking(self, circuit_breaker):
        """Отслеживание статистики"""
        async def successful_operation(**kwargs):
            return "success"
        
        async def failing_operation(**kwargs):
            raise Exception("error")
        
        async def fallback(**kwargs):
            return "fallback"
        
        async def run_test():
            # Успешная операция
            await circuit_breaker.execute("op1", successful_operation)
            
            # Неудачная операция (fallback не вызывается, так как circuit еще закрыт)
            try:
                await circuit_breaker.execute("op2", failing_operation, fallback=fallback)
            except Exception:
                pass  # Ожидаем исключение
            
            stats = circuit_breaker.get_stats()
            
            assert stats["stats"]["total_calls"] == 2
            assert stats["stats"]["successful_calls"] == 1
            assert stats["stats"]["failed_calls"] == 1
            # Fallback вызывается только когда circuit открыт
            assert stats["stats"]["fallback_calls"] == 0
        
        asyncio.run(run_test())
    
    def test_fallback_stats_when_circuit_open(self, circuit_breaker):
        """Статистика fallback когда circuit открыт"""
        async def failing_operation(**kwargs):
            raise Exception("error")
        
        async def fallback(**kwargs):
            return "fallback"
        
        async def run_test():
            # Открываем circuit вручную
            circuit_breaker._state = CircuitState.OPEN
            
            # Вызываем с fallback
            result = await circuit_breaker.execute("op1", failing_operation, fallback=fallback)
            assert result == "fallback"
            
            stats = circuit_breaker.get_stats()
            assert stats["stats"]["fallback_calls"] == 1
        
        asyncio.run(run_test())
    
    def test_reset_clears_stats(self, circuit_breaker):
        """Сброс очищает статистику"""
        circuit_breaker._stats.total_calls = 10
        circuit_breaker._stats.successful_calls = 5
        
        circuit_breaker.reset()
        
        stats = circuit_breaker.get_stats()
        assert stats["stats"]["total_calls"] == 0
        assert stats["stats"]["successful_calls"] == 0


class TestGlobalCircuitBreaker:
    """Тесты глобального Circuit Breaker"""
    
    def test_get_global_instance(self, global_circuit_breaker):
        """Получение глобального экземпляра"""
        assert global_circuit_breaker is not None
        assert isinstance(global_circuit_breaker, DBCircuitBreaker)
    
    def test_reset_global_instance(self):
        """Сброс глобального экземпляра"""
        cb1 = get_db_circuit_breaker()
        cb1._stats.total_calls = 100
        
        reset_db_circuit_breaker()
        
        cb2 = get_db_circuit_breaker()
        assert cb2 is not cb1  # Новый экземпляр
        stats = cb2.get_stats()
        assert stats["stats"]["total_calls"] == 0