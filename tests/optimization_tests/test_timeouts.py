"""
Исправление 3: Timeout на LLM запросы

Тесты для проверки timeout механизмов:
- Запрос завершается по timeout
- Быстрый запрос успевает выполниться
- Настраиваемый timeout через переменную окружения
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


class TestTimeout:
    """Тесты timeout для LLM запросов"""

    @pytest.mark.asyncio
    async def test_request_timeout(self):
        """
        Проверяет, что запрос завершается по timeout
        """
        from backend.runtime.litellm_service import LiteLLMService
        
        # Создаём сервис с коротким timeout (1 секунда)
        service = LiteLLMService(api_key="test_key", timeout=1)
        
        # Имитируем медленный ответ (5 секунд)
        with patch('backend.runtime.litellm_service.acompletion') as mock_completion:
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(5)
                return None
            
            mock_completion.side_effect = slow_response
            
            # Запрос должен завершиться по timeout
            with pytest.raises(asyncio.TimeoutError):
                await service.generate("Тест")

    @pytest.mark.asyncio
    async def test_fast_request_completes(self):
        """
        Проверяет, что быстрый запрос успевает выполниться
        """
        from backend.runtime.litellm_service import LiteLLMService, LLMResponse
        
        service = LiteLLMService(api_key="test_key", timeout=30)
        
        # Имитируем быстрый ответ (0.1 секунды)
        with patch('backend.runtime.litellm_service.acompletion') as mock_completion:
            mock_completion.return_value = AsyncMock(
                choices=[
                    AsyncMock(
                        message=AsyncMock(content="Быстрый ответ"),
                        finish_reason="stop"
                    )
                ],
                usage=AsyncMock(
                    prompt_tokens=10,
                    completion_tokens=20,
                    total_tokens=30
                )
            )
            
            result = await service.generate("Тест")
            
            assert result.text == "Быстрый ответ"
            assert result.provider is not None

    @pytest.mark.asyncio
    async def test_configurable_timeout_from_env(self):
        """
        Проверяет, что timeout настраивается через LLM_TIMEOUT
        """
        import os
        from backend.runtime.litellm_service import LiteLLMService
        
        # Timeout из переменной окружения
        with patch.dict(os.environ, {"LLM_TIMEOUT": "10"}):
            service = LiteLLMService(api_key="test_key")
            assert service._timeout == 10
        
        # Timeout по умолчанию
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("LLM_TIMEOUT", None)
            service = LiteLLMService(api_key="test_key")
            assert service._timeout == 30  # По умолчанию
        
        # Timeout из параметра конструктора
        service = LiteLLMService(api_key="test_key", timeout=60)
        assert service._timeout == 60

    @pytest.mark.asyncio
    async def test_timeout_error_message(self):
        """
        Проверяет, что ошибка timeout содержит понятное сообщение
        """
        from backend.runtime.litellm_service import LiteLLMService
        
        service = LiteLLMService(api_key="test_key", timeout=1)
        
        with patch('backend.runtime.litellm_service.acompletion') as mock_completion:
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(5)
                return None
            
            mock_completion.side_effect = slow_response
            
            with pytest.raises(asyncio.TimeoutError) as exc_info:
                await service.generate("Тест")
            
            # Проверяем, что сообщение содержит полезную информацию
            error_message = str(exc_info.value)
            assert "timeout" in error_message.lower() or "1" in error_message

    @pytest.mark.asyncio
    async def test_timeout_with_circuit_breaker(self):
        """
        Проверяет, что timeout корректно взаимодействует с Circuit Breaker
        """
        from backend.runtime.litellm_service import LiteLLMService
        
        service = LiteLLMService(api_key="test_key", timeout=1)
        service._circuit_breaker.failure_threshold = 3
        
        # 3 запроса с timeout
        for i in range(3):
            with patch('backend.runtime.litellm_service.acompletion') as mock_completion:
                async def slow_response(*args, **kwargs):
                    await asyncio.sleep(5)
                    return None
                
                mock_completion.side_effect = slow_response
                
                with pytest.raises(asyncio.TimeoutError):
                    await service.generate(f"Тест {i}")
        
        # Circuit Breaker должен открыться после 3 ошибок
        assert service._circuit_breaker.is_open()

    @pytest.mark.asyncio
    async def test_different_timeouts_for_different_models(self):
        """
        Проверяет, что можно использовать разные timeout для разных моделей
        """
        from backend.runtime.litellm_service import LiteLLMService
        
        # Сервис с коротким timeout для быстрых моделей
        fast_service = LiteLLMService(api_key="test_key", timeout=5)
        
        # Сервис с длинным timeout для медленных моделей
        slow_service = LiteLLMService(api_key="test_key", timeout=60)
        
        assert fast_service._timeout == 5
        assert slow_service._timeout == 60


class TestTimeoutIntegration:
    """Интеграционные тесты timeout"""

    @pytest.mark.asyncio
    async def test_timeout_does_not_affect_other_requests(self):
        """
        Проверяет, что timeout одного запроса не влияет на другие
        """
        from backend.runtime.litellm_service import LiteLLMService, LLMResponse
        
        service = LiteLLMService(api_key="test_key", timeout=1)
        
        # Первый запрос — медленный (должен таймаутиться)
        with patch('backend.runtime.litellm_service.acompletion') as mock_completion:
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(5)
                return None
            
            mock_completion.side_effect = slow_response
            
            with pytest.raises(asyncio.TimeoutError):
                await service.generate("Медленный запрос")
        
        # Второй запрос — быстрый (должен выполниться)
        with patch('backend.runtime.litellm_service.acompletion') as mock_completion:
            mock_completion.return_value = AsyncMock(
                choices=[
                    AsyncMock(
                        message=AsyncMock(content="Быстрый ответ"),
                        finish_reason="stop"
                    )
                ]
            )
            
            result = await service.generate("Быстрый запрос")
            assert result.text == "Быстрый ответ"

    @pytest.mark.asyncio
    async def test_concurrent_requests_with_timeout(self):
        """
        Проверяет работу timeout при конкурентных запросах
        """
        from backend.runtime.litellm_service import LiteLLMService, LLMResponse
        
        service = LiteLLMService(api_key="test_key", timeout=2)
        
        async def make_request(request_id):
            with patch('backend.runtime.litellm_service.acompletion') as mock_completion:
                if request_id % 2 == 0:
                    # Чётные запросы — медленные
                    async def slow_response(*args, **kwargs):
                        await asyncio.sleep(5)
                        return None
                    mock_completion.side_effect = slow_response
                    
                    with pytest.raises(asyncio.TimeoutError):
                        await service.generate(f"Запрос {request_id}")
                    return "timeout"
                else:
                    # Нечётные запросы — быстрые
                    mock_completion.return_value = AsyncMock(
                        choices=[
                            AsyncMock(
                                message=AsyncMock(content=f"Ответ {request_id}"),
                                finish_reason="stop"
                            )
                        ]
                    )
                    result = await service.generate(f"Запрос {request_id}")
                    return result.text
        
        # Запускаем 10 конкурентных запросов
        tasks = [make_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Проверяем результаты
        timeouts = sum(1 for r in results if r == "timeout")
        successes = sum(1 for r in results if isinstance(r, str) and r.startswith("Ответ"))
        
        assert timeouts == 5  # 5 чётных запросов
        assert successes == 5  # 5 нечётных запросов

    @pytest.mark.asyncio
    async def test_timeout_with_retry_logic(self):
        """
        Проверяет, что timeout корректно работает с retry логикой
        """
        from backend.runtime.litellm_service import LiteLLMService, LLMResponse
        
        service = LiteLLMService(api_key="test_key", timeout=1)
        
        call_count = 0
        
        async def flaky_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                # Первые 2 вызова — медленные
                await asyncio.sleep(5)
                return None
            else:
                # Третий вызов — быстрый
                return AsyncMock(
                    choices=[
                        AsyncMock(
                            message=AsyncMock(content="Успешный ответ"),
                            finish_reason="stop"
                        )
                    ]
                )
        
        # Retry логика
        max_retries = 3
        for attempt in range(max_retries):
            with patch('backend.runtime.litellm_service.acompletion', side_effect=flaky_response):
                try:
                    result = await service.generate("Тест")
                    assert result.text == "Успешный ответ"
                    break
                except asyncio.TimeoutError:
                    if attempt == max_retries - 1:
                        raise  # Последний attempt тоже таймаутился
                    continue
        
        # Проверяем, что было 3 попытки
        assert call_count == 3


class TestTimeoutEdgeCases:
    """Тесты граничных случаев timeout"""

    @pytest.mark.asyncio
    async def test_zero_timeout(self):
        """
        Проверяет поведение при timeout = 0
        """
        from backend.runtime.litellm_service import LiteLLMService
        
        service = LiteLLMService(api_key="test_key", timeout=0)
        
        # Даже с timeout=0 запрос должен хотя бы начать выполняться
        with patch('backend.runtime.litellm_service.acompletion') as mock_completion:
            mock_completion.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(asyncio.TimeoutError):
                await service.generate("Тест")

    @pytest.mark.asyncio
    async def test_very_large_timeout(self):
        """
        Проверяет поведение при очень большом timeout
        """
        from backend.runtime.litellm_service import LiteLLMService, LLMResponse
        
        service = LiteLLMService(api_key="test_key", timeout=3600)  # 1 час
        
        with patch('backend.runtime.litellm_service.acompletion') as mock_completion:
            mock_completion.return_value = AsyncMock(
                choices=[
                    AsyncMock(
                        message=AsyncMock(content="Ответ"),
                        finish_reason="stop"
                    )
                ]
            )
            
            result = await service.generate("Тест")
            assert result.text == "Ответ"

    @pytest.mark.asyncio
    async def test_timeout_precision(self):
        """
        Проверяет, что timeout работает с точностью до секунды
        """
        from backend.runtime.litellm_service import LiteLLMService
        
        service = LiteLLMService(api_key="test_key", timeout=2)
        
        start = datetime.now()
        
        with patch('backend.runtime.litellm_service.acompletion') as mock_completion:
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(10)
                return None
            
            mock_completion.side_effect = slow_response
            
            with pytest.raises(asyncio.TimeoutError):
                await service.generate("Тест")
        
        elapsed = (datetime.now() - start).total_seconds()
        
        # Timeout должен сработать примерно через 2 секунды (с небольшой погрешностью)
        assert 1.5 < elapsed < 3.0
