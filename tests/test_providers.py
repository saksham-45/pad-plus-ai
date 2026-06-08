"""
Тесты для GigaChat, OpenRouter и ProviderManager.

Использует mock HTTP-клиенты для изоляции от внешних API.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, Optional, AsyncGenerator
import json

# Добавляем корень проекта и backend в путь
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runtime.llm_service import LLMService, LLMResponse
from runtime.provider_manager import (
    ProviderManager,
    ProviderManagerError,
    AllProvidersFailedError,
    ProviderResult,
    _is_retryable_error,
    FALLBACK_ORDER,
    DEFAULT_FALLBACK_CHAIN,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_service():
    """Создаёт mock LLMService с контролируемыми ответами."""
    service = AsyncMock(spec=LLMService)
    
    # Настраиваем generate по умолчанию
    async def mock_generate(**kwargs):
        provider = kwargs.get('provider', 'openrouter')
        return LLMResponse(
            text=f"Ответ от {provider}",
            model=kwargs.get('model', 'test-model'),
            provider=provider,
            usage={"total_tokens": 10, "prompt_tokens": 5, "completion_tokens": 5},
            finish_reason="stop",
        )
    
    service.generate = mock_generate
    
    # Настраиваем generate_stream
    async def mock_generate_stream(**kwargs):
        yield "chunk1 "
        yield "chunk2"
    
    service.generate_stream = mock_generate_stream
    
    # Настраиваем close
    service.close_session = AsyncMock()
    
    return service


@pytest.fixture
def provider_manager(mock_llm_service):
    """ProviderManager с mock LLMService."""
    return ProviderManager(llm_service=mock_llm_service)


@pytest.fixture
def mock_http_response(status_code: int = 200, json_data: Optional[Dict] = None):
    """Создаёт mock HTTP-ответ."""
    response = AsyncMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.text = str(json_data or {})
    return response


# ============================================================================
# Тесты _is_retryable_error
# ============================================================================

class TestIsRetryableError:
    """Тесты для определения retryable ошибок."""

    def test_401_retryable(self):
        """401 Unauthorized — retryable."""
        assert _is_retryable_error(ValueError("401 Unauthorized"))
        assert _is_retryable_error(ValueError("HTTP error 401"))

    def test_5xx_retryable(self):
        """5xx server errors — retryable."""
        assert _is_retryable_error(ValueError("500 Server Error"))
        assert _is_retryable_error(ValueError("502 Bad Gateway"))
        assert _is_retryable_error(ValueError("503 Service Unavailable"))
        assert _is_retryable_error(ValueError("504 Gateway Timeout"))

    def test_timeout_retryable(self):
        """Timeout — retryable."""
        assert _is_retryable_error(TimeoutError("Connection timed out"))
        assert _is_retryable_error(ValueError("timeout"))
        assert _is_retryable_error(ValueError("timed out"))

    def test_connection_retryable(self):
        """Connection errors — retryable."""
        assert _is_retryable_error(ConnectionError("Connection refused"))
        assert _is_retryable_error(OSError("ECONNREFUSED"))
        assert _is_retryable_error(OSError("ECONNRESET"))

    def test_400_not_retryable(self):
        """400 Bad Request — not retryable."""
        assert not _is_retryable_error(ValueError("400 Bad Request"))

    def test_404_not_retryable(self):
        """404 Not Found — not retryable."""
        assert not _is_retryable_error(ValueError("404 Not Found"))

    def test_429_retryable(self):
        """429 Rate Limited — retryable."""
        assert _is_retryable_error(ValueError("429 Too Many Requests"))
        assert _is_retryable_error(ValueError("rate limit exceeded"))

    def test_unknown_error_default_retryable(self):
        """Неизвестная ошибка — считаем retryable."""
        assert _is_retryable_error(ValueError("Some random error"))


# ============================================================================
# Тесты ProviderManager.generate
# ============================================================================

class TestProviderManagerGenerate:
    """Тесты основной логики ProviderManager.generate()."""

    @patch.dict(os.environ, {"GIGACHAT_AUTH_KEY": ""})
    async def test_openrouter_success(self, mock_llm_service):
        """Успешный запрос через OpenRouter."""
        pm = ProviderManager(llm_service=mock_llm_service)
        result = await pm.generate(
            prompt="Привет",
            api_key="sk-test",
            provider="openrouter",
        )
        assert result.fallback_used is False
        assert result.response.provider == "openrouter"
        assert "Ответ от" in result.response.text
        assert result.attempted_providers == ["openrouter"]

    @patch.dict(os.environ, {"GIGACHAT_AUTH_KEY": ""})
    async def test_gigachat_success(self, mock_llm_service):
        """Успешный запрос через GigaChat."""
        pm = ProviderManager(llm_service=mock_llm_service)
        result = await pm.generate(
            prompt="Привет",
            api_key="gigachat-test-key",
            provider="gigachat",
        )
        assert result.fallback_used is False
        assert result.response.provider == "gigachat"

    @patch.dict(os.environ, {"GIGACHAT_AUTH_KEY": "sys-gigachat-key"})
    async def test_fallback_openrouter_to_gigachat(self, mock_llm_service):
        """
        Fallback OpenRouter → GigaChat при ошибке OpenRouter.
        GigaChat берётся из системного ключа.
        """
        # OpenRouter падает, GigaChat работает
        call_count = 0
        
        async def mock_generate_with_fallback(**kwargs):
            nonlocal call_count
            call_count += 1
            provider = kwargs.get('provider', '')
            
            if provider == 'openrouter':
                raise ValueError("500 Server Error")
            elif provider == 'gigachat':
                return LLMResponse(
                    text="Ответ от GigaChat (fallback)",
                    model="GigaChat",
                    provider="gigachat",
                    usage={"total_tokens": 5},
                    finish_reason="stop",
                )
            raise ValueError(f"Unknown provider: {provider}")
        
        mock_llm_service.generate = mock_generate_with_fallback
        pm = ProviderManager(llm_service=mock_llm_service)
        
        result = await pm.generate(
            prompt="Привет",
            api_key="sk-test",
            provider="openrouter",
        )
        
        assert result.fallback_used is True
        assert result.fallback_from == "openrouter"
        assert result.fallback_to == "gigachat"
        assert result.response.provider == "gigachat"
        assert call_count == 2

    @patch.dict(os.environ, {"GIGACHAT_AUTH_KEY": ""})
    async def test_fallback_all_fail(self, mock_llm_service):
        """Оба провайдера падают — AllProvidersFailedError."""
        async def mock_generate_fail(**kwargs):
            raise ValueError("500 Server Error")
        
        mock_llm_service.generate = mock_generate_fail
        pm = ProviderManager(llm_service=mock_llm_service)
        
        with pytest.raises(AllProvidersFailedError) as exc_info:
            await pm.generate(
                prompt="Привет",
                api_key="sk-test",
                provider="openrouter",
            )
        
        assert "openrouter" in exc_info.value.errors
        assert "gigachat" in exc_info.value.errors
        assert exc_info.value.original_provider == "openrouter"

    @patch.dict(os.environ, {"GIGACHAT_AUTH_KEY": ""})
    async def test_non_retryable_error_no_fallback(self, mock_llm_service):
        """
        400 Bad Request — не retryable, исключение сразу.
        """
        async def mock_generate_bad_request(**kwargs):
            raise ValueError("400 Bad Request")
        
        mock_llm_service.generate = mock_generate_bad_request
        pm = ProviderManager(llm_service=mock_llm_service)
        
        with pytest.raises(ProviderManagerError) as exc_info:
            await pm.generate(
                prompt="Привет",
                api_key="sk-test",
                provider="openrouter",
            )
        assert "критическую ошибку" in str(exc_info.value)

    @patch.dict(os.environ, {"GIGACHAT_AUTH_KEY": ""})
    async def test_auto_provider_selection(self, mock_llm_service):
        """
        Авто-режим (provider=None) — использует DEFAULT_FALLBACK_CHAIN.
        Если первый провайдер работает — возвращает его ответ.
        """
        pm = ProviderManager(llm_service=mock_llm_service)
        result = await pm.generate(
            prompt="Привет",
            api_key="sk-test",
        )
        # Первый в DEFAULT_FALLBACK_CHAIN — "openrouter"
        assert result.response.provider == "openrouter"
        assert result.fallback_used is False

    @patch.dict(os.environ, {"GIGACHAT_AUTH_KEY": ""})
    async def test_no_api_key_no_gigachat_key(self, mock_llm_service):
        """Нет ключа ни для одного провайдера — пропускаем."""
        pm = ProviderManager(llm_service=mock_llm_service)
        
        with pytest.raises(AllProvidersFailedError) as exc_info:
            await pm.generate(
                prompt="Привет",
                api_key=None,
            )
        assert "API ключ не настроен" in exc_info.value.errors.get("openrouter", "")

    @patch.dict(os.environ, {"GIGACHAT_AUTH_KEY": "sys-gigachat-key"})
    async def test_gigachat_key_from_env(self, mock_llm_service):
        """Системный GigaChat ключ из .env."""
        async def mock_generate_gigachat(**kwargs):
            key = kwargs.get('api_key', '')
            assert key == "sys-gigachat-key", "Должен использовать системный ключ"
            return LLMResponse(
                text="Ответ от GigaChat",
                model="GigaChat",
                provider="gigachat",
                usage={},
                finish_reason="stop",
            )
        
        mock_llm_service.generate = mock_generate_gigachat
        pm = ProviderManager(llm_service=mock_llm_service)
        
        result = await pm.generate(
            prompt="Привет",
            api_key=None,  # Нет пользовательского ключа
            provider="gigachat",
        )
        assert result.response.provider == "gigachat"
        assert result.fallback_used is False


# ============================================================================
# Тесты ProviderManager.generate_stream
# ============================================================================

class TestProviderManagerStream:
    """Тесты streaming с fallback."""

    @patch.dict(os.environ, {"GIGACHAT_AUTH_KEY": ""})
    async def test_stream_success(self, mock_llm_service):
        """Успешный стриминг."""
        pm = ProviderManager(llm_service=mock_llm_service)
        chunks = []
        async for chunk in pm.generate_stream(
            prompt="Привет",
            api_key="sk-test",
            provider="openrouter",
        ):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        assert "".join(chunks) == "chunk1 chunk2"

    @patch.dict(os.environ, {"GIGACHAT_AUTH_KEY": ""})
    async def test_stream_no_key_error(self, mock_llm_service):
        """Нет ключа — ошибка."""
        pm = ProviderManager(llm_service=mock_llm_service)
        
        with pytest.raises(ProviderManagerError, match="API ключ не настроен"):
            async for _ in pm.generate_stream(
                prompt="Привет",
                api_key=None,
            ):
                pass


    @patch.dict(os.environ, {"GIGACHAT_AUTH_KEY": "sys-gigachat-key"})
    async def test_stream_fallback_on_error(self, mock_llm_service):
        """
        Fallback в streaming: если первый провайдер упал до начала стрима,
        пробуем второй из цепочки.
        """
        call_count = 0
        
        async def mock_stream_fallback(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Первый вызов (OpenRouter) — падает
                raise ValueError("500 Server Error")
            # Второй вызов (GigaChat) — успех
            yield "fallback chunk 1 "
            yield "fallback chunk 2"
        
        mock_llm_service.generate_stream = mock_stream_fallback
        pm = ProviderManager(llm_service=mock_llm_service)
        
        chunks = []
        async for chunk in pm.generate_stream(
            prompt="Привет",
            api_key="sk-test",
            provider="openrouter",
        ):
            chunks.append(chunk)
        
        # Должны получить чанки от gigachat
        assert "".join(chunks) == "fallback chunk 1 fallback chunk 2"
        assert call_count == 2


# ============================================================================
# Тесты ProviderManager.test_connection
# ============================================================================

class TestProviderManagerTestConnection:
    """Тесты test_connection."""

    async def test_connection_success(self, mock_llm_service):
        """Успешное тестирование подключения."""
        pm = ProviderManager(llm_service=mock_llm_service)
        result = await pm.test_connection(
            api_key="sk-test",
            provider="openrouter",
        )
        assert result["success"] is True
        assert "успешно" in result["message"]
        assert result["model_tested"] is not None

    async def test_connection_failure(self, mock_llm_service):
        """Ошибка при тестировании."""
        async def mock_generate_fail(**kwargs):
            raise ValueError("Connection refused")
        
        mock_llm_service.generate = mock_generate_fail
        pm = ProviderManager(llm_service=mock_llm_service)
        
        result = await pm.test_connection(
            api_key="sk-test",
            provider="openrouter",
        )
        assert result["success"] is False
        assert "Connection refused" in result["message"]


# ============================================================================
# Тесты FALLBACK_ORDER
# ============================================================================

class TestFallbackOrder:
    """Тесты конфигурации fallback."""

    def test_openrouter_fallback_chain(self):
        """OpenRouter → GigaChat."""
        assert FALLBACK_ORDER["openrouter"] == ["openrouter", "gigachat"]

    def test_gigachat_no_fallback(self):
        """GigaChat — без fallback."""
        assert FALLBACK_ORDER["gigachat"] == ["gigachat"]

    def test_openai_fallback(self):
        """OpenAI → OpenRouter → GigaChat."""
        assert FALLBACK_ORDER["openai"] == ["openai", "openrouter", "gigachat"]

    def test_default_fallback_chain(self):
        """DEFAULT_FALLBACK_CHAIN — OpenRouter, GigaChat."""
        assert DEFAULT_FALLBACK_CHAIN == ["openrouter", "gigachat"]

    def test_unknown_provider_fallback(self):
        """Неизвестный провайдер — только он сам."""
        assert FALLBACK_ORDER.get("unknown", ["unknown"]) == ["unknown"]
        assert FALLBACK_ORDER.get("unknown", ["unknown"]) == ["unknown"]


# ============================================================================
# ProviderResult
# ============================================================================

class TestProviderResult:
    """Тесты ProviderResult."""

    def test_provider_result_defaults(self):
        """Поля по умолчанию."""
        mock_response = AsyncMock(spec=LLMResponse)
        mock_response.to_dict.return_value = {"text": "test"}
        
        result = ProviderResult(response=mock_response)
        assert result.fallback_used is False
        assert result.fallback_from is None
        assert result.fallback_to is None
        assert result.attempted_providers == []
        assert result.provider_errors == {}

    def test_provider_result_with_fallback(self):
        """Fallback информация."""
        mock_response = AsyncMock(spec=LLMResponse)
        mock_response.to_dict.return_value = {"text": "test"}
        
        result = ProviderResult(
            response=mock_response,
            fallback_used=True,
            fallback_from="openrouter",
            fallback_to="gigachat",
            attempted_providers=["openrouter", "gigachat"],
            provider_errors={"openrouter": "500 Server Error"},
        )
        
        assert result.fallback_used is True
        assert result.fallback_from == "openrouter"
        assert result.fallback_to == "gigachat"

    def test_provider_result_to_dict(self):
        """Преобразование в словарь."""
        mock_response = AsyncMock(spec=LLMResponse)
        mock_response.to_dict.return_value = {"text": "test", "model": "gpt-4"}
        
        result = ProviderResult(
            response=mock_response,
            fallback_used=True,
            fallback_from="openrouter",
            fallback_to="gigachat",
            attempted_providers=["openrouter", "gigachat"],
            provider_errors={"openrouter": "error"},
        )
        
        d = result.to_dict()
        assert d["fallback_used"] is True
        assert d["fallback_from"] == "openrouter"
        assert d["fallback_to"] == "gigachat"
        assert "response" in d


# ============================================================================
# Параметризованный тест: разные провайдеры
# ============================================================================

@pytest.mark.parametrize("provider,expected_chain", [
    ("openrouter", ["openrouter", "gigachat"]),
    ("gigachat", ["gigachat"]),
    ("openai", ["openai", "openrouter", "gigachat"]),
    ("google", ["google", "openrouter", "gigachat"]),
    ("anthropic", ["anthropic", "openrouter", "gigachat"]),
    ("groq", ["groq", "openrouter", "gigachat"]),
])
def test_fallback_chain_for_providers(provider, expected_chain):
    """Проверка цепочек fallback для всех провайдеров."""
    chain = FALLBACK_ORDER.get(provider, [provider])
    assert chain == expected_chain


@pytest.mark.parametrize("error_msg,expected_retryable", [
    ("401 Unauthorized", True),
    ("403 Forbidden", True),
    ("429 Rate limit exceeded", True),
    ("500 Internal Server Error", True),
    ("502 Bad Gateway", True),
    ("503 Service Unavailable", True),
    ("Connection timed out", True),
    ("400 Bad Request", False),
    ("404 Not Found", False),
])
def test_is_retryable_error_parametrized(error_msg, expected_retryable):
    """Параметризованный тест для _is_retryable_error."""
    assert _is_retryable_error(ValueError(error_msg)) == expected_retryable


# ============================================================================
# Запуск асинхронных тестов
# ============================================================================

@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()