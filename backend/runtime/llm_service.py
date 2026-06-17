"""
LLM Service — HTTP-провайдеры OpenRouter, GigaChat и HuggingFace.

Поддерживает:
- OpenRouter (OpenAI-совместимый API)
- GigaChat
- HuggingFace Inference API
"""

from typing import Optional, Dict, Any, List, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
import os
import asyncio
import logging

import httpx

from adapters.gigachat_client import get_gigachat_client

logger = logging.getLogger("padplus.llm")


@dataclass
class LLMResponse:
    """Ответ от LLM"""
    text: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    confidence: float = 0.7
    cached: bool = False
    provider_name: str = ""
    style: str = "default"

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "model": self.model,
            "provider": self.provider,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "confidence": self.confidence,
            "cached": self.cached,
            "provider_name": self.provider_name or self.provider,
            "style": self.style,
        }


async def acompletion(response: Any) -> Any:
    """Универсальный адаптер для ответа от HTTP клиента."""
    try:
        if hasattr(response, "json") and callable(response.json):
            data = response.json()
            if asyncio.iscoroutine(data):
                data = await data
            return data
    except Exception as e:
        logger.warning(f"{__name__} error: {e}")
    return response


def _object_to_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return dict(obj)
    try:
        if hasattr(obj, "items") and callable(obj.items):
            return dict(obj.items())
    except Exception as e:
        logger.warning(f"{__name__} error: {e}")
    result: Dict[str, Any] = {}
    for attr in dir(obj):
        if attr.startswith("_"):
            continue
        try:
            value = getattr(obj, attr)
        except Exception:
            continue
        if callable(value):
            continue
        result[attr] = value
    return result


OPENROUTER_BASE = "https://openrouter.ai/api/v1"

DEFAULT_MODELS = {
    "gigachat": "GigaChat",
    "openrouter": "gpt-4o-mini",
    "openrouter_free": "meta-llama/llama-3.1-8b-instruct:free",
    "openai": "gpt-4o-mini",
    "google": "gemini-2.0-flash",
    "anthropic": "claude-3-5-haiku-20241022",
    "groq": "llama-3.1-70b-versatile",
    "deepseek": "deepseek-chat",
    "mistral": "mistral-large-latest",
    "cohere": "command-r",
    "xai": "grok-2",
    "huggingface": "microsoft/phi-3-mini-4k-instruct",
}

# Бесплатные модели OpenRouter
OPENROUTER_FREE_MODELS = [
    "microsoft/phi-3-mini-4k-instruct:free",
    "google/gemma-2b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "huggingfaceh4/zephyr-7b-beta:free",
]


