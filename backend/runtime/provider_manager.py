"""
ProviderManager — управление выбором провайдера и fallback логика.

Отвечает за:
- Выбор провайдера (явный или авто-режим)
- Fallback OpenRouter → GigaChat при ошибках
- Тестирование подключения
- Получение списка моделей

Использует LLMService для непосредственной отправки HTTP-запросов.
"""

from typing import Optional, Dict, Any, List, AsyncGenerator, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger("padplus.provider_manager")

from runtime.llm_service import LLMService, LLMResponse, get_llm_service


FALLBACK_ORDER: Dict[str, List[str]] = {
    "openrouter": ["openrouter"],
    "gigachat": ["gigachat"],
    "openai": ["openai"],
    "google": ["google"],
    "anthropic": ["anthropic"],
    "groq": ["groq"],
}

DEFAULT_FALLBACK_CHAIN = ["openrouter"]


class ProviderManagerError(Exception):
    """Ошибка ProviderManager"""
    pass


class AllProvidersFailedError(ProviderManagerError):
    """Все провайдеры из цепочки fallback вернули ошибку"""
    def __init__(self, errors: Dict[str, str], original_provider: Optional[str] = None):
        self.errors = errors
        self.original_provider = original_provider
        details = "; ".join(f"{p}: {e}" for p, e in errors.items())
        super().__init__(f"Все провайдеры недоступны [{details}]")


@dataclass
class ProviderResult:
    """Результат работы ProviderManager с информацией о fallback"""
    response: LLMResponse
    fallback_used: bool = False
    fallback_from: Optional[str] = None
    fallback_to: Optional[str] = None
    attempted_providers: List[str] = field(default_factory=list)
    provider_errors: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "response": self.response.to_dict(),
            "fallback_used": self.fallback_used,
            "fallback_from": self.fallback_from,
            "fallback_to": self.fallback_to,
            "attempted_providers": self.attempted_providers,
            "provider_errors": self.provider_errors,
        }


def _is_retryable_error(error: Exception) -> bool:
    """
    Определяет, стоит ли повторять запрос через другой провайдер.
    
    Retryable ошибки:
    - 401 Unauthorized (возможно, ключ для этого провайдера невалиден)
    - 429 Rate limited
    - 5xx Server errors
    - Timeout
    - Connection errors
    
    Non-retryable:
    - 400 Bad request (проблема с форматом запроса)
    - 404 Not found
    """
    error_str = str(error).lower()
    
    # Retryable
    if any(phrase in error_str for phrase in [
        "401", "unauthorized", "403", "429", "rate limit",
        "500", "502", "503", "504", "5xx", "server error",
        "timeout", "timed out", "connection", "econnrefused",
        "econnreset", "ehostunreach",
    ]):
        return True
    
    # Non-retryable
    if any(phrase in error_str for phrase in [
        "400", "bad request", "402", "payment required", "404", "not found",
    ]):
        return False
    
    # По умолчанию считаем retryable для безопасности
    return True


