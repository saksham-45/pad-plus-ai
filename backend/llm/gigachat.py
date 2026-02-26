"""
GigaChat API Client — официальный клиент для GigaChat API

Поддерживает:
- Автоматическое обновление Access Token (каждые 30 минут)
- Отправку сообщений в чат
- Обработку ошибок авторизации
"""

import httpx
import asyncio
import os
from typing import Optional
from datetime import datetime
import logging
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env из корня проекта
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

logger = logging.getLogger("neuromind.gigachat")

# === Конфигурация API ===
AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
AUTH_KEY = os.getenv("GIGACHAT_AUTHORIZATION_KEY")
SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")


class GigaChatClient:
    """
    Клиент для работы с GigaChat API
    
    Автоматически управляет токенами авторизации.
    Токен действителен 30 минут, обновляется автоматически.
    """
    
    def __init__(self):
        self.token: Optional[str] = None
        self.token_expires_at: float = 0  # timestamp
        self.lock = asyncio.Lock()
        self.enabled = AUTH_KEY is not None and AUTH_KEY != "ВАШ_КЛЮЧ_ЗДЕСЬ"
        
        if not self.enabled:
            logger.warning("⚠️ GigaChat не настроен. Укажите GIGACHAT_AUTHORIZATION_KEY в .env")
    
    async def get_token(self) -> str:
        """Получает Access Token (автоматически обновляет при истечении)"""
        now = datetime.now().timestamp()
        
        # Если токен ещё действителен (с запасом в 60 секунд)
        if self.token and now < self.token_expires_at - 60:
            return self.token
        
        async with self.lock:
            # Повторная проверка после блокировки
            if self.token and now < self.token_expires_at - 60:
                return self.token
            
            logger.info("🔐 Запрашиваем новый Access Token у GigaChat...")
            
            # Генерируем уникальный UUID для запроса
            import uuid
            rquid = str(uuid.uuid4())
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "RqUID": rquid,
                "Authorization": f"Basic {AUTH_KEY}",
            }
            
            # Формируем data как form-encoded
            payload = f"scope={SCOPE}"
            
            try:
                async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                    response = await client.post(AUTH_URL, headers=headers, data=payload)
                    
                    if response.status_code in [401, 403]:
                        logger.error(f"❌ Ошибка авторизации: {response.text}")
                        raise Exception("Неверный или просроченный Authorization Key")
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    self.token = data["access_token"]
                    self.token_expires_at = now + data.get("expires_at", 1800)
                    
                    logger.info("✅ Новый Access Token получен")
                    return self.token
                    
            except Exception as e:
                logger.error(f"❌ Не удалось получить токен: {e}")
                raise
    
    async def generate(self, prompt: str, context: str = "", 
                       temperature: float = 0.7,
                       return_raw: bool = False) -> str | dict:
        """
        Генерирует ответ от GigaChat
        
        Args:
            prompt: Запрос пользователя
            context: Контекст (например, ANTI_DIRECTIVE)
            temperature: Креативность (0.0 - 1.0)
            return_raw: Если True, возвращает полный ответ с метаданными
            
        Returns:
            str или dict в зависимости от return_raw
        """
        if not self.enabled:
            return "⚠️ GigaChat не настроен. Укажите ключ в .env файле."
        
        try:
            token = await self.get_token()
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            
            messages = []
            
            # Добавляем контекст как системное сообщение
            if context:
                messages.append({"role": "system", "content": context})
            
            # Добавляем запрос пользователя
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": "GigaChat",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 1024,
            }
            
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                response = await client.post(API_URL, headers=headers, json=payload)
                
                if response.status_code == 401:
                    # Токен истёк, пробуем снова
                    self.token = None
                    return await self.generate(prompt, context, temperature)
                
                if response.status_code != 200:
                    logger.error(f"❌ GigaChat API: {response.status_code} - {response.text}")
                    return f"Ошибка API: {response.status_code}"
                
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                
                logger.info(f"💬 GigaChat: {content[:100]}...")
                
                if return_raw:
                    return {
                        "content": content,
                        "raw": result,
                        "metadata": {
                            "model": result.get("model", "GigaChat"),
                            "tokens": {
                                "prompt": result.get("usage", {}).get(
                                    "prompt_tokens", 0),
                                "completion": result.get("usage", {}).get(
                                    "completion_tokens", 0),
                                "total": result.get("usage", {}).get(
                                    "total_tokens", 0)
                            },
                            "finish_reason": result["choices"][0].get(
                                "finish_reason", "stop"),
                            "provider": "gigachat"
                        }
                    }
                return content
                
        except Exception as e:
            logger.error(f"❌ Ошибка генерации: {e}")
            return f"Ошибка: {str(e)}"
    
    async def check_health(self) -> dict:
        """Проверяет работоспособность GigaChat"""
        if not self.enabled:
            return {"status": "disabled", "message": "Ключ не настроен"}
        
        try:
            response = await self.generate("Привет", temperature=0.5)
            if "Ошибка" in response or "⚠️" in response:
                return {"status": "error", "message": response}
            return {"status": "ok", "message": "GigaChat работает"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# === Глобальный экземпляр ===
gigachat = GigaChatClient()