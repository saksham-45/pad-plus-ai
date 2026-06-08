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
    "openrouter": ["openrouter", "gigachat"],
    "gigachat": ["gigachat"],
    "openai": ["openai", "openrouter", "gigachat"],
    "google": ["google", "openrouter", "gigachat"],
    "anthropic": ["anthropic", "openrouter", "gigachat"],
    "groq": ["groq", "openrouter", "gigachat"],
}

DEFAULT_FALLBACK_CHAIN = ["openrouter", "gigachat"]


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
        "400", "bad request", "404", "not found",
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
        Генерирует ответ с поддержкой fallback.
        
        Args:
            provider: Целевой провайдер. Если None — авто-выбор.
            Остальные параметры как у LLMService.generate()
        
        Returns:
            ProviderResult с ответом и информацией о fallback
        """
        # Определяем цепочку провайдеров для попыток
        if provider:
            chain = FALLBACK_ORDER.get(provider, [provider])
        else:
            chain = DEFAULT_FALLBACK_CHAIN.copy()

        # Удаляем дубликаты, сохраняя порядок
        seen = set()
        unique_chain = []
        for p in chain:
            if p not in seen:
                seen.add(p)
                unique_chain.append(p)

        attempted_providers: List[str] = []
        provider_errors: Dict[str, str] = {}
        
        # Если указан конкретный провайдер — пробуем только его цепочку
        if provider and provider not in unique_chain:
            unique_chain.insert(0, provider)

        # Если провайдер не указан — используем дефолтную цепочку
        if not provider:
            unique_chain = DEFAULT_FALLBACK_CHAIN.copy()

        # Определяем ключи для каждого провайдера
        # Если api_key один — он универсальный (OpenRouter)
        # Для GigaChat нужен отдельный ключ из .env
        gigachat_api_key = self._get_gigachat_key()

        for attempt_idx, current_provider in enumerate(unique_chain):
            attempted_providers.append(current_provider)
            
            try:
                current_key = api_key
                # Для GigaChat используем системный ключ, если не передан
                if current_provider == "gigachat" and not current_key:
                    current_key = gigachat_api_key
                
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

                # Успех
                fallback_from = unique_chain[0] if attempt_idx > 0 else None
                return ProviderResult(
                    response=response,
                    fallback_used=attempt_idx > 0,
                    fallback_from=fallback_from,
                    fallback_to=current_provider if attempt_idx > 0 else None,
                    attempted_providers=attempted_providers,
                    provider_errors=provider_errors,
                )

            except Exception as e:
                error_msg = str(e)
                provider_errors[current_provider] = error_msg
                logger.warning(
                    f"⚠️ Provider {current_provider} failed: {error_msg[:200]}"
                )
                
                # Проверяем, стоит ли пробовать следующий провайдер
                if not _is_retryable_error(e):
                    # Non-retryable ошибка — прерываем цепочку
                    raise ProviderManagerError(
                        f"Провайдер {current_provider} вернул критическую ошибку: {error_msg}"
                    ) from e
                
                # Если это последний провайдер — пробрасываем исключение
                if attempt_idx == len(unique_chain) - 1:
                    break
                
                # Небольшая задержка перед fallback
                await asyncio.sleep(0.5)

        # Все провайдеры упали
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
        Streaming с поддержкой fallback.
        
        Для streaming fallback применяется только если первый провайдер
        не смог начать стриминг (ошибка соединения), но не в середине потока.
        """
        if provider:
            chain = FALLBACK_ORDER.get(provider, [provider])
        else:
            chain = DEFAULT_FALLBACK_CHAIN.copy()

        current_provider = chain[0]
        current_key = api_key
        
        if current_provider == "gigachat" and not current_key:
            current_key = self._get_gigachat_key()
        
        if not current_key:
            # Fallback на второй в цепочке
            if len(chain) > 1:
                current_provider = chain[1]
                if current_provider == "gigachat":
                    current_key = self._get_gigachat_key()
                logger.info(f"↪️ Stream fallback: {chain[0]} → {current_provider}")
        
        if not current_key:
            raise ProviderManagerError("API ключ не настроен ни для одного провайдера")

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
        except Exception as e:
            # Если первый провайдер упал до начала стрима — пробуем fallback
            if len(chain) > 1 and chain[0] == current_provider:
                fallback_provider = chain[1]
                fallback_key = self._get_gigachat_key() if fallback_provider == "gigachat" else api_key
                
                if fallback_key:
                    logger.info(f"↪️ Stream fallback after error: {current_provider} → {fallback_provider}")
                    async for chunk in self._llm.generate_stream(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        api_key=fallback_key,
                        model=model,
                        provider=fallback_provider,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs,
                    ):
                        yield chunk
                    return
            
            raise

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
        import os
        
        gigachat_key = bool(os.getenv("GIGACHAT_AUTH_KEY", "").strip())
        
        return [
            {
                "id": "openrouter",
                "name": "OpenRouter",
                "has_key": False,  # Ключ пользовательский
                "is_system": False,
                "fallback_to": "gigachat",
            },
            {
                "id": "gigachat",
                "name": "GigaChat",
                "has_key": gigachat_key,
                "is_system": gigachat_key,
                "fallback_to": None,
            },
        ]

    async def close(self) -> None:
        """Закрывает сессию"""
        await self._llm.close_session()

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