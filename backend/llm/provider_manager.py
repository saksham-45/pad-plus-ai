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
from typing import Optional, Dict, List, Any
from abc import ABC, abstractmethod
import os
import sqlite3
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
                timeout=30.0,
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
    
    def __init__(self, api_key: str = None, enabled: bool = True, model: str = None):
        # Если api_key не передан, пытаемся получить из переменной окружения
        if api_key is None:
            api_key = os.getenv("OPENROUTER_API_KEY")
        super().__init__(api_key, enabled)
        self.model = model or os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
    
    async def generate(self, prompt: str, context: str = "") -> LLMResponse:
        if not self.enabled or not self.api_key:
            raise ValueError("OpenRouter не настроен")
        
        # Поддержка автовыбора бесплатной модели
        model = self.model
        if model.lower() == "free":
            model = "google/gemma-7b-it"  # Рабочая бесплатная модель
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://padplus-ai.onrender.com",
            "X-Title": "PAD+ AI"
        }
        
        data = {
            "model": model,
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
                timeout=30.0,
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
    
    async def test_connection(self) -> dict:
        """Тестирует подключение к OpenRouter"""
        if not self.enabled:
            return {
                "success": False,
                "error": "OpenRouter отключен"
            }
        
        if not self.api_key:
            return {
                "success": False,
                "error": "OpenRouter API ключ не настроен"
            }
        
        try:
            # Тестируем аутентификацию
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/auth",
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    self.healthy = True
                    return {
                        "success": True,
                        "message": "OpenRouter API ключ действителен"
                    }
                else:
                    self.healthy = False
                    return {
                        "success": False,
                        "error": f"Ошибка аутентификации: {response.status_code}"
                    }
        except Exception as e:
            self.healthy = False
            return {
                "success": False,
                "error": f"Ошибка подключения: {str(e)}"
            }


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
        """Настраивает провайдеров из переменных окружения и конфигурации"""
        from dotenv import load_dotenv
        from core.config_manager import get_config
        
        # Загружаем переменные окружения
        load_dotenv()
        
        config_manager = get_config()
        
        # GigaChat
        gigachat_key = os.getenv("GIGACHAT_API_KEY") or config_manager.get(
            "GIGACHAT_API_KEY"
        )
        gigachat_enabled = (
            os.getenv("GIGACHAT_ENABLED", "false").lower() == "true"
            or config_manager.get("GIGACHAT_ENABLED", False)
        )
        if gigachat_key and gigachat_enabled:
            self.register(GigaChatProvider(gigachat_key, True))
        
        # Gemini
        gemini_key = os.getenv("GOOGLE_API_KEY") or config_manager.get("GOOGLE_API_KEY")
        gemini_enabled = (
            os.getenv("GEMINI_ENABLED", "false").lower() == "true"
            or config_manager.get("GEMINI_ENABLED", False)
        )
        if gemini_key and gemini_enabled:
            self.register(GeminiProvider(gemini_key, True))
        
        # OpenRouter
        openrouter_key = os.getenv("OPENROUTER_API_KEY") or config_manager.get(
            "OPENROUTER_API_KEY"
        )
        openrouter_enabled = (
            os.getenv("OPENROUTER_ENABLED", "false").lower() == "true"
            or config_manager.get("OPENROUTER_ENABLED", False)
        )
        if openrouter_key and openrouter_enabled:
            model = config_manager.get("OPENROUTER_MODEL") or os.getenv(
                "OPENROUTER_MODEL", "openrouter/free"
            )
            self.register(OpenRouterProvider(openrouter_key, True, model))
    
    async def generate(self, prompt: str, context: str = "") -> LLMResponse:
        """Генерирует ответ через каскад провайдеров"""
        for name in self.order:
            provider = self.providers.get(name)
            if provider and provider.enabled:
                try:
                    response = await provider.generate(prompt, context)
                    # Сохраняем успешный ответ в fallback
                    self.fallback.save_response(prompt, response.text, response.confidence)
                    return response
                except Exception:
                    continue
        
        # Используем fallback
        return await self.fallback.generate(prompt, context)
    
    def has_active_providers(self) -> bool:
        """Проверяет, есть ли активные провайдеры"""
        return any(p.enabled for p in self.providers.values())
    
    async def test_provider(self, provider_name: str) -> dict:
        """Тестирует провайдера"""
        provider = self.providers.get(provider_name)
        if not provider:
            return {
                "success": False,
                "error": f"Провайдер {provider_name} не найден"
            }
        
        if not provider.enabled:
            return {
                "success": False,
                "error": f"Провайдер {provider_name} отключен"
            }
        
        try:
            # Тестируем генерацию ответа
            response = await provider.generate("Привет", "Тестовый запрос")
            return {
                "success": True,
                "message": f"Провайдер {provider_name} работает корректно",
                "response": response.text[:100] + "..." if len(response.text) > 100 else response.text
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка при тестировании провайдера {provider_name}: {str(e)}"
            }
    
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
    
    def get_providers_status(self) -> dict:
        """Возвращает статус провайдеров (для API)"""
        return {
            name: {
                "enabled": p.enabled,
                "healthy": p.healthy,
                "has_key": p.api_key is not None
            }
            for name, p in self.providers.items()
        }
    
    def get_active_provider_name(self) -> Optional[str]:
        """Возвращает имя активного провайдера"""
        for name in self.order:
            provider = self.providers.get(name)
            if provider and provider.enabled:
                return name
        return None
    
    def reload_providers(self):
        """Перезагружает провайдеров из конфигурации"""
        # Очищаем текущих провайдеров
        self.providers.clear()
        
        # Перезагружаем из environment variables
        self.setup_from_env()
        
        # Проверяем здоровье провайдеров
        for provider in self.providers.values():
            try:
                # Асинхронная проверка здоровья будет вызвана при необходимости
                provider.healthy = provider.enabled
            except Exception:
                provider.healthy = False


# Глобальный экземпляр
_provider_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """Возвращает глобальный менеджер провайдеров"""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
        _provider_manager.setup_from_env()
    return _provider_manager