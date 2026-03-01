"""
LLM Provider Manager — управление провайдерами ИИ

Каскад провайдеров:
1. GigaChat (основной)
2. Google Gemini
3. OpenRouter
4. SQLite Fallback (оффлайн)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable
from abc import ABC, abstractmethod
import json
import os
import sqlite3
import asyncio
import httpx


@dataclass
class LLMResponse:
    """Ответ от LLM"""
    text: str
    provider: str
    confidence: float = 0.5
    cached: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "provider": self.provider,
            "confidence": self.confidence,
            "cached": self.cached,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class BaseProvider(ABC):
    """Базовый класс для провайдеров LLM"""
    
    name: str = "base"
    
    def __init__(self, api_key: str = None, enabled: bool = True):
        self.api_key = api_key
        self.enabled = enabled
        self.healthy = False
    
    @abstractmethod
    async def generate(self, prompt: str, context: str = "") -> LLMResponse:
        """Генерирует ответ"""
        pass
    
    async def check_health(self) -> bool:
        """Проверяет здоровье провайдера"""
        return self.enabled


class GigaChatProvider(BaseProvider):
    """Провайдер GigaChat"""
    
    name = "gigachat"
    API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    
    def __init__(self, api_key: str = None, enabled: bool = True):
        super().__init__(api_key, enabled)
        self.model = "GigaChat:latest"
    
    async def generate(self, prompt: str, context: str = "") -> LLMResponse:
        if not self.enabled or not self.api_key:
            raise ValueError("GigaChat не настроен")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": context},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                self.API_URL,
                headers=headers,
                json=data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result["choices"][0]["message"]["content"]
                return LLMResponse(
                    text=text,
                    provider=self.name,
                    confidence=0.7
                )
            else:
                raise Exception(f"GigaChat error: {response.status_code}")


class GeminiProvider(BaseProvider):
    """Провайдер Google Gemini"""
    
    name = "gemini"
    API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    
    def __init__(self, api_key: str = None, enabled: bool = False):
        super().__init__(api_key, enabled)
    
    async def generate(self, prompt: str, context: str = "") -> LLMResponse:
        if not self.enabled or not self.api_key:
            raise ValueError("Gemini не настроен")
        
        url = f"{self.API_URL}?key={self.api_key}"
        
        data = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{context}\n\n{prompt}"}
                    ]
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, timeout=30.0)
            
            if response.status_code == 200:
                result = response.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return LLMResponse(
                    text=text,
                    provider=self.name,
                    confidence=0.7
                )
            else:
                raise Exception(f"Gemini error: {response.status_code}")


class OpenRouterProvider(BaseProvider):
    """Провайдер OpenRouter"""
    
    name = "openrouter"
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    def __init__(self, api_key: str = None, enabled: bool = False, model: str = None):
        super().__init__(api_key, enabled)
        self.model = model or os.getenv("OPENROUTER_MODEL", "google/gemma-7b-it")
    
    async def generate(self, prompt: str, context: str = "") -> LLMResponse:
        if not self.enabled or not self.api_key:
            raise ValueError("OpenRouter не настроен")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://padplus-ai.onrender.com",
            "X-Title": "PAD+ AI"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": context},
                {"role": "user", "content": prompt}
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.API_URL,
                headers=headers,
                json=data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result["choices"][0]["message"]["content"]
                return LLMResponse(
                    text=text,
                    provider=self.name,
                    confidence=0.7
                )
            else:
                raise Exception(f"OpenRouter error: {response.status_code}")


class SQLiteFallbackProvider(BaseProvider):
    """Fallback провайдер на SQLite (оффлайн)"""
    
    name = "sqlite_fallback"
    
    def __init__(self, db_path: str = None):
        super().__init__(None, True)
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "llm.db"
            )
        self.db_path = db_path
        self._ensure_tables()
        self.healthy = True
    
    def _ensure_tables(self):
        """Создаёт таблицы"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fallback_responses (
                id TEXT PRIMARY KEY,
                query_hash TEXT NOT NULL,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                confidence REAL DEFAULT 0.6,
                created_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_hash 
            ON fallback_responses(query_hash)
        """)
        
        conn.commit()
        conn.close()
    
    def _hash_query(self, query: str) -> str:
        """Хеширует запрос"""
        import hashlib
        return hashlib.md5(query.encode()).hexdigest()
    
    async def generate(self, prompt: str, context: str = "") -> LLMResponse:
        """Возвращает сохранённый ответ или заглушку"""
        query_hash = self._hash_query(prompt)
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Ищем существующий ответ
        cursor.execute(
            "SELECT * FROM fallback_responses WHERE query_hash = ?",
            (query_hash,)
        )
        row = cursor.fetchone()
        
        if row:
            conn.close()
            return LLMResponse(
                text=row["response"],
                provider=self.name,
                confidence=row["confidence"],
                cached=True,
                metadata={"query_id": row["id"]}
            )
        
        conn.close()
        
        # Возвращаем заглушку
        return LLMResponse(
            text="У меня нет информации по этому вопросу. "
                 "Пожалуйста, подключите провайдера ИИ для получения ответов.",
            provider=self.name,
            confidence=0.3,
            cached=False
        )
    
    def save_response(self, query: str, response: str, confidence: float = 0.6):
        """Сохраняет ответ для будущего использования"""
        import uuid
        query_hash = self._hash_query(query)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO fallback_responses 
            (id, query_hash, query, response, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4())[:8],
            query_hash,
            query,
            response,
            confidence,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()


class ProviderManager:
    """Менеджер провайдеров LLM"""
    
    def __init__(self):
        self.providers: Dict[str, BaseProvider] = {}
        self.fallback: SQLiteFallbackProvider = SQLiteFallbackProvider()
        self.order: List[str] = ["gigachat", "gemini", "openrouter"]
    
    def register(self, provider: BaseProvider):
        """Регистрирует провайдера"""
        self.providers[provider.name] = provider
    
    def setup_from_env(self):
        """Настраивает провайдеров из переменных окружения"""
        # GigaChat
        gigachat_key = os.getenv("GIGACHAT_API_KEY")
        gigachat_enabled = os.getenv("GIGACHAT_ENABLED", "false").lower() == "true"
        if gigachat_key and gigachat_enabled:
            self.register(GigaChatProvider(gigachat_key, True))
        
        # Gemini
        gemini_key = os.getenv("GOOGLE_API_KEY")
        gemini_enabled = os.getenv("GEMINI_ENABLED", "false").lower() == "true"
        if gemini_key and gemini_enabled:
            self.register(GeminiProvider(gemini_key, True))
        
        # OpenRouter
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        openrouter_enabled = os.getenv("OPENROUTER_ENABLED", "false").lower() == "true"
        if openrouter_key and openrouter_enabled:
            self.register(OpenRouterProvider(openrouter_key, True))
    
    async def generate(self, prompt: str, context: str = "") -> LLMResponse:
        """Генерирует ответ через каскад провайдеров"""
        last_error = None
        
        for name in self.order:
            provider = self.providers.get(name)
            if provider and provider.enabled:
                try:
                    response = await provider.generate(prompt, context)
                    # Сохраняем успешный ответ в fallback
                    self.fallback.save_response(prompt, response.text, response.confidence)
                    return response
                except Exception as e:
                    last_error = e
                    continue
        
        # Используем fallback
        return await self.fallback.generate(prompt, context)
    
    def has_active_providers(self) -> bool:
        """Проверяет, есть ли активные провайдеры"""
        return any(p.enabled for p in self.providers.values())
    
    def get_status(self) -> dict:
        """Возвращает статус провайдеров"""
        return {
            "providers": {
                name: {
                    "enabled": p.enabled,
                    "healthy": p.healthy
                }
                for name, p in self.providers.items()
            },
            "fallback": {
                "enabled": True,
                "healthy": self.fallback.healthy
            },
            "order": self.order
        }


# Глобальный экземпляр
_provider_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """Возвращает глобальный менеджер провайдеров"""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
        _provider_manager.setup_from_env()
    return _provider_manager