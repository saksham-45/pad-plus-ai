"""
GigaChatClient — HTTP-клиент для GigaChat API.

Фичи:
- Кэширование access_token (in-memory, с учётом expires_at)
- Единая логика auth: Basic Auth (client_id:secret), fallback на secret-only
- Exponential backoff retry для auth и chat
- Полный и streaming режимы
"""

from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import os
import asyncio
import base64
import uuid
import json as json_module
import logging

import httpx

logger = logging.getLogger("padplus.gigachat_client")

GIGACHAT_AUTH_URL = os.getenv("GIGACHAT_AUTH_URL", "https://ngw.devices.sberbank.ru:9443/api/v2/oauth")
GIGACHAT_API_URL = os.getenv("GIGACHAT_API_URL", "https://gigachat.devices.sberbank.ru/api/v1/chat/completions")


class GigaChatAuthError(Exception):
    pass


class GigaChatAPIError(Exception):
    pass


class GigaChatClient:
    _token_cache: Dict[str, Dict] = {}
    _cache_lock = asyncio.Lock()

    def __init__(self):
        verify_str = os.getenv("GIGACHAT_VERIFY_TLS", "false").strip().lower()
        self._verify_tls = verify_str not in ("0", "false", "no")
        self._timeout = httpx.Timeout(60.0, connect=15.0)

    def _encode_key(self, api_key: str) -> str:
        if not api_key:
            raise ValueError("GigaChat: API ключ пуст")

        cleaned = api_key.strip()

        if ":" in cleaned:
            parts = cleaned.split(":", 1)
            secret = parts[1].replace("\n", "").replace("\r", "").replace(" ", "")
            cleaned = f"{parts[0]}:{secret}"
            if len(secret) > 80:
                return secret

        if len(cleaned) > 80:
            return cleaned

        return base64.b64encode(cleaned.encode()).decode()

    async def _get_access_token(self, api_key: str) -> str:
        encoded_key = self._encode_key(api_key)
        cache_key = encoded_key[-32:]

        async with self._cache_lock:
            cached = self._token_cache.get(cache_key)
            if cached:
                expires_at = cached.get("expires_at", 0)
                expires_at_sec = expires_at / 1000 if expires_at > 1e12 else expires_at
                if expires_at_sec > int(datetime.now().timestamp()) + 60:
                    logger.info("GigaChat: using cached access_token")
                    return cached["access_token"]
                else:
                    self._token_cache.pop(cache_key, None)

        access_token, expires_at = await self._auth(api_key, encoded_key)

        async with self._cache_lock:
            self._token_cache[cache_key] = {
                "access_token": access_token,
                "expires_at": expires_at,
            }

        return access_token

    async def _auth(self, api_key: str, encoded_key: str) -> tuple:
        rquid = str(uuid.uuid4())
        auth_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": rquid,
            "Authorization": f"Basic {encoded_key}",
        }

        auth_variants = [
            ("Basic Auth (client_id:secret)", auth_headers),
        ]

        if api_key and ":" in api_key:
            secret_only = api_key.strip().split(":", 1)[1]
            secret_b64 = base64.b64encode(secret_only.encode()).decode()
            alt_headers = dict(auth_headers)
            alt_headers["Authorization"] = f"Basic {secret_b64}"
            auth_variants.append(("Basic Auth (secret only)", alt_headers))

        last_error = None

        for method_name, headers in auth_variants:
            for attempt in range(3):
                try:
                    async with httpx.AsyncClient(
                        timeout=httpx.Timeout(15.0, connect=10.0),
                        verify=self._verify_tls,
                    ) as session:
                        resp = await session.post(
                            GIGACHAT_AUTH_URL,
                            headers=headers,
                            data={"scope": "GIGACHAT_API_PERS"},
                        )

                    if resp.status_code == 200:
                        data = resp.json()
                        access_token = data.get("access_token")
                        expires_at = data.get("expires_at", 0)
                        if not access_token:
                            raise GigaChatAuthError("Auth response missing access_token")
                        logger.info(f"GigaChat auth succeeded: {method_name}")
                        return access_token, expires_at

                    if resp.status_code in (401, 403):
                        last_error = f"{method_name}: {resp.status_code} Unauthorized"
                        break

                    last_error = f"{method_name}: {resp.status_code}"
                    if attempt < 2:
                        wait = 1 * (2 ** attempt)
                        logger.warning(f"GigaChat auth retry {attempt+1}/3: {last_error}, waiting {wait}s")
                        await asyncio.sleep(wait)

                except httpx.TimeoutException as e:
                    last_error = f"{method_name}: timeout ({e})"
                    if attempt < 2:
                        await asyncio.sleep(1 * (2 ** attempt))

        raise GigaChatAuthError(
            f"GigaChat auth failed. Last error: {last_error}. "
            f"Проверьте API ключ на https://developers.sber.ru/gigachat"
        )

    async def _chat_request(
        self,
        access_token: str,
        messages: list,
        model: str,
        temperature: float,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
    ) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens
        if os.getenv("GIGACHAT_PROFANITY_CHECK", "false").lower() == "true":
            body["profanity_check"] = True

        last_error = None
        for attempt in range(3):
            try:
                if attempt > 0 and api_key:
                    access_token = await self._get_access_token(api_key)
                    headers["Authorization"] = f"Bearer {access_token}"

                async with httpx.AsyncClient(
                    timeout=self._timeout,
                    verify=self._verify_tls,
                ) as session:
                    resp = await session.post(
                        GIGACHAT_API_URL,
                        json=body,
                        headers=headers,
                    )

                if resp.status_code == 200:
                    return resp

                if resp.status_code == 401 and api_key:
                    encoded_key = self._encode_key(api_key)
                    cache_key = encoded_key[-32:]
                    async with self._cache_lock:
                        self._token_cache.pop(cache_key, None)
                    last_error = "401 Unauthorized — access_token истёк, обновляю..."
                    logger.warning(last_error)
                    continue

                resp_body = str(getattr(resp, "content", b""), "utf-8", errors="replace")[:200]
                last_error = f"HTTP {resp.status_code}: {resp_body}"
                if attempt < 2:
                    wait = 1 * (2 ** attempt)
                    logger.warning(f"GigaChat chat retry {attempt+1}/3: {last_error}, waiting {wait}s")
                    await asyncio.sleep(wait)

            except httpx.TimeoutException as e:
                last_error = f"timeout ({e})"
                if attempt < 2:
                    await asyncio.sleep(1 * (2 ** attempt))

        raise GigaChatAPIError(f"GigaChat chat failed: {last_error}")

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        api_key: Optional[str] = None,
        model: str = "GigaChat",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> dict:
        if not api_key:
            raise ValueError("API ключ не настроен")

        access_token = await self._get_access_token(api_key)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        resp = await self._chat_request(
            access_token=access_token,
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
        )

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise GigaChatAPIError(f"GigaChat вернул пустой choices: {data}")

        choice = choices[0]
        text = choice.get("message", {}).get("content", "") or choice.get("text", "") or ""
        usage = data.get("usage", {}) or {}

        return {
            "text": text,
            "model": model,
            "provider": "gigachat",
            "usage": usage,
            "finish_reason": choice.get("finish_reason"),
            "raw_response": data,
        }

    async def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        api_key: Optional[str] = None,
        model: str = "GigaChat",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        if not api_key:
            raise ValueError("API ключ не настроен")

        access_token = await self._get_access_token(api_key)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens

        for attempt in range(3):
            if attempt > 0:
                access_token = await self._get_access_token(api_key)

            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

            async with httpx.AsyncClient(
                timeout=self._timeout,
                verify=self._verify_tls,
            ) as session:
                async with session.stream(
                    "POST",
                    GIGACHAT_API_URL,
                    json=body,
                    headers=headers,
                ) as response:
                    if response.status_code == 401:
                        encoded_key = self._encode_key(api_key)
                        cache_key = encoded_key[-32:]
                        async with self._cache_lock:
                            self._token_cache.pop(cache_key, None)
                        logger.warning("GigaChat stream 401 — обновляю токен...")
                        continue

                    if response.status_code != 200:
                        error_body = await response.aread()
                        raise GigaChatAPIError(
                            f"GigaChat stream error: {response.status_code} — "
                            f"{error_body.decode('utf-8', errors='replace')[:300]}"
                        )

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            try:
                                chunk = json_module.loads(data_str)
                                if "choices" in chunk:
                                    choices = chunk["choices"]
                                    if choices and isinstance(choices, list):
                                        delta = choices[0].get("delta", {})
                                        if isinstance(delta, dict):
                                            content = delta.get("content", "")
                                            if content:
                                                yield content
                                        message = choices[0].get("message", {})
                                        if isinstance(message, dict):
                                            content = message.get("content", "")
                                            if content:
                                                yield content
                                content = chunk.get("content", "")
                                if content:
                                    yield content
                            except json_module.JSONDecodeError:
                                if data_str and data_str not in ("[DONE]", ""):
                                    yield data_str

                    break  # успешный стрим — выходим из retry-цикла


_client: Optional[GigaChatClient] = None


def get_gigachat_client() -> GigaChatClient:
    global _client
    if _client is None:
        _client = GigaChatClient()
    return _client
