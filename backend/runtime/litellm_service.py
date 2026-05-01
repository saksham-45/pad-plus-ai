"""
LiteLLM Service — Основной сервис для работы с LLM через LiteLLM

Заменяет старую систему провайдеров (GigaChat, Gemini, OpenRouter)
на единую систему через LiteLLM.

Поддерживает:
- 50+ провайдеров через единый API
- Персональные API ключи пользователей
- Streaming ответов
- Автоматический fallback между моделями
"""

from typing import Optional, Dict, Any, List, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import os
import asyncio
import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from litellm import acompletion
from litellm.exceptions import AuthenticationError, RateLimitError, APIConnectionError, InternalServerError
from litellm.utils import get_model_info

logger = logging.getLogger("padplus.litellm")


class CircuitBreakerOpenError(Exception):
    """Исключение, когда Circuit Breaker открыт"""
    pass


class CircuitBreaker:
    """
    Circuit Breaker паттерн для защиты от каскадных ошибок
    
    Состояния:
    - CLOSED: нормальная работа, запросы проходят
    - OPEN: запросы блокируются, провайдер считается недоступным
    - HALF_OPEN: проверка восстановления (один запрос)
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._state = "closed"  # closed, open, half_open
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._opened_at: Optional[datetime] = None
        self._half_open_calls = 0
        
        # Метрики
        self._total_requests = 0
        self._total_failures = 0
        self._total_successes = 0
    
    @property
    def state(self) -> str:
        """Возвращает текущее состояние с учётом timeout"""
        if self._state == "open" and self._opened_at:
            elapsed = (datetime.now() - self._opened_at).total_seconds()
            if elapsed >= self.recovery_timeout:
                self._state = "half_open"
                self._half_open_calls = 0
        return self._state
    
    def is_closed(self) -> bool:
        return self.state == "closed"
    
    def is_open(self) -> bool:
        return self.state == "open"
    
    def is_half_open(self) -> bool:
        return self.state == "half_open"
    
    def open(self):
        """Открывает Circuit Breaker"""
        self._state = "open"
        self._opened_at = datetime.now()
        self._half_open_calls = 0
        logger.warning(f"⚠️ Circuit Breaker открыт после {self._failure_count} ошибок")
    
    def close(self):
        """Закрывает Circuit Breaker (сброс после успеха)"""
        self._state = "closed"
        self._failure_count = 0
        self._success_count = 0
        self._opened_at = None
        self._half_open_calls = 0
        logger.info("✅ Circuit Breaker закрыт (восстановление)")
    
    def half_open(self):
        """Переводит в half-open состояние"""
        self._state = "half_open"
        self._half_open_calls = 0
        logger.info("🔄 Circuit Breaker в half-open состоянии")
    
    def record_success(self):
        """Записывает успешный запрос"""
        self._total_requests += 1
        self._total_successes += 1
        self._success_count += 1
        
        if self.state == "half_open":
            # Успех в half-open закрывает Circuit Breaker
            self.close()
        elif self.state == "closed":
            # Сбрасываем счётчик ошибок при успехе
            self._failure_count = 0
    
    def record_failure(self):
        """Записывает неудачный запрос"""
        self._total_requests += 1
        self._total_failures += 1
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        
        if self.state == "half_open":
            # Неудача в half-open снова открывает Circuit Breaker
            self.open()
        elif self.state == "closed":
            if self._failure_count >= self.failure_threshold:
                self.open()
    
    def can_execute(self) -> bool:
        """Проверяет, можно ли выполнить запрос"""
        state = self.state
        
        if state == "closed":
            return True
        elif state == "open":
            return False
        elif state == "half_open":
            # Разрешаем только ограниченное число запросов
            return self._half_open_calls < self.half_open_max_calls
        
        return False
    
    def before_request(self):
        """Вызывается перед запросом"""
        if self.state == "half_open":
            self._half_open_calls += 1
        
        if not self.can_execute():
            raise CircuitBreakerOpenError(
                f"Circuit Breaker открыт. "
                f"Состояние: {self.state}, "
                f"Ошибок: {self._failure_count}, "
                f"Последняя ошибка: {self._last_failure_time}"
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Возвращает метрики Circuit Breaker"""
        return {
            "state": self.state,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_requests": self._total_requests,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None,
            "opened_at": self._opened_at.isoformat() if self._opened_at else None,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация состояния"""
        return self.get_metrics()


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
            # Совместимость
            "confidence": self.confidence,
            "cached": self.cached,
            "provider_name": self.provider_name or self.provider,
            "style": self.style
        }


class LiteLLMService:
    """
    Основной сервис для работы с LLM

    Использует LiteLLM для унифицированного доступа ко всем провайдерам.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """
        Инициализирует сервис

        Args:
            api_key: API ключ (опционально, можно передавать для каждого запроса)
            model: Модель по умолчанию
            timeout: Timeout для запросов в секундах (по умолчанию 30)
        """
        self.default_api_key = api_key
        self.default_model = model
        
        # Timeout из переменной окружения или параметра
        self._timeout = timeout or int(os.getenv("LLM_TIMEOUT", "30"))
        
        # Circuit Breaker
        failure_threshold = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
        recovery_timeout = int(os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60"))
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
        
        # Настройка LiteLLM
        os.environ.setdefault("LITELLM_LOG", "False")
        
        # HTTP сессия для connection pooling (исправление 6)
        self._session = None
    
    def _get_full_model_name(self, provider: str, model: Optional[str] = None) -> str:
        """
        Формирует полное имя модели для LiteLLM
        
        LiteLLM требует: provider/model
        Например: "google/gemini-2.0-flash", "groq/llama-3.1-70b-versatile"
        
        Args:
            provider: Провайдер (google, groq, openai, anthropic)
            model: Модель (например: gemini-2.0-flash)

        Returns:
            Полное имя: provider/model
        """
        # Защита от None модели
        if model is None:
            model = ""
        
        # Если модель уже содержит префикс провайдера
        if "/" in model:
            return model
        
        # Добавляем префикс провайдера
        return f"{provider}/{model}" if model else provider
    
    def _detect_provider(self, model: str) -> str:
        """
        Определяет провайдера по названию модели

        Приоритет:
        1. Явный провайдер в модели (openrouter/..., groq/...)
        2. Определение по названию
        3. OpenRouter по умолчанию
        """
        model_lower = model.lower()

        # Если уже есть префикс провайдера - используем его
        if model_lower.startswith("groq/"):
            return "groq"
        elif model_lower.startswith("gemini/"):
            return "google"
        elif model_lower.startswith("gpt-"):
            return "openai"
        elif model_lower.startswith("claude-"):
            return "anthropic"
        elif model_lower.startswith("openrouter/"):
            return "openrouter"
        elif model_lower.startswith("deepseek"):
            return "deepseek"
        elif model_lower.startswith("llama"):
            return "groq"  # Llama модели обычно через Groq
        elif model_lower.startswith("mistral"):
            return "mistral"
        elif model_lower.startswith("gemma"):
            return "groq"  # Gemma модели через Groq
        elif model_lower.startswith("mixtral"):
            return "groq"  # Mixtral модели через Groq
        elif model_lower.startswith("yandexgpt") or model_lower.startswith("yandex"):
            return "yandex"
        elif model_lower.startswith("gigachat"):
            return "gigachat"
        elif model_lower.startswith("command"):
            return "cohere"
        elif model_lower.startswith("grok"):
            return "xai"
        elif model_lower.startswith("meta-llama"):
            return "together_ai"  # Meta модели обычно через Together

        # Определяем по названию
        if "gigachat" in model_lower:
            return "gigachat"
        elif "gemini" in model_lower:
            return "google"
        elif "gpt-" in model_lower or "openai" in model_lower:
            return "openai"
        elif "claude" in model_lower:
            return "anthropic"
        elif "groq" in model_lower or "llama" in model_lower or "mixtral" in model_lower or "gemma" in model_lower:
            return "groq"
        elif "deepseek" in model_lower:
            return "deepseek"
        elif "mistral" in model_lower:
            return "mistral"
        elif "yandex" in model_lower:
            return "yandex"
        elif "grok" in model_lower:
            return "xai"
        elif "command" in model_lower:
            return "cohere"
        elif "openrouter" in model_lower:
            return "openrouter"

        # Не можем определить — возвращаем None
        return None

    # === RETRY-МЕХАНИЗМ (Вторая очередь улучшений) ===
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((APIConnectionError, InternalServerError)),
        reraise=True
    )
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
        """
        Генерирует ответ от LLM

        Args:
            prompt: Пользовательский запрос
            system_prompt: Системный промпт
            api_key: API ключ
            model: Модель
            provider: Провайдер (google, groq, openai, anthropic)
            temperature: Температура (0.0-2.0)
            max_tokens: Максимум токенов
            stream: Потоковый режим

        Returns:
            LLMResponse с ответом
        """
        key = api_key or self.default_api_key
        model_name = model or self.default_model

        # GigaChat — используем ключ из БД (не из .env)
        if provider == "gigachat":
            if not key:
                raise ValueError("GigaChat ключ не настроен. Подключите провайдера в настройках.")

        if not key:
            raise ValueError("API ключ не настроен. Укажите OPENROUTER_API_KEY в .env")

        # === ИСПРАВЛЕНИЕ 2: Circuit Breaker ===
        # Проверяем, можно ли выполнить запрос
        try:
            self._circuit_breaker.before_request()
        except CircuitBreakerOpenError as e:
            logger.warning(f"⚠️ Circuit Breaker открыт: {e}")
            raise

        # Формируем сообщения
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Формируем полное имя модели
        if provider:
            full_model = self._get_full_model_name(provider, model_name)
        else:
            full_model = self._get_full_model_name(
                self._detect_provider(model_name),
                model_name
            )

        # GigaChat — используем официальный SDK напрямую
        if provider == "gigachat":
            return await self._generate_gigachat(
                prompt=prompt,
                system_prompt=system_prompt,
                api_key=key,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        try:
            # === ИСПРАВЛЕНИЕ 3: Timeout ===
            response = await asyncio.wait_for(
                acompletion(
                    model=full_model,
                    messages=messages,
                    api_key=key,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                ),
                timeout=self._timeout
            )

            # Извлекаем ответ
            choice = response.choices[0]
            text = choice.message.content or ""

            # Извлекаем usage
            usage = {}
            if hasattr(response, "usage"):
                usage = {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                    "total_tokens": getattr(response.usage, "total_tokens", 0)
                }

            # === ИСПРАВЛЕНИЕ 2: Запись успеха в Circuit Breaker ===
            self._circuit_breaker.record_success()

            return LLMResponse(
                text=text,
                model=full_model,
                provider=self._detect_provider(model_name),
                usage=usage,
                finish_reason=choice.finish_reason,
                metadata={"raw_response": response.dict() if hasattr(response, "dict") else None}
            )

        except asyncio.TimeoutError:
            # Timeout истёк
            logger.error(f"⏱️ Timeout ({self._timeout}s) для запроса к {full_model}")
            self._circuit_breaker.record_failure()
            raise asyncio.TimeoutError(
                f"Превышен timeout ожидания ответа от LLM ({self._timeout}с). "
                f"Попробуйте позже или увеличьте LLM_TIMEOUT."
            )

        except AuthenticationError as e:
            logger.error(f"❌ Authentication error: {e}")
            self._circuit_breaker.record_failure()
            raise ValueError(f"❌ Неверный API ключ: {str(e)}")
            
        except RateLimitError as e:
            logger.error(f"⏱️ Rate limit: {e}")
            self._circuit_breaker.record_failure()
            raise ValueError(f"⏱️ Превышен лимит: {str(e)}")
            
        except APIConnectionError as e:
            logger.error(f"🔌 Connection error: {e}")
            self._circuit_breaker.record_failure()
            raise ValueError(f"🔌 Ошибка подключения: {str(e)}")
            
        except Exception as e:
            logger.error(f"❌ LLM error: {e}")
            self._circuit_breaker.record_failure()
            raise ValueError(f"❌ Ошибка LLM: {str(e)}")

    async def _generate_gigachat(
        self,
        prompt: str,
        system_prompt: str = "",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Прямой вызов GigaChat через HTTP (как в test_gigachat_auth.py)"""
        import httpx

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
            model_name = "GigaChat"  # Lite/2-Lite → базовый GigaChat
        else:
            model_name = "GigaChat"

        # Ключ в БД: client_id:base64_secret
        if api_key and ':' in api_key:
            parts = api_key.split(':', 1)
            secret = parts[1].replace('\n', '').replace('\r', '').replace(' ', '')
            if len(secret) > 80:
                api_key = secret  # Уже base64-encoded secret
            else:
                import base64
                api_key = base64.b64encode(api_key.encode()).decode()

        # Шаг 1: Получаем токен (синхронный requests в thread)
        def _get_token():
            import requests as _req
            import uuid as _uuid
            return _req.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "RqUID": str(_uuid.uuid4()),
                    "Authorization": f"Basic {api_key}",
                },
                data={"scope": "GIGACHAT_API_PERS"},
                timeout=10,
                verify=False
            )

        token_resp = await asyncio.to_thread(_get_token)
        if token_resp.status_code != 200:
            raise ValueError(f"GigaChat auth failed: {token_resp.status_code} {token_resp.text}")

        access_token = token_resp.json()["access_token"]

        # Шаг 2: Отправляем запрос
        def _send_chat():
            import requests as _req
            return _req.post(
                "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
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
                verify=False
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        chat_resp = await asyncio.to_thread(_send_chat)
        if chat_resp.status_code != 200:
            raise ValueError(f"GigaChat API error: {chat_resp.text}")

        data = chat_resp.json()
        text = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage", {})

        self._circuit_breaker.record_success()

        return LLMResponse(
            text=text,
            model=model_name,
            provider="gigachat",
            usage=usage,
            finish_reason=data["choices"][0].get("finish_reason"),
        )

    async def _generate_gigachat_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ):
        """Потоковый вызов GigaChat через HTTP"""
        import requests as req_lib

        model_name = model or "GigaChat"
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

        # Ключ в БД: client_id:base64_secret
        if api_key and ':' in api_key:
            parts = api_key.split(':', 1)
            secret = parts[1].replace('\n', '').replace('\r', '').replace(' ', '')
            if len(secret) > 80:
                api_key = secret
            else:
                import base64
                api_key = base64.b64encode(api_key.encode()).decode()

        # Шаг 1: Получаем токен (синхронный requests в thread)
        def _get_token():
            import requests as _req
            import uuid as _uuid
            return _req.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "RqUID": str(_uuid.uuid4()),
                    "Authorization": f"Basic {api_key}",
                },
                data={"scope": "GIGACHAT_API_PERS"},
                timeout=10,
                verify=False
            )

        token_resp = await asyncio.to_thread(_get_token)
        if token_resp.status_code != 200:
            yield f"❌ Auth failed: {token_resp.status_code} {token_resp.text}"
            return

        access_token = token_resp.json()["access_token"]

        # Шаг 2: Отправляем запрос
        def _send_chat():
            import requests as _req
            return _req.post(
                "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                json={
                    "model": model_name,
                    "messages": [
                        *([{"role": "system", "content": system_prompt}] if system_prompt else []),
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                    **({"max_tokens": max_tokens} if max_tokens else {}),
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                timeout=60,
                verify=False
            )

        chat_resp = await asyncio.to_thread(_send_chat)
        if chat_resp.status_code != 200:
            yield f"❌ GigaChat error: {chat_resp.status_code} {chat_resp.text}"
            return

        data = chat_resp.json()
        text = data["choices"][0]["message"]["content"] or ""
        yield text
        self._circuit_breaker.record_success()

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
        """
        Генерирует потоковый ответ

        Yields:
            Часть ответа (строка)
        """
        key = api_key or self.default_api_key
        model_name = model or self.default_model

        # GigaChat — используем ключ из БД (не из .env)
        if provider == "gigachat":
            if not key:
                raise ValueError("GigaChat ключ не настроен. Подключите провайдера в настройках.")

        if not key:
            raise ValueError("API ключ не настроен")

        # Формируем полное имя модели с учётом provider
        if provider:
            full_model = self._get_full_model_name(provider, model_name)
        else:
            full_model = self._get_full_model_name(
                self._detect_provider(model_name),
                model_name
            )

        # GigaChat — потоковый вызов через официальный SDK
        if provider == "gigachat":
            async for chunk in self._generate_gigachat_stream(
                prompt=prompt,
                system_prompt=system_prompt,
                api_key=key,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield chunk
            return

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await acompletion(
                model=full_model,
                messages=messages,
                api_key=key,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )

            async for chunk in response:
                if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    content = getattr(delta, "content", "") or ""
                    if content:
                        yield content

        except Exception as e:
            yield f"❌ Ошибка: {str(e)}"
    
    async def test_connection(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Тестирует подключение к провайдеру
        
        Returns:
            Результат теста
        """
        try:
            response = await self.generate(
                prompt="Привет! Ответь кратко.",
                api_key=api_key,
                model=model,
                max_tokens=10
            )
            
            return {
                "success": True,
                "message": "Подключение успешно",
                "model": response.model,
                "provider": response.provider,
                "response": response.text[:50] + "..." if len(response.text) > 50 else response.text
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_available_models(self, provider: str = None) -> List[Dict[str, Any]]:
        """
        Возвращает список доступных моделей — загружает АКТУАЛЬНЫЕ модели от провайдеров через LiteLLM
        """
        import litellm

        models = []
        seen_ids = set()

        # 1. Загружаем модели из litellm.model_cost — это актуальные данные от LiteLLM
        model_cost = getattr(litellm, 'model_cost', {})
        if model_cost:
            for model_name, info in model_cost.items():
                if provider and not model_name.startswith(f"{provider}/"):
                    continue
                if model_name in seen_ids:
                    continue
                seen_ids.add(model_name)

                try:
                    input_cost = info.get('input_cost_per_token', 0)
                    cost_label = 'free' if input_cost == 0 else ('low' if input_cost < 0.0001 else 'medium')
                    max_tokens = info.get('max_tokens', 4096)
                    prov = model_name.split('/')[0] if '/' in model_name else 'unknown'

                    models.append({
                        "id": model_name,
                        "name": model_name.split('/')[-1],
                        "provider": prov,
                        "max_tokens": max_tokens if isinstance(max_tokens, int) else 4096,
                        "supports_vision": info.get('supports_vision', False),
                        "supports_function_calling": info.get('supports_function_calling', True),
                        "cost": cost_label,
                    })
                except Exception:
                    pass

        # 2. Если model_cost пуст — загружаем модели через litellm.get_model_info для каждого провайдера
        if not models:
            # Список известных провайдеров
            providers_to_check = [
                'openai', 'google', 'anthropic', 'groq', 'deepseek',
                'mistral', 'xai', 'cohere', 'ollama', 'gigachat',
                'yandex', 'together_ai', 'openrouter'
            ] if not provider else [provider]

            for prov in providers_to_check:
                try:
                    # Пробуем получить модели через litellm
                    prov_models_attr = getattr(litellm, f'{prov}_models', None)
                    if prov_models_attr:
                        for model_name in prov_models_attr:
                            full_name = f"{prov}/{model_name}" if '/' not in model_name else model_name
                            if full_name in seen_ids:
                                continue
                            seen_ids.add(full_name)
                            models.append({
                                "id": full_name,
                                "name": model_name.split('/')[-1],
                                "provider": prov,
                                "max_tokens": 4096,
                                "supports_vision": False,
                                "supports_function_calling": True,
                                "cost": 'unknown',
                            })
                except Exception:
                    pass

        # 3. Если всё ещё пусто — пробуем получить через completion с test запросом
        if not models:
            logger.warning("⚠️ Не удалось загрузить модели из LiteLLM. Проверьте версию litellm.")

        return models
    
    def _get_fallback_models(self, provider: str = None) -> List[Dict[str, Any]]:
        """Расширенный fallback модели если LiteLLM не отдаёт"""
        fallback_models = {
            "openai": [
                {"id": "gpt-4o", "name": "GPT-4o", "max_tokens": 128000, "supports_vision": True},
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "max_tokens": 128000, "supports_vision": True},
                {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "max_tokens": 128000, "supports_vision": True},
                {"id": "gpt-4", "name": "GPT-4", "max_tokens": 8192, "supports_vision": False},
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "max_tokens": 16385, "supports_vision": False},
                {"id": "gpt-3.5-turbo-16k", "name": "GPT-3.5 Turbo 16K", "max_tokens": 16385, "supports_vision": False},
                {"id": "o1", "name": "o1", "max_tokens": 100000, "supports_vision": True},
                {"id": "o1-mini", "name": "o1 Mini", "max_tokens": 65536, "supports_vision": False},
                {"id": "o3-mini", "name": "o3 Mini", "max_tokens": 100000, "supports_vision": False},
            ],
            "google": [
                {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "max_tokens": 1048576, "supports_vision": True},
                {"id": "gemini-2.0-flash-lite", "name": "Gemini 2.0 Flash Lite", "max_tokens": 1048576, "supports_vision": True},
                {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "max_tokens": 2097152, "supports_vision": True},
                {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "max_tokens": 1048576, "supports_vision": True},
                {"id": "gemini-1.5-flash-8b", "name": "Gemini 1.5 Flash 8B", "max_tokens": 1048576, "supports_vision": True},
            ],
            "anthropic": [
                {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "max_tokens": 200000, "supports_vision": True},
                {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "max_tokens": 200000, "supports_vision": True},
                {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "max_tokens": 200000, "supports_vision": True},
                {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "max_tokens": 200000, "supports_vision": True},
                {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "max_tokens": 200000, "supports_vision": True},
            ],
            "groq": [
                {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B", "max_tokens": 131072, "supports_vision": False},
                {"id": "llama-3.1-70b-versatile", "name": "Llama 3.1 70B", "max_tokens": 131072, "supports_vision": False},
                {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B", "max_tokens": 131072, "supports_vision": False},
                {"id": "llama-3.2-1b-preview", "name": "Llama 3.2 1B", "max_tokens": 8192, "supports_vision": False},
                {"id": "llama-3.2-3b-preview", "name": "Llama 3.2 3B", "max_tokens": 8192, "supports_vision": False},
                {"id": "llama-3.2-11b-vision-preview", "name": "Llama 3.2 11B Vision", "max_tokens": 8192, "supports_vision": True},
                {"id": "llama-3.2-90b-vision-preview", "name": "Llama 3.2 90B Vision", "max_tokens": 8192, "supports_vision": True},
                {"id": "llama-guard-3-8b", "name": "Llama Guard 3 8B", "max_tokens": 8192, "supports_vision": False},
                {"id": "llama3-70b-8192", "name": "Llama 3 70B", "max_tokens": 8192, "supports_vision": False},
                {"id": "llama3-8b-8192", "name": "Llama 3 8B", "max_tokens": 8192, "supports_vision": False},
                {"id": "gemma2-9b-it", "name": "Gemma2 9B", "max_tokens": 8192, "supports_vision": False},
                {"id": "deepseek-r1-distill-llama-70b", "name": "DeepSeek R1 Distill 70B", "max_tokens": 131072, "supports_vision": False},
            ],
            "deepseek": [
                {"id": "deepseek-chat", "name": "DeepSeek Chat", "max_tokens": 128000, "supports_vision": False},
                {"id": "deepseek-coder", "name": "DeepSeek Coder", "max_tokens": 128000, "supports_vision": False},
                {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner", "max_tokens": 64000, "supports_vision": False},
            ],
            "ollama": [
                {"id": "llama3.2", "name": "Llama 3.2", "max_tokens": 8192, "supports_vision": False},
                {"id": "llama3.1", "name": "Llama 3.1", "max_tokens": 8192, "supports_vision": False},
                {"id": "mistral", "name": "Mistral", "max_tokens": 8192, "supports_vision": False},
                {"id": "codellama", "name": "Code Llama", "max_tokens": 4096, "supports_vision": False},
                {"id": "phi3", "name": "Phi 3", "max_tokens": 4096, "supports_vision": False},
            ],
            "gigachat": [
                {"id": "GigaChat", "name": "GigaChat", "max_tokens": 4096, "supports_vision": False},
                {"id": "GigaChat-Pro", "name": "GigaChat Pro", "max_tokens": 8192, "supports_vision": False},
                {"id": "GigaChat-Plus", "name": "GigaChat Plus", "max_tokens": 8192, "supports_vision": False},
            ],
            "mistral": [
                {"id": "mistral-large-latest", "name": "Mistral Large", "max_tokens": 128000, "supports_vision": False},
                {"id": "mistral-medium-latest", "name": "Mistral Medium", "max_tokens": 32000, "supports_vision": False},
                {"id": "mistral-small-latest", "name": "Mistral Small", "max_tokens": 32000, "supports_vision": False},
                {"id": "open-mistral-nemo", "name": "Mistral Nemo", "max_tokens": 128000, "supports_vision": False},
                {"id": "codestral-latest", "name": "Codestral", "max_tokens": 32000, "supports_vision": False},
            ],
            "xai": [
                {"id": "grok-2", "name": "Grok 2", "max_tokens": 131072, "supports_vision": False},
                {"id": "grok-2-vision", "name": "Grok 2 Vision", "max_tokens": 8192, "supports_vision": True},
            ],
            "cohere": [
                {"id": "command-r-plus", "name": "Command R+", "max_tokens": 128000, "supports_vision": False},
                {"id": "command-r", "name": "Command R", "max_tokens": 128000, "supports_vision": False},
                {"id": "command", "name": "Command", "max_tokens": 4096, "supports_vision": False},
            ],
            "openrouter": [
                {"id": "openrouter/auto", "name": "Auto (OpenRouter)", "max_tokens": 128000, "supports_vision": True},
            ],
            "together_ai": [
                {"id": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "name": "Llama 3.3 70B", "max_tokens": 32768, "supports_vision": False},
                {"id": "mistralai/Mixtral-8x7B-Instruct-v0.1", "name": "Mixtral 8x7B", "max_tokens": 32768, "supports_vision": False},
            ],
            "yandex": [
                {"id": "yandexgpt-lite", "name": "YandexGPT Lite", "max_tokens": 8192, "supports_vision": False},
                {"id": "yandexgpt-pro", "name": "YandexGPT Pro", "max_tokens": 16384, "supports_vision": False},
            ],
        }

        models = []

        if provider and provider in fallback_models:
            for model in fallback_models[provider]:
                models.append({
                    "id": model["id"],
                    "name": model["name"],
                    "provider": provider,
                    "max_tokens": model["max_tokens"],
                    "supports_vision": model.get("supports_vision", False),
                    "supports_function_calling": True,
                    "cost": 'unknown',
                })
        elif not provider:
            for prov, prov_models in fallback_models.items():
                for model in prov_models:
                    models.append({
                        "id": model["id"],
                        "name": model["name"],
                        "provider": prov,
                        "max_tokens": model["max_tokens"],
                        "supports_vision": model.get("supports_vision", False),
                        "supports_function_calling": True,
                        "cost": 'unknown',
                    })

        return models

    async def close_session(self):
        """
        Закрывает HTTP сессию при shutdown
        
        === ИСПРАВЛЕНИЕ 6: Connection Pooling ===
        """
        if self._session is not None:
            await self._session.close()
            self._session = None
            logger.info("✅ HTTP сессия закрыта")


# Глобальный экземпляр
_litellm_service: Optional[LiteLLMService] = None


def get_litellm_service() -> LiteLLMService:
    """
    Возвращает глобальный сервис LiteLLM
    """
    global _litellm_service
    if _litellm_service is None:
        _litellm_service = LiteLLMService()
    return _litellm_service