class LLMService:
    """HTTP-сервис для основных провайдеров LLM (OpenRouter, GigaChat, HuggingFace)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, timeout: Optional[int] = None):
        self.default_api_key = api_key
        self.default_model = model
        self._timeout = timeout or int(os.getenv("LLM_TIMEOUT", "30"))
        self._verify_tls = os.getenv("LLM_VERIFY_TLS", "true").strip().lower() not in ("0", "false", "no")
        self._session = httpx.AsyncClient(timeout=self._timeout, verify=self._verify_tls)

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
    ) -> LLMResponse:
        """
        Отправляет запрос к указанному провайдеру.
        
        ProviderManager отвечает за выбор провайдера и fallback.
        LLMService только маршрутизирует к конкретному HTTP-провайдеру.
        """
        key = api_key or self.default_api_key
        model_name = model or self.default_model
        if not key:
            raise ValueError("API ключ не настроен.")

        if provider == "gigachat":
            return await self._generate_gigachat(
                prompt=prompt,
                system_prompt=system_prompt,
                api_key=key,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        return await self._generate_openrouter(
            prompt=prompt,
            system_prompt=system_prompt,
            api_key=key,
            model=model_name,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def _generate_openrouter(
        self,
        prompt: str,
        system_prompt: str = "",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        base_url = OPENROUTER_BASE
        if provider and provider != "openrouter":
            base_url = OPENROUTER_BASE

        # OpenRouter не добавляет openrouter/ к имени модели — он принимает
        # либо полный ID (openai/gpt-4o-mini), либо короткое имя (gpt-4o-mini)
        if provider == "openrouter":
            if model and "/" in model:
                if model.startswith("openrouter/"):
                    model = model[len("openrouter/"):]
                full_model = model
            elif model:
                full_model = model
            elif DEFAULT_MODELS.get("openrouter"):
                full_model = DEFAULT_MODELS["openrouter"]
            else:
                full_model = "gpt-4o-mini"
        else:
            if model and "/" not in model and provider:
                full_model = f"{provider}/{model}"
            elif not model:
                model_for_provider = DEFAULT_MODELS.get(provider) if provider else None
                full_model = model_for_provider or DEFAULT_MODELS.get("openrouter", "gpt-4o-mini")
            else:
                full_model = model or DEFAULT_MODELS.get("openrouter", "gpt-4o-mini")

        if full_model:
            if ":free" not in full_model and os.getenv("USE_FREE_MODELS", "false").lower() == "true":
                full_model = OPENROUTER_FREE_MODELS[0]
                logger.info(f"Using free OpenRouter model: {full_model}")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": full_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("FRONTEND_URL", "http://localhost:5174"),
            "X-Title": "PAD+ AI",
        }

        response = await self._session.post(
            f"{base_url}/chat/completions",
            json=body,
            headers=headers,
            timeout=self._timeout,
        )

        status_code = getattr(response, "status_code", None)
        if isinstance(status_code, int) and status_code != 200:
            raw = str(getattr(response, "text", ""))[:500]
            error_text = raw.encode("ascii", errors="replace").decode("ascii")
            logger.error(f"❌ HTTP error {status_code}: {error_text}")
            raise ValueError(f"Ошибка API: {status_code} - {error_text}")

        data = await acompletion(response)
        if isinstance(data, dict):
            choice = data["choices"][0]
            text = choice.get("message", {}).get("content", "") or choice.get("text", "") or ""
            usage = _object_to_dict(data.get("usage", {}) or {})
            model_name = data.get("model", full_model)
        else:
            choice = getattr(data, "choices", [None])[0]
            msg = getattr(choice, "message", None)
            text = getattr(msg, "content", "") if msg is not None else getattr(choice, "content", "")
            usage = _object_to_dict(getattr(data, "usage", {}) or {})
            model_name = getattr(data, "model", full_model)

        return LLMResponse(
            text=text,
            model=model_name,
            provider=provider or "openrouter",
            usage=usage,
            finish_reason=(choice.get("finish_reason") if isinstance(choice, dict) else getattr(choice, "finish_reason", None)),
            metadata={"raw_response": data},
        )

    async def _generate_gigachat(
        self,
        prompt: str,
        system_prompt: str = "",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        model_name = self._resolve_gigachat_model(model or "GigaChat")
        logger.info(f"GigaChat call: model={model_name}, prompt_len={len(prompt)}")

        client = get_gigachat_client()
        result = await client.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            api_key=api_key,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return LLMResponse(
            text=result["text"],
            model=result["model"],
            provider=result["provider"],
            usage=result["usage"],
            finish_reason=result.get("finish_reason"),
            metadata={"raw_response": result.get("raw_response", {})},
        )

    def _resolve_gigachat_model(self, model_name: str) -> str:
        """
        Определяет корректное имя модели GigaChat.

        Args:
            model_name: Исходное имя модели (может быть с префиксом провайдера)

        Returns:
            Корректное имя модели для GigaChat API
        """
        if "/" in model_name:
            model_name = model_name.split("/")[-1]

        name_lower = model_name.lower()

        if "pro" in name_lower and "plus" not in name_lower:
            return "GigaChat-Pro"
        elif "plus" in name_lower:
            return "GigaChat-Plus"
        elif "lite" in name_lower or "2" in name_lower or "latest" in name_lower:
            return "GigaChat"
        else:
            # По умолчанию — GigaChat (базовая модель)
            return "GigaChat"

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
        Генерирует ответ в режиме streaming (SSE).

        Для OpenRouter использует SSE API (streaming через chunks).
        Для GigaChat использует SSE API GigaChat.
        Для остальных провайдеров возвращает полный ответ.

        Args:
            prompt: Текст запроса
            system_prompt: Системный промпт
            api_key: API ключ
            model: Модель
            provider: Провайдер
            temperature: Температура
            max_tokens: Максимум токенов

        Yields:
            Строки с чанками ответа
        """
        if provider == "gigachat":
            async for chunk in self._stream_gigachat(
                prompt=prompt,
                system_prompt=system_prompt,
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield chunk
        else:
            async for chunk in self._stream_openrouter(
                prompt=prompt,
                system_prompt=system_prompt,
                api_key=api_key,
                model=model,
                provider=provider,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield chunk

    async def _stream_openrouter(
        self,
        prompt: str,
        system_prompt: str = "",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming для OpenRouter (SSE через OpenAI-совместимый API)."""
        import json as json_module

        key = api_key or self.default_api_key
        if not key:
            raise ValueError("API ключ не настроен.")

        base_url = OPENROUTER_BASE
        if provider == "openrouter":
            if model and "/" in model:
                if model.startswith("openrouter/"):
                    model = model[len("openrouter/"):]
                full_model = model
            elif model:
                full_model = model
            elif DEFAULT_MODELS.get("openrouter"):
                full_model = DEFAULT_MODELS["openrouter"]
            else:
                full_model = "gpt-4o-mini"
        else:
            if model and "/" not in model and provider:
                full_model = f"{provider}/{model}"
            elif not model:
                model_for_provider = DEFAULT_MODELS.get(provider) if provider else None
                full_model = model_for_provider or DEFAULT_MODELS.get("openrouter", "gpt-4o-mini")
            else:
                full_model = model or DEFAULT_MODELS.get("openrouter", "gpt-4o-mini")

        if full_model and ":free" not in full_model and os.getenv("USE_FREE_MODELS", "false").lower() == "true":
            full_model = OPENROUTER_FREE_MODELS[0]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": full_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("FRONTEND_URL", "http://localhost:5174"),
            "X-Title": "PAD+ AI",
        }

        try:
            async with self._session.stream(
                "POST",
                f"{base_url}/chat/completions",
                json=body,
                headers=headers,
                timeout=self._timeout,
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    error_text = error_body.decode("utf-8", errors="replace")[:500]
                    raise ValueError(f"Ошибка API: {response.status_code} - {error_text}")

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_data = json_module.loads(data_str)
                            delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json_module.JSONDecodeError:
                            continue
        except httpx.TimeoutException:
            raise ValueError("OpenRouter timeout: сервер не отвечает. Попробуйте позже.")

    async def _stream_gigachat(
        self,
        prompt: str,
        system_prompt: str = "",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        model_name = self._resolve_gigachat_model(model or "GigaChat")
        logger.info(f"GigaChat streaming: model={model_name}")

        key = api_key or self.default_api_key
        if not key:
            raise ValueError("API ключ не настроен.")

        client = get_gigachat_client()
        async for chunk in client.stream(
            prompt=prompt,
            system_prompt=system_prompt,
            api_key=key,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk

    async def test_connection(self, api_key: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        try:
            response = await self.generate(
                prompt="Привет! Ответь кратко одним словом.",
                api_key=api_key,
                model=model,
                max_tokens=10,
            )
            return {
                "success": True,
                "message": "Подключение успешно",
                "model": response.model,
                "provider": response.provider,
                "response": response.text[:50] + "..." if len(response.text) > 50 else response.text,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_available_models(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._get_fallback_models(provider)

    def _get_fallback_models(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        fallback_models = {
            "openrouter": [
                {"id": "openrouter/auto", "name": "Auto (OpenRouter)", "max_tokens": 128000, "supports_vision": True, "cost": "paid"},
                {"id": "openrouter/gpt-4o-mini", "name": "GPT-4o Mini (OpenRouter)", "max_tokens": 128000, "supports_vision": True, "cost": "paid"},
                {"id": "openrouter/meta-llama/llama-3.1-8b-instruct:free", "name": "Llama 3.1 8B (FREE)", "max_tokens": 8192, "supports_vision": False, "cost": "free"},
                {"id": "openrouter/microsoft/phi-3-mini-4k-instruct:free", "name": "Phi-3 Mini (FREE)", "max_tokens": 4096, "supports_vision": False, "cost": "free"},
            ],
            "gigachat": [
                {"id": "GigaChat", "name": "GigaChat", "max_tokens": 4096, "supports_vision": False},
                {"id": "GigaChat-Pro", "name": "GigaChat Pro", "max_tokens": 8192, "supports_vision": False},
                {"id": "GigaChat-Plus", "name": "GigaChat Plus", "max_tokens": 8192, "supports_vision": False},
            ],
        }
        models: List[Dict[str, Any]] = []
        if provider and provider in fallback_models:
            for m in fallback_models[provider]:
                models.append({**m, "provider": provider, "supports_function_calling": True, "cost": "unknown"})
        elif not provider:
            for prov, prov_models in fallback_models.items():
                for m in prov_models:
                    models.append({**m, "provider": prov, "supports_function_calling": True, "cost": "unknown"})
        return models

    async def close_session(self) -> None:
        if hasattr(self, "_session") and self._session is not None:
            try:
                await self._session.aclose()
            except Exception as e:
                logger.warning(f"Error closing session: {e}")


_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _service
    if _service is None:
        _service = LLMService()
    return _service

