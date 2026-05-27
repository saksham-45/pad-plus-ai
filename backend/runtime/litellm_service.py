"""
LiteLLM Service — Сервис для работы с LLM через прямые HTTP запросы

Поддерживает:
- OpenRouter (OpenAI-совместимый API) — через прямой HTTP
- GigaChat — через прямой HTTP
"""

from typing import Optional, Dict, Any, List, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
import os
import asyncio
import logging
import json

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
    
    # Для совместимости со старой системой
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
            "style": self.style
        }


# Базовая OpenAI-совместимая модель для OpenRouter
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
GIGACHAT_AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

# Модели по умолчанию для каждого провайдера
DEFAULT_MODELS = {
    "gigachat": "GigaChat",
    "openrouter": "gpt-4o-mini",
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


class LiteLLMService:
    """
    Сервис для работы с LLM через прямые HTTP запросы.
    Без зависимостей от litellm или openai SDK.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        self.default_api_key = api_key
        self.default_model = model
        self._timeout = timeout or int(os.getenv("LLM_TIMEOUT", "60"))
        self._http_client = httpx.AsyncClient(timeout=self._timeout, verify=False)

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
        **kwargs
    ) -> LLMResponse:
        """Генерирует ответ от LLM через прямой HTTP запрос"""
        key = api_key or self.default_api_key
        model_name = model or self.default_model

        if not key:
            raise ValueError("API ключ не настроен.")

        # GigaChat — прямой вызов
        if provider == "gigachat":
            return await self._generate_gigachat(
                prompt=prompt,
                system_prompt=system_prompt,
                api_key=key,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # HuggingFace Inference API
        if provider == "huggingface":
            return await self._generate_huggingface(
                prompt=prompt,
                system_prompt=system_prompt,
                api_key=key,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # OpenRouter / OpenAI-совместимые — прямой HTTP запрос
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
        """Прямой HTTP вызов OpenRouter / OpenAI-совместимых API"""
        # Определяем базовый URL
        if provider == "openrouter":
            base_url = OPENROUTER_BASE
        else:
            # Для других OpenAI-совместимых провайдеров (openai, google через OpenRouter и т.д.)
            # По умолчанию используем OpenRouter как роутер
            base_url = OPENROUTER_BASE

        # Формируем полное имя модели
        if model and "/" not in model and provider:
            full_model = f"{provider}/{model}"
        else:
            full_model = model or DEFAULT_MODELS.get(provider, "gpt-4o-mini")

        # Собираем сообщения
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Формируем тело запроса
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

        logger.info(f"🔌 HTTP request: provider={provider}, model={full_model}")

        try:
            response = await self._http_client.post(
                f"{base_url}/chat/completions",
                json=body,
                headers=headers,
            )

            if response.status_code != 200:
                error_text = response.text[:500]
                logger.error(f"❌ HTTP error {response.status_code}: {error_text}")
                raise ValueError(f"Ошибка API: {response.status_code} - {error_text}")

            data = response.json()

            # Извлекаем ответ
            choice = data["choices"][0]
            text = choice["message"]["content"] or ""

            # Извлекаем usage если есть
            usage = {}
            if "usage" in data:
                usage = {
                    "prompt_tokens": data["usage"].get("prompt_tokens", 0),
                    "completion_tokens": data["usage"].get("completion_tokens", 0),
                    "total_tokens": data["usage"].get("total_tokens", 0),
                }

            logger.info(f"✅ Response: model={data.get('model', full_model)}, tokens={usage.get('total_tokens', '?')}")

            return LLMResponse(
                text=text,
                model=data.get("model", full_model),
                provider=provider or "openrouter",
                usage=usage,
                finish_reason=choice.get("finish_reason"),
                metadata={"raw_response": data},
            )

        except httpx.TimeoutException:
            raise ValueError(f"Превышен timeout ({self._timeout}с) для запроса к {full_model}")
        except httpx.RequestError as e:
            raise ValueError(f"Ошибка подключения: {str(e)}")

    async def _generate_huggingface(
        self,
        prompt: str,
        system_prompt: str = "",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Прямой вызов HuggingFace Inference API"""
        model_name = model or DEFAULT_MODELS.get("huggingface", "microsoft/phi-3-mini-4k-instruct")
        # Убираем префикс провайдера если есть
        if "/" in model_name and not model_name.startswith(("microsoft/", "google/", "meta-", "mistralai/", "HuggingFaceH4/")):
            model_name = model_name.split("/", 1)[-1]
        if model_name.startswith("huggingface/"):
            model_name = model_name.split("/", 1)[-1]

        logger.info(f"🔌 HuggingFace call: model={model_name}")

        # HuggingFace использует отдельный URL для каждой модели
        api_url = f"https://api-inference.huggingface.co/models/{model_name}"

        # Формируем промпт с системным сообщением
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        body = {
            "inputs": full_prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens or 500,
                "return_full_text": False,
            }
        }

        try:
            response = await self._http_client.post(
                api_url,
                json=body,
                headers=headers,
            )

            if response.status_code != 200:
                error_text = response.text[:500]
                logger.error(f"❌ HuggingFace error {response.status_code}: {error_text}")
                raise ValueError(f"Ошибка HuggingFace API: {response.status_code} - {error_text}")

            data = response.json()

            # HuggingFace возвращает список: [{"generated_text": "..."}]
            if isinstance(data, list) and len(data) > 0:
                text = data[0].get("generated_text", "")
            elif isinstance(data, dict) and "generated_text" in data:
                text = data["generated_text"]
            else:
                text = str(data)

            logger.info(f"✅ HuggingFace response: model={model_name}, len={len(text)} chars")

            return LLMResponse(
                text=text.strip(),
                model=model_name,
                provider="huggingface",
                usage={"total_tokens": len(text) // 4},
                finish_reason="stop",
                metadata={"raw_response": data},
            )

        except httpx.TimeoutException:
            raise ValueError(f"Превышен timeout ({self._timeout}с) для запроса к {model_name}")
        except httpx.RequestError as e:
            raise ValueError(f"Ошибка подключения к HuggingFace: {str(e)}")

    async def _generate_gigachat(
        self,
        prompt: str,
        system_prompt: str = "",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Прямой вызов GigaChat через HTTP"""
        model_name = model or "GigaChat"
        logger.info(f"🔌 GigaChat call: model={model_name}, api_key_len={len(api_key) if api_key else 0}")

        # Убираем префикс провайдера
        if "/" in model_name:
            model_name = model_name.split("/")[-1]

        # Приводим к корректным названиям GigaChat API
        model_lower = model_name.lower()
        if "pro" in model_lower and "plus" not in model_lower:
            model_name = "GigaChat-Pro"
        elif "plus" in model_lower:
            model_name = "GigaChat-Plus"
        elif "lite" in model_lower or "2" in model_lower:
            model_name = "GigaChat"
        else:
            model_name = "GigaChat"

        # Обработка ключа
        if api_key and ':' in api_key:
            parts = api_key.split(':', 1)
            secret = parts[1].replace('\n', '').replace('\r', '').replace(' ', '')
            if len(secret) > 80:
                api_key = secret
            else:
                import base64
                api_key = base64.b64encode(api_key.encode()).decode()

        # Шаг 1: Получаем токен
        def _get_token():
            import requests as _req
            import uuid as _uuid
            return _req.post(
                GIGACHAT_AUTH_URL,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "RqUID": str(_uuid.uuid4()),
                    "Authorization": f"Basic {api_key}",
                },
                data={"scope": "GIGACHAT_API_PERS"},
                timeout=10,
                verify=False,
            )

        token_resp = await asyncio.to_thread(_get_token)
        if token_resp.status_code != 200:
            raise ValueError(f"GigaChat auth failed: {token_resp.status_code} {token_resp.text}")

        access_token = token_resp.json()["access_token"]

        # Шаг 2: Отправляем запрос
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        def _send_chat():
            import requests as _req
            return _req.post(
                GIGACHAT_API_URL,
                json={
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature,
                    **({"max_tokens": max_tokens} if max_tokens else {}),
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                timeout=60,
                verify=False,
            )

        chat_resp = await asyncio.to_thread(_send_chat)
        if chat_resp.status_code != 200:
            raise ValueError(f"GigaChat API error: {chat_resp.text}")

        data = chat_resp.json()
        text = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage", {})

        return LLMResponse(
            text=text,
            model=model_name,
            provider="gigachat",
            usage=usage,
            finish_reason=data["choices"][0].get("finish_reason"),
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
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Потоковый ответ — пока не реализован, возвращаем полный ответ"""
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

    async def test_connection(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Тестирует подключение к провайдеру"""
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

    def get_available_models(self, provider: str = None) -> List[Dict[str, Any]]:
        """Возвращает список доступных моделей (статический fallback)"""
        return self._get_fallback_models(provider)

    def _get_fallback_models(self, provider: str = None) -> List[Dict[str, Any]]:
        """Статический список популярных моделей"""
        fallback_models = {
            "openai": [
                {"id": "openai/gpt-4o", "name": "GPT-4o", "max_tokens": 128000, "supports_vision": True},
                {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "max_tokens": 128000, "supports_vision": True},
                {"id": "openai/gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "max_tokens": 16385, "supports_vision": False},
            ],
            "google": [
                {"id": "google/gemini-2.0-flash", "name": "Gemini 2.0 Flash", "max_tokens": 1048576, "supports_vision": True},
                {"id": "google/gemini-1.5-pro", "name": "Gemini 1.5 Pro", "max_tokens": 2097152, "supports_vision": True},
                {"id": "google/gemini-1.5-flash", "name": "Gemini 1.5 Flash", "max_tokens": 1048576, "supports_vision": True},
            ],
            "anthropic": [
                {"id": "anthropic/claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "max_tokens": 200000, "supports_vision": True},
                {"id": "anthropic/claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "max_tokens": 200000, "supports_vision": True},
            ],
            "groq": [
                {"id": "groq/llama-3.3-70b-versatile", "name": "Llama 3.3 70B", "max_tokens": 131072, "supports_vision": False},
                {"id": "groq/llama-3.1-70b-versatile", "name": "Llama 3.1 70B", "max_tokens": 131072, "supports_vision": False},
                {"id": "groq/llama-3.1-8b-instant", "name": "Llama 3.1 8B", "max_tokens": 131072, "supports_vision": False},
                {"id": "groq/gemma2-9b-it", "name": "Gemma2 9B", "max_tokens": 8192, "supports_vision": False},
            ],
            "deepseek": [
                {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat", "max_tokens": 128000, "supports_vision": False},
                {"id": "deepseek/deepseek-coder", "name": "DeepSeek Coder", "max_tokens": 128000, "supports_vision": False},
            ],
            "openrouter": [
                {"id": "openrouter/auto", "name": "Auto (OpenRouter)", "max_tokens": 128000, "supports_vision": True},
                {"id": "openrouter/gpt-4o-mini", "name": "GPT-4o Mini (OpenRouter)", "max_tokens": 128000, "supports_vision": True},
            ],
            "gigachat": [
                {"id": "GigaChat", "name": "GigaChat", "max_tokens": 4096, "supports_vision": False},
                {"id": "GigaChat-Pro", "name": "GigaChat Pro", "max_tokens": 8192, "supports_vision": False},
                {"id": "GigaChat-Plus", "name": "GigaChat Plus", "max_tokens": 8192, "supports_vision": False},
            ],
        }

        models = []
        if provider and provider in fallback_models:
            for m in fallback_models[provider]:
                models.append({**m, "provider": provider, "supports_function_calling": True, "cost": "unknown"})
        elif not provider:
            for prov, prov_models in fallback_models.items():
                for m in prov_models:
                    models.append({**m, "provider": prov, "supports_function_calling": True, "cost": "unknown"})
        return models

    async def close_session(self):
        """Закрывает HTTP клиент"""
        if self._http_client:
            await self._http_client.aclose()
            logger.info("✅ HTTP client closed")


# Глобальный экземпляр
_litellm_service: Optional[LiteLLMService] = None


def get_litellm_service() -> LiteLLMService:
    """Возвращает глобальный сервис LiteLLM"""
    global _litellm_service
    if _litellm_service is None:
        _litellm_service = LiteLLMService()
    return _litellm_service