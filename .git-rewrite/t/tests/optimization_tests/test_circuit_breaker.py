"""
Исправление 2: Circuit Breaker для LiteLLM

Тесты для проверки паттерна Circuit Breaker:
- Открытие после N ошибок
- Закрытие после timeout
- Half-open состояние для проверки восстановления
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


class CircuitBreakerError(Exception):
    """Ошибка для тестирования Circuit Breaker"""
    pass


class TestCircuitBreaker:
    """Тесты Circuit Breaker для LiteLLMService"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """
        Проверяет, что Circuit Breaker открывается после N неудачных запросов
        """
        from backend.runtime.litellm_service import LiteLLMService, CircuitBreaker
        
        service = LiteLLMService(api_key="test_key")
        service._circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            half_open_max_calls=1
        )
        
        # Имитируем 3 неудачных запроса
        for i in range(3):
            with patch.object(service, '_call_llm', new=AsyncMock(side_effect=CircuitBreakerError(f"Ошибка {i}"))):
                with pytest.raises(CircuitBreakerError):
                    await service.generate("Тест")
        
        # Circuit Breaker должен открыться
        assert service._circuit_breaker.is_open()
        assert not service._circuit_breaker.is_closed()

    @pytest.mark.asyncio
    async def test_circuit_breaker_rejects_when_open(self):
        """
        Проверяет, что Circuit Breaker отклоняет запросы в открытом состоянии
        """
        from backend.runtime.litellm_service import LiteLLMService, CircuitBreaker, CircuitBreakerOpenError
        
        service = LiteLLMService(api_key="test_key")
        service._circuit_breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        
        # Открываем Circuit Breaker
        service._circuit_breaker.open()
        
        # Запрос должен сразу вернуть ошибку
        with pytest.raises(CircuitBreakerOpenError):
            await service.generate("Тест")

    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_after_timeout(self):
        """
        Проверяет, что Circuit Breaker закрывается через timeout
        """
        from backend.runtime.litellm_service import LiteLLMService, CircuitBreaker
        
        service = LiteLLMService(api_key="test_key")
        service._circuit_breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=1,  # 1 секунда для теста
            half_open_max_calls=1
        )
        
        # Открываем
        service._circuit_breaker.open()
        assert service._circuit_breaker.is_open()
        
        # Ждём timeout + небольшой буфер
        await asyncio.sleep(1.1)
        
        # Circuit Breaker должен перейти в half-open
        assert service._circuit_breaker.is_half_open()

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_to_closed(self):
        """
        Проверяет переход из half-open в closed после успешного запроса
        """
        from backend.runtime.litellm_service import LiteLLMService, CircuitBreaker, LLMResponse
        
        service = LiteLLMService(api_key="test_key")
        service._circuit_breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=1,
            half_open_max_calls=1
        )
        
        # Открываем и ждём перехода в half-open
        service._circuit_breaker.open()
        await asyncio.sleep(1.1)
        
        assert service._circuit_breaker.is_half_open()
        
        # Успешный запрос
        with patch.object(service, '_call_llm', new=AsyncMock(return_value=LLMResponse(
            text="Успех",
            model="test",
            provider="test"
        ))):
            result = await service.generate("Тест")
            assert result.text == "Успех"
        
        # Circuit Breaker должен закрыться
        assert service._circuit_breaker.is_closed()

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_to_open(self):
        """
        Проверяет переход из half-open в open после неудачного запроса
        """
        from backend.runtime.litellm_service import LiteLLMService, CircuitBreaker
        
        service = LiteLLMService(api_key="test_key")
        service._circuit_breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=1,
            half_open_max_calls=1
        )
        
        # Открываем и ждём перехода в half-open
        service._circuit_breaker.open()
        await asyncio.sleep(1.1)
        
        assert service._circuit_breaker.is_half_open()
        
        # Неудачный запрос в half-open
        with patch.object(service, '_call_llm', new=AsyncMock(side_effect=CircuitBreakerError("Ошибка"))):
            with pytest.raises(CircuitBreakerError):
                await service.generate("Тест")
        
        # Circuit Breaker должен снова открыться
        assert service._circuit_breaker.is_open()

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_count_reset_on_success(self):
        """
        Проверяет, что счётчик ошибок сбрасывается после успешного запроса
        """
        from backend.runtime.litellm_service import LiteLLMService, CircuitBreaker, LLMResponse
        
        service = LiteLLMService(api_key="test_key")
        service._circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        # 2 неудачных запроса (ещё не открывает)
        for i in range(2):
            with patch.object(service, '_call_llm', new=AsyncMock(side_effect=CircuitBreakerError("Ошибка"))):
                with pytest.raises(CircuitBreakerError):
                    await service.generate("Тест")
        
        assert service._circuit_breaker._failure_count == 2
        assert service._circuit_breaker.is_closed()
        
        # Успешный запрос
        with patch.object(service, '_call_llm', new=AsyncMock(return_value=LLMResponse(
            text="Успех",
            model="test",
            provider="test"
        ))):
            await service.generate("Тест")
        
        # Счётчик должен сброситься
        assert service._circuit_breaker._failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_metrics(self):
        """
        Проверяет, что Circuit Breaker записывает метрики
        """
        from backend.runtime.litellm_service import LiteLLMService, CircuitBreaker
        
        service = LiteLLMService(api_key="test_key")
        service._circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        # Несколько запросов
        for i in range(5):
            with patch.object(service, '_call_llm', new=AsyncMock(side_effect=CircuitBreakerError("Ошибка"))):
                with pytest.raises((CircuitBreakerError, Exception)):
                    await service.generate("Тест")
        
        # Проверяем метрики
        metrics = service._circuit_breaker.get_metrics()
        
        assert metrics['total_requests'] == 5
        assert metrics['failure_count'] >= 3
        assert metrics['state'] == 'open'
        assert 'last_failure_time' in metrics


class TestCircuitBreakerConfiguration:
    """Тесты конфигурации Circuit Breaker"""

    @pytest.mark.asyncio
    async def test_custom_failure_threshold(self):
        """
        Проверяет настройку порога ошибок через переменную окружения
        """
        from backend.runtime.litellm_service import LiteLLMService, CircuitBreaker
        import os
        
        with patch.dict(os.environ, {"CIRCUIT_BREAKER_FAILURE_THRESHOLD": "5"}):
            service = LiteLLMService(api_key="test_key")
            service._circuit_breaker = CircuitBreaker(
                failure_threshold=int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "3"))
            )
            
            assert service._circuit_breaker.failure_threshold == 5

    @pytest.mark.asyncio
    async def test_custom_recovery_timeout(self):
        """
        Проверяет настройку timeout восстановления
        """
        from backend.runtime.litellm_service import LiteLLMService, CircuitBreaker
        import os
        
        with patch.dict(os.environ, {"CIRCUIT_BREAKER_RECOVERY_TIMEOUT": "30"}):
            service = LiteLLMService(api_key="test_key")
            service._circuit_breaker = CircuitBreaker(
                recovery_timeout=int(os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60"))
            )
            
            assert service._circuit_breaker.recovery_timeout == 30

    @pytest.mark.asyncio
    async def test_default_configuration(self):
        """
        Проверяет значения по умолчанию
        """
        from backend.runtime.litellm_service import CircuitBreaker
        
        cb = CircuitBreaker()
        
        assert cb.failure_threshold == 5  # По умолчанию
        assert cb.recovery_timeout == 60
        assert cb.half_open_max_calls == 1


class TestCircuitBreakerWithRealService:
    """Интеграционные тесты Circuit Breaker с LiteLLMService"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_invalid_key(self):
        """
        Проверяет, что Circuit Breaker открывается при неверном API ключе
        """
        from backend.runtime.litellm_service import LiteLLMService, CircuitBreaker
        
        service = LiteLLMService(api_key="invalid_key_12345")
        service._circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        # 2 неудачных запроса с неверным ключом
        for i in range(2):
            with pytest.raises(Exception):
                await service.generate("Тест")
        
        # Circuit Breaker должен открыться
        assert service._circuit_breaker.is_open()

    @pytest.mark.asyncio
    async def test_circuit_breaker_state_serialization(self):
        """
        Проверяет сериализацию состояния Circuit Breaker
        """
        from backend.runtime.litellm_service import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        # Открываем
        cb.open()
        
        # Сериализуем
        state = cb.to_dict()
        
        assert state['state'] == 'open'
        assert 'failure_count' in state
        assert 'last_failure_time' in state
        assert 'opened_at' in state