class ProviderManager:
    """
    Менеджер провайдеров с поддержкой fallback.
    
    Использование:
        pm = ProviderManager()
        result = await pm.generate(prompt="...", api_key=key, provider="openrouter")
        if result.fallback_used:
            print(f"Fallback: {result.fallback_from} → {result.fallback_to}")
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self._llm = llm_service or get_llm_service()

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> ProviderResult:
        """
        Генерирует ответ.
        
        Если указан конкретный провайдер — только он и пробуется.
        Если None — авто-выбор с fallback.
        """
        if provider:
            unique_chain = [provider]
            gigachat_api_key = self._get_gigachat_key()
        else:
            unique_chain = DEFAULT_FALLBACK_CHAIN.copy()
            gigachat_api_key = None

        attempted_providers: List[str] = []
        provider_errors: Dict[str, str] = {}

        for attempt_idx, current_provider in enumerate(unique_chain):
            attempted_providers.append(current_provider)

            try:
                if current_provider == "gigachat":
                    current_key = gigachat_api_key or api_key
                else:
                    current_key = api_key

                if not current_key:
                    provider_errors[current_provider] = "API ключ не настроен"
                    logger.warning(f"⚠️ Provider {current_provider}: пропущен (нет ключа)")
                    continue

                response = await self._llm.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    api_key=current_key,
                    model=model,
                    provider=current_provider,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                    **kwargs,
                )

                return ProviderResult(
                    response=response,
                    fallback_used=attempt_idx > 0,
                    fallback_from=unique_chain[0] if attempt_idx > 0 else None,
                    fallback_to=current_provider if attempt_idx > 0 else None,
                    attempted_providers=attempted_providers,
                    provider_errors=provider_errors,
                )

            except Exception as e:
                raw_msg = str(e)
                # Ошибки провайдеров могут содержать NBSP (\xa0) и другие не-ASCII символы.
                # Не кодируем/не приводим к ascii — логируем безопасно как Unicode.
                error_msg = raw_msg[:500]
                provider_errors[current_provider] = error_msg
                safe_preview = error_msg[:200]
                # Иногда ошибка может содержать не-ascii (например NBSP). Логируем как unicode, без ascii-коэрсии.
                logger.warning(f"⚠️ Provider {current_provider} failed: {safe_preview}")


                if not _is_retryable_error(e):
                    raise ProviderManagerError(
                        f"Провайдер {current_provider} недоступен: {error_msg}"
                    ) from e

                if attempt_idx == len(unique_chain) - 1:
                    break

                await asyncio.sleep(0.5)

        raise AllProvidersFailedError(
            errors=provider_errors,
            original_provider=provider,
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        Streaming для выбранного провайдера.
        Если провайдер не указан — авто-выбор.
        """
        if provider:
            chain = [provider]
        else:
            chain = DEFAULT_FALLBACK_CHAIN.copy()

        for current_provider in chain:
            if current_provider == "gigachat":
                current_key = self._get_gigachat_key() or api_key
            else:
                current_key = api_key

            if not current_key:
                logger.warning(f"⚠️ Stream: {current_provider} пропущен (нет ключа)")
                continue

            try:
                async for chunk in self._llm.generate_stream(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    api_key=current_key,
                    model=model,
                    provider=current_provider,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                ):
                    yield chunk
                return
            except Exception as e:
                raw_msg = str(e)
                error_msg = raw_msg[:500]
                logger.warning(f"⚠️ Stream: {current_provider} failed: {error_msg[:200]}")

                if not _is_retryable_error(e) or len(chain) == 1:
                    raise ProviderManagerError(f"Провайдер {current_provider} недоступен: {error_msg}") from e

                continue

        raise ProviderManagerError("Все провайдеры недоступны")

    async def test_connection(
        self,
        api_key: str,
        provider: str,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Тестирует подключение к провайдеру.
        
        Returns:
            Dict с ключами: success, message, model_tested, error
        """
        try:
            # Если модель не указана — используем дефолтную
            if not model:
                from runtime.llm_service import DEFAULT_MODELS
                model = DEFAULT_MODELS.get(provider, "gpt-4o-mini")
            
            response = await self._llm.generate(
                prompt="test",
                system_prompt="test",
                api_key=api_key,
                model=model,
                provider=provider,
                max_tokens=5,
            )
            
            return {
                "success": True,
                "message": "Подключение успешно",
                "model_tested": response.model,
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "model_tested": model,
            }

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """Возвращает список доступных провайдеров с их статусом"""
        return [
            {
                "id": "openrouter",
                "name": "OpenRouter",
                "has_key": False,
                "is_system": False,
            },
            {
                "id": "gigachat",
                "name": "GigaChat",
                "has_key": False,
                "is_system": False,
            },
        ]

    async def close(self) -> None:
        """Закрывает сессию"""
        await self._llm.close_session()

    def has_active_providers(self) -> bool:
        """Проверяет, доступен ли хотя бы один провайдер."""
        return True

    def _get_gigachat_key(self) -> Optional[str]:
        """Получает системный ключ GigaChat из .env"""
        import os
        key = os.getenv("GIGACHAT_AUTH_KEY")
        return key.strip() if key and key.strip() else None


# === Single instance ===
_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """Возвращает singleton ProviderManager"""
    global _manager
    if _manager is None:
        _manager = ProviderManager()
    return _manager