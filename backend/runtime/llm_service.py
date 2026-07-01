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
import json
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
        safe = str(e).encode("ascii", errors="replace").decode("ascii")
        logger.warning(f"{__name__} error: {safe}")
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
        # "auto" → используем модель по умолчанию
        if model in ("auto", f"{provider}/auto"):
            model = None

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

        # Очищаем ключ от не-ASCII символов (например неразрывный пробел \xa0)
        clean_key = api_key.strip().encode("ascii", errors="ignore").decode("ascii")
        headers = {
            "Authorization": f"Bearer {clean_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("FRONTEND_URL", "http://localhost:5174"),
            "X-Title": "PAD+ AI",
        }

        try:
            _resp = await self._session.post(
                f"{base_url}/chat/completions",
                json=body,
                headers=headers,
                timeout=self._timeout,
            )
            _status = _resp.status_code
            _raw = await _resp.aread()
        except httpx.TimeoutException as _e:
            raise ValueError(f"OpenRouter timeout: {_e}")
        except Exception as _e:
            _err_str = str(_e)
            raise ValueError(f"OpenRouter HTTP error: {_err_str[:500]}")
        response = _raw
        status_code = _status

        if status_code != 200:
            try:
                raw = response.decode("utf-8", errors="replace")[:500]
            except Exception:
                raw = ""
            logger.error(f"HTTP error {status_code}: {raw}")
            raise ValueError(f"Ошибка API: {status_code} - {raw}")

        try:
            raw_text = response.decode("utf-8", errors="replace")
        except Exception:
            raise ValueError("OpenRouter: не удалось прочитать тело ответа")
        data = json.loads(raw_text)
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

    async def get_embeddings(
        self,
        texts: List[str],
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
    ) -> List[List[float]]:
        """
        Получает эмбеддинги для списка текстов через OpenRouter embeddings API.

        Args:
            texts: Список текстов для векторизации
            api_key: API ключ OpenRouter
            model: Модель эмбеддингов (по умолчанию text-embedding-3-small)

        Returns:
            Список векторов (каждый вектор — список float)
        """
        key = api_key or self.default_api_key
        if not key:
            raise ValueError("API ключ не настроен для получения эмбеддингов.")

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        body = {
            "model": model,
            "input": texts,
        }

        for attempt in range(3):
            try:
                _resp = await self._session.post(
                    f"{OPENROUTER_BASE}/embeddings",
                    json=body,
                    headers=headers,
                    timeout=self._timeout,
                )
                _status = _resp.status_code
                _raw = await _resp.aread()
            except httpx.TimeoutException:
                if attempt < 2:
                    await asyncio.sleep(1)
                    continue
                raise ValueError(f"OpenRouter embeddings timeout после {attempt+1} попыток")
            except Exception as _e:
                if attempt < 2:
                    await asyncio.sleep(1)
                    continue
                raise ValueError(f"OpenRouter embeddings error: {str(_e)[:500]}")

            if _status != 200:
                raw_text = _raw.decode("utf-8", errors="replace")[:500]
                if attempt < 2:
                    await asyncio.sleep(2)
                    continue
                raise ValueError(f"OpenRouter embeddings HTTP {_status}: {raw_text}")

            try:
                data = json.loads(_raw.decode("utf-8", errors="replace"))
            except Exception as _e:
                raise ValueError(f"OpenRouter embeddings: не удалось прочитать ответ: {_e}")

            embeddings = []
            for item in data.get("data", []):
                embeddings.append(item.get("embedding", []))
            return embeddings

        raise ValueError("OpenRouter embeddings: все попытки исчерпаны")

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
        if model in ("auto", f"{provider}/auto"):
            model = None

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
                                content = content.encode("ascii", errors="replace").decode("ascii")
                                yield content
                        except json_module.JSONDecodeError:
                            continue
        except httpx.TimeoutException:
            raise ValueError("OpenRouter timeout: сервер не отвечает. Попробуйте позже.")
        except Exception as e:
            raise ValueError(f"OpenRouter stream error: {e}") from e

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

    async def fetch_openrouter_models(self) -> List[Dict[str, Any]]:
        """Загружает актуальный список моделей из OpenRouter API."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get("https://openrouter.ai/api/v1/models")
                if resp.status_code != 200:
                    logger.warning(f"OpenRouter models API: HTTP {resp.status_code}")
                    return []
                data = resp.json()
                raw_models = data.get("data", [])
        except Exception as e:
            logger.warning(f"Failed to fetch OpenRouter models: {e}")
            return []

        result = []
        for m in raw_models:
            mid = m.get("id", "")
            if not mid:
                continue
            pricing = m.get("pricing", {}) or {}
            p_prompt = pricing.get("prompt", "0")
            is_free = p_prompt == "0" or p_prompt is None
            cost = "free" if is_free else "paid"
            ctx = m.get("context_length", 4096) or 4096
            caps = m.get("capabilities", {}) or {}
            supports_vision = bool(caps.get("vision", False))
            result.append({
                "id": f"openrouter/{mid}",
                "name": m.get("name", mid),
                "max_tokens": ctx,
                "supports_vision": supports_vision,
                "cost": cost,
                "provider": "openrouter",
                "supports_function_calling": True,
            })
        return result

    def get_available_models(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._get_fallback_models(provider)

    def _get_fallback_models(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        fallback_models = {
            "openrouter": [
                {"id": "openrouter/auto", "name": "Auto (OpenRouter)", "max_tokens": 128000, "supports_vision": True, "cost": "paid"},
                {"id": "openrouter/openai/gpt-4o-mini", "name": "GPT-4o Mini", "max_tokens": 128000, "supports_vision": True, "cost": "paid"},
                {"id": "openrouter/openai/gpt-4o", "name": "GPT-4o", "max_tokens": 128000, "supports_vision": True, "cost": "paid"},
                {"id": "openrouter/anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "max_tokens": 200000, "supports_vision": True, "cost": "paid"},
                {"id": "openrouter/google/gemini-2.0-flash", "name": "Gemini 2.0 Flash", "max_tokens": 1048576, "supports_vision": True, "cost": "paid"},
                {"id": "openrouter/deepseek/deepseek-chat", "name": "DeepSeek Chat", "max_tokens": 32768, "supports_vision": False, "cost": "paid"},
                {"id": "openrouter/meta-llama/llama-3.1-8b-instruct:free", "name": "Llama 3.1 8B (FREE)", "max_tokens": 8192, "supports_vision": False, "cost": "free"},
                {"id": "openrouter/microsoft/phi-3-mini-4k-instruct:free", "name": "Phi-3 Mini (FREE)", "max_tokens": 4096, "supports_vision": False, "cost": "free"},
                {"id": "openrouter/google/gemma-4-31b-it:free", "name": "Gemma 4 31B (FREE)", "max_tokens": 262144, "supports_vision": False, "cost": "free"},
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

