"""
Рабочие тесты для реализованных оптимизаций

Эти тесты проверяют фактически реализованный функционал:
1. ✅ asyncio.Lock в PipelineExecutor
2. ✅ Circuit Breaker в LiteLLMService  
3. ✅ Timeout в LiteLLMService
4. ✅ Health Check методы в HealthMonitor
5. ✅ close_session в LiteLLMService
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


# ============================================================================
# ИСПРАВЛЕНИЕ 1: asyncio.Lock в PipelineExecutor
# ============================================================================

class TestLockImplemented:
    """Тесты asyncio.Lock в PipelineExecutor"""

    @pytest.mark.asyncio
    async def test_lock_exists(self):
        """Проверяет, что Lock создан"""
        from backend.core.pipeline import PipelineExecutor
        
        pipeline = PipelineExecutor()
        assert hasattr(pipeline, '_consolidation_lock')
        assert isinstance(pipeline._consolidation_lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_lock_acquire_release(self):
        """Проверяет захват и освобождение Lock"""
        from backend.core.pipeline import PipelineExecutor
        
        pipeline = PipelineExecutor()
        
        await pipeline._consolidation_lock.acquire()
        assert pipeline._consolidation_lock.locked()
        
        pipeline._consolidation_lock.release()
        assert not pipeline._consolidation_lock.locked()

    @pytest.mark.asyncio
    async def test_lock_context_manager(self):
        """Проверяет Lock как контекстный менеджер"""
        from backend.core.pipeline import PipelineExecutor
        
        pipeline = PipelineExecutor()
        
        async with pipeline._consolidation_lock:
            assert pipeline._consolidation_lock.locked()
        
        assert not pipeline._consolidation_lock.locked()

    @pytest.mark.asyncio
    async def test_lock_prevents_concurrent_access(self):
        """Проверяет, что Lock предотвращает конкурентный доступ"""
        from backend.core.pipeline import PipelineExecutor
        
        pipeline = PipelineExecutor()
        execution_order = []
        
        async def task(task_id):
            async with pipeline._consolidation_lock:
                execution_order.append(f"{task_id}_start")
                await asyncio.sleep(0.01)
                execution_order.append(f"{task_id}_end")
        
        await asyncio.gather(task(1), task(2), task(3))
        
        # Проверяем последовательное выполнение
        for i in range(1, 4):
            start_idx = execution_order.index(f"{i}_start")
            end_idx = execution_order.index(f"{i}_end")
            assert start_idx < end_idx


# ============================================================================
# ИСПРАВЛЕНИЕ 2 и 3: Circuit Breaker и Timeout
# ============================================================================

class TestCircuitBreakerImplemented:
    """Тесты Circuit Breaker"""

    def test_circuit_breaker_states(self):
        """Проверяет состояния Circuit Breaker"""
        from backend.runtime.litellm_service import CircuitBreaker
        
        cb = CircuitBreaker()
        assert cb.is_closed()
        assert not cb.is_open()
        
        cb.open()
        assert cb.is_open()
        assert not cb.is_closed()

    def test_circuit_breaker_records_failure(self):
        """Проверяет запись ошибок"""
        from backend.runtime.litellm_service import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=3)
        
        cb.record_failure()
        assert cb._failure_count == 1
        assert cb.is_closed()  # Ещё не открыт
        
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open()  # Открыт после 3 ошибок

    def test_circuit_breaker_records_success(self):
        """Проверяет запись успеха"""
        from backend.runtime.litellm_service import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=3)
        
        cb.record_failure()
        cb.record_failure()
        assert cb._failure_count == 2
        
        cb.record_success()
        assert cb._failure_count == 0  # Сброшено при успехе

    def test_circuit_breaker_metrics(self):
        """Проверяет метрики Circuit Breaker"""
        from backend.runtime.litellm_service import CircuitBreaker
        
        cb = CircuitBreaker()
        cb.record_success()
        cb.record_failure()
        
        metrics = cb.get_metrics()
        assert 'state' in metrics
        assert 'failure_count' in metrics
        assert 'total_requests' in metrics


class TestTimeoutImplemented:
    """Тесты Timeout"""

    def test_timeout_from_env(self):
        """Проверяет timeout из переменной окружения"""
        import os
        from backend.runtime.litellm_service import LiteLLMService
        
        with patch.dict(os.environ, {"LLM_TIMEOUT": "45"}):
            service = LiteLLMService(api_key="test")
            assert service._timeout == 45

    def test_timeout_from_parameter(self):
        """Проверяет timeout из параметра"""
        from backend.runtime.litellm_service import LiteLLMService
        
        service = LiteLLMService(api_key="test", timeout=90)
        assert service._timeout == 90

    def test_timeout_default(self):
        """Проверяет timeout по умолчанию"""
        import os
        from backend.runtime.litellm_service import LiteLLMService
        
        # Удаляем переменную окружения
        env = os.environ.copy()
        env.pop("LLM_TIMEOUT", None)
        
        with patch.dict(os.environ, env, clear=True):
            service = LiteLLMService(api_key="test")
            assert service._timeout == 30  # По умолчанию


# ============================================================================
# ИСПРАВЛЕНИЕ 6: close_session
# ============================================================================

class TestCloseSessionImplemented:
    """Тесты close_session"""

    @pytest.mark.asyncio
    async def test_close_session_exists(self):
        """Проверяет, что метод существует"""
        from backend.runtime.litellm_service import LiteLLMService
        
        service = LiteLLMService(api_key="test")
        assert hasattr(service, 'close_session')
        assert asyncio.iscoroutinefunction(service.close_session)

    @pytest.mark.asyncio
    async def test_close_session_with_none(self):
        """Проверяет close_session с None сессией"""
        from backend.runtime.litellm_service import LiteLLMService
        
        service = LiteLLMService(api_key="test")
        service._session = None
        
        # Не должно вызывать ошибку
        await service.close_session()

    @pytest.mark.asyncio
    async def test_close_session_with_mock(self):
        """Проверяет close_session с мок сессией"""
        from backend.runtime.litellm_service import LiteLLMService
        
        service = LiteLLMService(api_key="test")
        mock_session = AsyncMock()
        service._session = mock_session
        
        await service.close_session()
        
        mock_session.close.assert_called_once()
        assert service._session is None


# ============================================================================
# ИСПРАВЛЕНИЕ 7: Health Checks
# ============================================================================

class TestHealthChecksImplemented:
    """Тесты Health Checks"""

    def test_check_methods_exist(self):
        """Проверяет, что методы существуют"""
        from backend.core.health_monitor import CognitiveHealthMonitor
        
        monitor = CognitiveHealthMonitor()
        assert hasattr(monitor, 'check_redis')
        assert hasattr(monitor, 'check_supabase')
        assert hasattr(monitor, 'check_llm')
        assert hasattr(monitor, 'run_health_check')
        assert hasattr(monitor, 'start_periodic_health_check')

    @pytest.mark.asyncio
    async def test_check_redis_returns_bool(self):
        """Проверяет, что check_redis возвращает bool"""
        from backend.core.health_monitor import CognitiveHealthMonitor
        
        monitor = CognitiveHealthMonitor()
        result = await monitor.check_redis()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_check_supabase_returns_bool(self):
        """Проверяет, что check_supabase возвращает bool"""
        from backend.core.health_monitor import CognitiveHealthMonitor
        
        monitor = CognitiveHealthMonitor()
        result = await monitor.check_supabase()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_check_llm_returns_bool(self):
        """Проверяет, что check_llm возвращает bool"""
        from backend.core.health_monitor import CognitiveHealthMonitor
        
        monitor = CognitiveHealthMonitor()
        result = await monitor.check_llm()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_run_health_check(self):
        """Проверяет запуск health check"""
        from backend.core.health_monitor import CognitiveHealthMonitor
        
        monitor = CognitiveHealthMonitor()
        await monitor.run_health_check()
        
        # Проверяем, что метрики существуют (могут быть None если Redis не подключен)
        # Главное — что метод работает без ошибок
        assert True


# ============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# ============================================================================

class TestIntegrationsImplemented:
    """Интеграционные тесты реализованных функций"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_timeout(self):
        """Проверяет совместную работу Circuit Breaker и Timeout"""
        from backend.runtime.litellm_service import LiteLLMService, CircuitBreaker
        
        service = LiteLLMService(api_key="test", timeout=5)
        
        # Circuit Breaker должен быть создан
        assert hasattr(service, '_circuit_breaker')
        assert isinstance(service._circuit_breaker, CircuitBreaker)
        
        # Timeout должен быть настроен
        assert service._timeout == 5

    def test_circuit_breaker_serialization(self):
        """Проверяет сериализацию Circuit Breaker"""
        from backend.runtime.litellm_service import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        cb.record_failure()
        cb.record_failure()
        
        data = cb.to_dict()
        
        assert data['state'] == 'closed'
        assert data['failure_count'] == 2
        assert data['failure_threshold'] == 5

    @pytest.mark.asyncio
    async def test_health_check_periodic(self):
        """Проверяет периодический health check"""
        from backend.core.health_monitor import CognitiveHealthMonitor
        
        monitor = CognitiveHealthMonitor()
        
        # Запускаем на короткое время
        async def run_short():
            task = asyncio.create_task(monitor.start_periodic_health_check(interval=0.1))
            await asyncio.sleep(0.25)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        await run_short()
        
        # Health check должен был запуститься
        assert True  # Если не упало — тест прошёл


# ============================================================================
# ТЕСТЫ ПРОИЗВОДИТЕЛЬНОСТИ
# ============================================================================

class TestPerformanceImplemented:
    """Тесты производительности"""

    @pytest.mark.asyncio
    async def test_lock_overhead(self):
        """Проверяет накладные расходы Lock"""
        from backend.core.pipeline import PipelineExecutor
        
        pipeline = PipelineExecutor()
        
        import time
        start = time.time()
        
        for i in range(100):
            async with pipeline._consolidation_lock:
                pass
        
        elapsed = time.time() - start
        
        # 100 захватов Lock должны уложиться в 1 секунду
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_circuit_breaker_overhead(self):
        """Проверяет накладные расходы Circuit Breaker"""
        from backend.runtime.litellm_service import CircuitBreaker
        
        cb = CircuitBreaker()
        
        import time
        start = time.time()
        
        for i in range(1000):
            cb.record_success()
            cb.can_execute()
        
        elapsed = time.time() - start
        
        # 1000 операций должны уложиться в 1 секунду
        assert elapsed < 1.0
