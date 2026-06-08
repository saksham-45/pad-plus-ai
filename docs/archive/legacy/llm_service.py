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

logger = logging.getLogger("padplus.litellm")


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
    except Exception:
        pass
    return response


def _object_to_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return dict(obj)
    try:
        if hasattr(obj, "items") and callable(obj.items):
            return dict(obj.items())
    except Exception:
        pass
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
GIGACHAT_AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

DEFAULT_MODELS = {
    "gigachat": "GigaChat",
    "openrouter": "gpt-4o-mini",
    "openrouter_free": "meta-llama/llama-3.1-8b-instruct:free",  # Бесплатная модель
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
    "meta-llama/llama-3.1-8b-instruct:free",
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

        if model and "/" not in model and provider:
            full_model = f"{provider}/{model}"
        else:
            full_model = model or DEFAULT_MODELS.get(provider, "gpt-4o-mini")

        # Если модель не содержит ":free", но пользователь хочет бесплатные модели
        if ":free" not in full_model and os.getenv("USE_FREE_MODELS", "false").lower() == "true":
            full_model = OPENROUTER_FREE_MODELS[0]
            logger.info(f"🆓 Using free OpenRouter model: {full_model}")

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
            error_text = str(getattr(response, "text", ""))[:500]
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
        model_name = model or "GigaChat"
        logger.info(f"🔌 GigaChat call: model={model_name}, api_key_len={len(api_key) if api_key else 0}")

        if "/" in model_name:
            model_name = model_name.split("/")[-1]

        model_lower = model_name.lower()
        if "pro" in model_lower and "plus" not in model_lower:
            model_name = "GigaChat-Pro"
        elif "plus" in model_lower:
            model_name = "GigaChat-Plus"
        elif "lite" in model_lower or "2" in model_lower:
            model_name = "GigaChat"
        else:
            model_name = "GigaChat"

        if api_key and ":" in api_key:
            parts = api_key.split(":", 1)
            secret = parts[1].replace("\n", "").replace("\r", "").replace(" ", "")
            if len(secret) > 80:
                api_key = secret
            else:
                import base64
                api_key = base64.b64encode(api_key.encode()).decode()

        auth_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(os.urandom(16).hex()),
            "Authorization": f"Basic {api_key}",
        }

        # Для GigaChat отключаем проверку SSL (самоподписанный сертификат Сбера)
        gigachat_verify_tls = os.getenv("GIGACHAT_VERIFY_TLS", "false").strip().lower() not in ("0", "false", "no")
        
        logger.info(f"🔒 GigaChat SSL verification: {gigachat_verify_tls}")
        
        async with httpx.AsyncClient(timeout=10, verify=gigachat_verify_tls) as client:
            token_resp = await client.post(GIGACHAT_AUTH_URL, headers=auth_headers, data={"scope": "GIGACHAT_API_PERS"})
        if token_resp.status_code != 200:
            raise ValueError(f"GigaChat auth failed: {token_resp.status_code} {token_resp.text}")

        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise ValueError("GigaChat auth did not return access_token")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        chat_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        chat_body = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            chat_body["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=60, verify=gigachat_verify_tls) as client:
            chat_resp = await client.post(GIGACHAT_API_URL, json=chat_body, headers=chat_headers)

        if chat_resp.status_code != 200:
            raise ValueError(f"GigaChat API error: {chat_resp.text}")

        data = chat_resp.json()
        choice = data.get("choices", [])[0] if data.get("choices") else {}
        text = choice.get("message", {}).get("content", "") or ""
        usage = data.get("usage", {}) or {}

        return LLMResponse(
            text=text,
            model=model_name,
            provider="gigachat",
            usage=usage,
            finish_reason=choice.get("finish_reason"),
            metadata={"raw_response": data},
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
        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            api_key=api_key,
            model=model,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        yield response.text

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


# Алиас для обратной совместимости
get_litellm_service = get_llm_service