class TestCircuitBreakerEdgeCases:
    """Тесты граничных случаев Circuit Breaker"""

    @pytest.mark.asyncio
    async def test_rapid_success_of_failures(self):
        """
        Проверяет поведение при быстром потоке ошибок
        """
        from backend.runtime.litellm_service import LiteLLMService, CircuitBreaker
        
        service = LiteLLMService(api_key="test_key")
        service._circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        # 10 быстрых неудачных запросов
        for i in range(10):
            with patch.object(service, '_call_llm', new=AsyncMock(side_effect=CircuitBreakerError("Ошибка"))):
                with pytest.raises((CircuitBreakerError, Exception)):
                    await service.generate(f"Тест {i}")
        
        # Circuit Breaker должен быть открыт
        assert service._circuit_breaker.is_open()
        
        # Последующие запросы должны сразу отклоняться
        with pytest.raises(Exception):  # CircuitBreakerOpenError
            await service.generate("Тест после открытия")

    @pytest.mark.asyncio
    async def test_concurrent_requests_with_open_circuit(self):
        """
        Проверяет, что конкурентные запросы корректно обрабатываются
        при открытом Circuit Breaker
        """
        from backend.runtime.litellm_service import LiteLLMService, CircuitBreaker
        
        service = LiteLLMService(api_key="test_key")
        service._circuit_breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        
        # Открываем Circuit Breaker
        service._circuit_breaker.open()
        
        # 10 конкурентных запросов
        tasks = [service.generate(f"Тест {i}") for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Все должны вернуть ошибку Circuit Breaker
        for result in results:
            assert isinstance(result, Exception)

    @pytest.mark.asyncio
    async def test_circuit_breaker_does_not_affect_successful_requests(self):
        """
        Проверяет, что Circuit Breaker не влияет на успешные запросы
        """
        from backend.runtime.litellm_service import LiteLLMService, CircuitBreaker, LLMResponse
        
        service = LiteLLMService(api_key="test_key")
        service._circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        
        # 5 успешных запросов
        for i in range(5):
            with patch.object(service, '_call_llm', new=AsyncMock(return_value=LLMResponse(
                text=f"Ответ {i}",
                model="test",
                provider="test"
            ))):
                result = await service.generate(f"Тест {i}")
                assert result.text == f"Ответ {i}"
        
        # Circuit Breaker должен оставаться закрытым
        assert service._circuit_breaker.is_closed()
        assert service._circuit_breaker._failure_count == 0
