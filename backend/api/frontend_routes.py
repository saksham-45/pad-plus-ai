"""
API Routes for frontend - Supabase Auth + Keys + Chat

Endpoints for the new frontend with Supabase Auth:
- POST /api/v1/auth/register - Registration (Supabase Auth)
- POST /api/v1/auth/login - Login (Supabase Auth)
- GET /api/v1/auth/me - Current user
- GET /api/v1/keys - List keys
- POST /api/v1/keys - Add key
- DELETE /api/v1/keys/{id} - Delete key
- POST /api/v1/keys/{id}/test - Test key
- GET /api/v1/providers - List providers
- POST /api/v1/chat - Chat
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime
import logging
import uuid
import asyncio

logger = logging.getLogger("padplus")
import hashlib
import json
import os

T = TypeVar('T')

# Импорты шифрования и БД
from core.encryption import get_encryptor
from core.supabase_client import (
    get_supabase,
    get_supabase_service,
    get_db_client,
    check_database_connection
)
from core.cache_manager import get_cache_manager

router = APIRouter(prefix="/api/v1", tags=["Frontend API"])


# ============================================================================
# МОДЕЛИ ДАННЫХ
# ============================================================================

class UserRegister(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str] = None
    created_at: str


class APIKeyCreate(BaseModel):
    provider: str
    api_key: str
    name: Optional[str] = None
    model_preference: str = "auto"
    is_default: bool = False


class APIKeyUpdate(BaseModel):
    api_key: Optional[str] = None  # Для обновления самого ключа
    name: Optional[str] = None
    model_preference: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class APIKeyResponse(BaseModel):
    id: str
    provider: str
    provider_display_name: str
    name: Optional[str]
    model_preference: str
    is_default: bool
    is_active: bool
    created_at: str
    last_used_at: Optional[str] = None
    has_key: bool = True
    is_system_configured: bool = False  # Для GigaChat системной настройки


class ProviderResponse(BaseModel):
    id: str
    name: str
    description: str
    free_models: List[str]
    website: str
    is_premium: bool


# ============================================================================
# PAGINATION
# ============================================================================

class PaginatedRequest(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    total: int
    offset: int
    limit: int
    has_more: bool


class ChatRequest(BaseModel):
    message: Optional[str] = None
    prompt: Optional[str] = None  # Для совместимости
    model: Optional[str] = "auto"
    key_id: Optional[str] = None
    provider: Optional[str] = None  # Явный провайдер от фронтенда
    stream: bool = False
    dialog_id: Optional[str] = None  # ID существующего диалога для продолжения
    auto_mode: bool = True
    explain: bool = False

    @property
    def text(self) -> str:
        """Возвращает текст запроса (message или prompt)"""
        return self.prompt or self.message or ""


class ChatResponse(BaseModel):
    text: str
    model: str
    provider: str
    usage: Dict[str, int]
    finish_reason: Optional[str] = None
    timestamp: str
    dialog_id: Optional[str] = None  # ID диалога для продолжения чата
    confidence: Optional[float] = None
    truth_confidence: Optional[float] = None
    rag_used: Optional[bool] = None
    facts_used: Optional[int] = None
    emotion: Optional[Dict[str, Any]] = None
    is_fast_mode: Optional[bool] = None  # Показывает, какой режим использовался
    # === COGNITIVE UX LAYER: Полные мета-данные ===
    cognitive: Optional[Dict[str, Any]] = None
    memory: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    safety: Optional[Dict[str, Any]] = None
    truth: Optional[Dict[str, Any]] = None
    xray: Optional[Dict[str, Any]] = None  # При explain=true


class TestKeyRequest(BaseModel):
    provider: str
    api_key: str


class TestKeyResponse(BaseModel):
    success: bool
    message: str
    model_tested: Optional[str] = None


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

# Паттерны для быстрых запросов (не требуют Pipeline)
FAST_PATTERNS = [
    "привет", "здравствуй", "hello", "hi",
    "как дела", "как жизнь", "как настроение",
    "спасибо", "благодарю", "thank",
    "пока", "до свидания", "goodbye", "bye",
    "да", "нет", "yes", "no",
    "ок", "okay", "ok", "хорошо",
    "повтори", "ещё раз", "again",
    "что это", "кто это",  # Короткие вопросы
]

def is_fast_request(text: str) -> bool:
    """
    Определяет, является ли запрос быстрым
    
    Быстрые запросы:
    - Короткие (< 10 слов)
    - Простые паттерны (приветствия, благодарности)
    - Без сложных вопросов (нет "почему", "как работает", "сравни")
    
    Args:
        text: Текст запроса
    
    Returns:
        True если запрос быстрый, False если требует полной обработки
    """
    text_lower = text.lower().strip()
    words = text.split()
    
    # 1. Очень короткие запросы (< 5 слов)
    if len(words) < 5:
        # Проверяем на простые паттерны
        if any(pattern in text_lower for pattern in FAST_PATTERNS):
            return True
        
        # Короткие вопросы без контекста
        if text_lower.startswith(("что ", "кто ", "где ", "когда ")) and len(words) < 6:
            return True
    
    # 2. Проверка на сложные паттерны (требуют Pipeline)
    SLOW_PATTERNS = [
        "почему", "как работает", "объясни", "сравни",
        "проанализируй", "составь план", "как сделать",
        "вспомни", "что я спрашивал", "что ты знаешь",
        "какое мнение", "что думаешь",
    ]
    
    if any(pattern in text_lower for pattern in SLOW_PATTERNS):
        return False
    
    # 3. Если нет вопросительного знака и коротко
    if "?" not in text and len(words) < 10:
        return True
    
    # 4. По умолчанию — не быстрый (требует Pipeline)
    return False


def get_provider_display_name(provider: str) -> str:
    """Возвращает отображаемое имя провайдера"""
    names = {
        "openrouter": "OpenRouter",
        "google": "Google AI Studio",
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "groq": "Groq",
        "ollama": "Ollama (Local)",
        "gemini": "Google Gemini",
        "gigachat": "GigaChat"
    }
    return names.get(provider, provider.title())


async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_refresh_token: Optional[str] = Header(None, alias="X-Refresh-Token")
) -> dict:
    """
    Получает текущего пользователя из Supabase Auth
    
    Улучшенная версия с поддержкой refresh_token и обработкой истекших токенов
    """
    from core.auth_manager import get_current_user_safe
    
    # Используем улучшенную функцию аутентификации
    return await get_current_user_safe(authorization, x_refresh_token)


# ============================================================================
# AUTH ENDPOINTS (Supabase Auth)
# ============================================================================

@router.post("/auth/register")
async def register(data: UserRegister):
    """
    Регистрация нового пользователя через Supabase Auth
    
    1. Создаёт пользователя в Supabase Auth
    2. Создаёт профиль в public.users
    """
    supabase = get_supabase()
    
    if not supabase:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    try:
        # 1. Создаём через Supabase Auth
        # Сначала пробуем через Admin API (service_role — без лимитов)
        service_client = get_supabase_service()
        user_id = None

        if service_client:
            try:
                admin_response = service_client.auth.admin.create_user({
                    "email": data.email,
                    "password": data.password,
                    "email_confirm": True,
                    "user_metadata": {"full_name": data.full_name or ""}
                })
                user_id = admin_response.user.id
            except Exception as admin_err:
                logger.warning(f"Admin API не сработал, пробую sign_up: {admin_err}")

        if not user_id:
            auth_response = supabase.auth.sign_up({
                "email": data.email,
                "password": data.password,
                "options": {
                    "data": {
                        "full_name": data.full_name
                    }
                }
            })
            if not auth_response.user:
                raise HTTPException(status_code=400, detail="Ошибка регистрации")
            user_id = auth_response.user.id

        # 2. Создаём профиль в public.users (через service_role — обход RLS)
        profile_data = {
            "id": user_id,
            "email": data.email,
            "hashed_password": "",
            "full_name": data.full_name or "",
            "avatar_url": None,
            "email_verified": True,
            "is_active": True
        }

        service_client = get_supabase_service()
        upsert_data = {**profile_data, "updated_at": datetime.now().isoformat()}
        if service_client:
            try:
                service_client.table("users").upsert(upsert_data, on_conflict="email").execute()
            except Exception as insert_err:
                logger.warning(f"service client upsert failed, trying anon: {insert_err}")
                try:
                    supabase.table("users").upsert(upsert_data, on_conflict="email").execute()
                except Exception:
                    pass
        else:
            try:
                supabase.table("users").upsert(upsert_data, on_conflict="email").execute()
            except Exception:
                pass

        return {
            "id": user_id,
            "email": data.email,
            "full_name": data.full_name,
            "created_at": datetime.now().isoformat()
        }

    except Exception as e:
        error_msg = str(e)
        if "User already registered" in error_msg:
            raise HTTPException(status_code=400, detail="Пользователь уже существует")
        raise HTTPException(status_code=500, detail=f"Ошибка регистрации: {error_msg}")


@router.post("/auth/login")
async def login(credentials: UserLogin):
    """
    Вход через Supabase Auth
    
    1. Проверяет credentials через Supabase
    2. Возвращает access token и refresh token
    """
    supabase = get_supabase()
    
    if not supabase:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    try:
        # 1. Вход через Supabase Auth
        auth_response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=401, detail="Неверный email или пароль")
        
        user = auth_response.user
        
        # 2. Устанавливаем сессию на клиенте для последующих запросов
        supabase.auth.set_session(auth_response.session.access_token, auth_response.session.refresh_token)
        
        # 3. Получаем профиль
        try:
            profile_response = supabase.table("users")\
                .select("*")\
                .eq("id", user.id)\
                .execute()
            
            profile = profile_response.data[0] if profile_response.data else None
        except Exception as profile_error:
            logger.warning(f"Не удалось получить профиль пользователя: {profile_error}")
            profile = None
        
        # 3. Возвращаем токены
        return {
            "access_token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token,
            "token_type": "bearer",
            "expires_in": auth_response.session.expires_in,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": profile.get("full_name") if profile else None,
                "avatar_url": profile.get("avatar_url") if profile else None
            }
        }
        
    except Exception as e:
        # Логируем полную информацию об исключении для диагностики (временная мера)
        logger.exception("Ошибка при входе через Supabase Auth")
        if "Invalid login credentials" in str(e):
            raise HTTPException(status_code=401, detail="Неверный email или пароль")
        raise HTTPException(status_code=500, detail=f"Ошибка входа: {str(e)}")


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    profile = current_user.get("profile")
    
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=profile.get("full_name"),
        avatar_url=profile.get("avatar_url"),
        created_at=profile.get("created_at", datetime.now().isoformat())
    )


@router.post("/auth/refresh")
async def refresh_token(refresh_token: str = Header(..., alias="X-Refresh-Token")):
    """Обновление access токена"""
    supabase = get_supabase()
    
    if not supabase:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    try:
        response = supabase.auth.refresh_session(refresh_token)
        
        if not response.session:
            raise HTTPException(status_code=401, detail="Неверный refresh токен")
        
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "expires_in": response.session.expires_in
        }
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Ошибка обновления токена: {str(e)}")


# ============================================================================
# PROVIDERS ENDPOINTS
# ============================================================================

@router.get("/providers/status")
async def providers_status():
    """
    Статус всех провайдеров: настроены ли, есть ли ключи.
    Без авторизации — только системная информация.
    """
    from runtime.provider_manager import get_provider_manager

    pm = get_provider_manager()
    available = pm.get_available_providers()
    
    return {
        "providers": available,
        "fallback_order": {
            "openrouter": ["openrouter", "gigachat"],
            "gigachat": ["gigachat"],
        },
        "default_fallback": ["openrouter", "gigachat"],
    }


@router.get("/providers", response_model=List[ProviderResponse])
async def list_providers():
    """Список доступных провайдеров — OpenRouter и GigaChat"""
    import os

    # Проверка: есть ли глобальный GigaChat ключ в .env
    gigachat_system_key = os.getenv("GIGACHAT_AUTH_KEY")
    has_gigachat_system_key = bool(gigachat_system_key and gigachat_system_key.strip())

    # Только реально поддерживаемые провайдеры (HuggingFace удалён)
    providers = [
        {
            "id": "openrouter",
            "name": "OpenRouter",
            "description": "Универсальный роутер к 200+ моделям (GPT, Claude, Gemini, Llama и др.)",
            "free_models": ["gpt-4o-mini", "gemini-2.0-flash", "claude-3-5-haiku"],
            "website": "https://openrouter.ai",
            "is_premium": False,
            "has_system_key": False
        },
        {
            "id": "gigachat",
            "name": "GigaChat",
            "description": "Модели от Сбера (GigaChat API)",
            "free_models": ["GigaChat-Plus", "GigaChat-Pro"],
            "website": "https://developers.sber.ru/docs/ru/gigachat",
            "is_premium": False,
            "has_system_key": has_gigachat_system_key
        }
    ]
    
    return providers


# ============================================================================
# API KEY MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/keys", response_model=PaginatedResponse[APIKeyResponse])
async def list_keys(
    current_user: dict = Depends(get_current_user),
    offset: int = 0,
    limit: int = 50
):
    """
    Список API ключей пользователя с пагинацией
    
    Args:
        offset: Смещение (по умолчанию 0)
        limit: Количество результатов (1-100, по умолчанию 50)
    """
    import os
    supabase = get_db_client(current_user)
    if not supabase:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    user_id = current_user["id"]
    
    # Проверка: есть ли глобальный GigaChat ключ
    gigachat_system_key = os.getenv("GIGACHAT_AUTH_KEY")
    has_gigachat_system_key = bool(gigachat_system_key and gigachat_system_key.strip())
    
    # Ограничиваем limit
    limit = min(max(limit, 1), 100)

    try:
        # Получаем общее количество (только count, без данных)
        count_result = supabase.table("user_api_keys")\
            .select("id", count="exact")\
            .eq("user_id", user_id)\
            .limit(0)\
            .execute()
        
        total = count_result.count if count_result.count else 0
        
        # Получаем данные с пагинацией
        result = supabase.table("user_api_keys")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        # Защита от None
        if not hasattr(result, 'data') or result.data is None:
            logger.warning(f"?? Пустой ответ от Supabase для user_id={user_id}. Проверьте RLS политики или существование таблицы.")
            keys = []
        else:
            keys = []
            for key in result.data:
                keys.append(APIKeyResponse(
                    id=key["id"],
                    provider=key["provider"],
                    provider_display_name=get_provider_display_name(key["provider"]),
                    name=key.get("name"),
                    model_preference=key.get("model_preference", "auto"),
                    is_default=key.get("is_default", False),
                    is_active=key.get("is_active", True),
                    created_at=key["created_at"],
                    last_used_at=key.get("last_used_at"),
                    has_key=True,
                    is_system_configured=(key["provider"] == "gigachat" and has_gigachat_system_key)
                ))
        
        # Если нет ключа GigaChat у пользователя, но есть системный - добавляем виртуальный ключ
        if has_gigachat_system_key:
            has_user_gigachat = any(k.provider == "gigachat" for k in keys)
            if not has_user_gigachat:
                # Вставляем системный GigaChat ключ в начало списка
                keys.insert(0, APIKeyResponse(
                    id="system-gigachat",
                    provider="gigachat",
                    provider_display_name="GigaChat (System)",
                    name="GigaChat (Global Config)",
                    model_preference="GigaChat-2-Lite",
                    is_default=total == 0,  # Default если нет других ключей
                    is_active=True,
                    created_at=datetime.now().isoformat(),
                    last_used_at=None,
                    has_key=True,
                    is_system_configured=True
                ))
                total += 1
        
        return PaginatedResponse(
            data=keys,
            total=total,
            offset=offset,
            limit=limit,
            has_more=offset + limit < total
        )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"? Ошибка получения списка ключей: {error_msg}")
        
        # Обработка конкретных ошибок Supabase
        if "table not found" in error_msg.lower() or "relation does not exist" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Таблица user_api_keys не найдена. Проверьте миграции базы данных.")
        elif "permission denied" in error_msg.lower() or "rls" in error_msg.lower():
            raise HTTPException(status_code=403, detail="Доступ к таблице user_api_keys запрещён. Проверьте RLS политики.")
        else:
            raise HTTPException(status_code=500, detail=f"Ошибка получения списка ключей: {error_msg}")


@router.post("/keys", response_model=APIKeyResponse)
async def create_key(
    data: APIKeyCreate,
    current_user: dict = Depends(get_current_user)
):
    """Добавление API ключа"""
    supabase = get_db_client(current_user)
    encryptor = get_encryptor()
    user_id = current_user["id"]

    if not supabase:
        raise HTTPException(status_code=500, detail="БД не подключена")

    logger.info(f"?? Creating key: provider={data.provider}, model={data.model_preference}, is_default={data.is_default}")

    # Шифруем ключ
    encrypted_key = encryptor.encrypt(data.api_key)
    logger.info(f"?? Encrypted key length: {len(encrypted_key)}")

    # Если is_default=True, сбрасываем остальные
    if data.is_default:
        supabase.table("user_api_keys")\
            .update({"is_default": False})\
            .eq("user_id", user_id)\
            .execute()

    # Создаём запись
    key_id = str(uuid.uuid4())

    try:
        result = supabase.table("user_api_keys").insert({
            "id": key_id,
            "user_id": user_id,
            "provider": data.provider,
            "provider_display_name": get_provider_display_name(data.provider),
            "name": data.name,
            "api_key_encrypted": encrypted_key,
            "model_preference": data.model_preference,
            "is_default": data.is_default,
            "is_active": True
        }).execute()
    except Exception as e:
        logger.error(f"? Failed to insert key: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения: {str(e)}")

    if not result.data:
        logger.error(f"? No data returned from insert")
        raise HTTPException(status_code=500, detail="Ошибка сохранения ключа")
    
    key_data = result.data[0]
    
    return APIKeyResponse(
        id=key_data["id"],
        provider=key_data["provider"],
        provider_display_name=get_provider_display_name(key_data["provider"]),
        name=key_data.get("name"),
        model_preference=key_data.get("model_preference", "auto"),
        is_default=key_data.get("is_default", False),
        is_active=key_data.get("is_active", True),
        created_at=key_data["created_at"],
        has_key=True
    )


@router.delete("/keys/{key_id}")
async def delete_key(
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Удаление API ключа"""
    supabase = get_db_client(current_user)
    if not supabase:
        raise HTTPException(status_code=500, detail="БД не подключена")
    user_id = current_user["id"]
    
    result = supabase.table("user_api_keys")\
        .delete()\
        .eq("id", key_id)\
        .eq("user_id", user_id)\
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Ключ не найден")
    
    return {"success": True, "message": "Ключ удалён"}


@router.post("/keys/{key_id}/set-default")
async def set_default_key(
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Установка ключа по умолчанию"""
    supabase = get_db_client(current_user)
    if not supabase:
        raise HTTPException(status_code=500, detail="БД не подключена")
    user_id = current_user["id"]
    
    # Сначала сбрасываем все ключи пользователя
    supabase.table("user_api_keys")\
        .update({"is_default": False})\
        .eq("user_id", user_id)\
        .execute()
    
    # Затем устанавливаем нужный ключ как default
    result = supabase.table("user_api_keys")\
        .update({"is_default": True})\
        .eq("id", key_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Ключ не найден")
    
    return {"success": True, "message": "Ключ установлен по умолчанию"}


@router.patch("/keys/{key_id}")
async def update_key(
    key_id: str,
    data: APIKeyUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Обновление API ключа (модель, имя, сам ключ)"""
    supabase = get_db_client(current_user)
    if not supabase:
        raise HTTPException(status_code=500, detail="БД не подключена")
    encryptor = get_encryptor()
    user_id = current_user["id"]
    
    # Собираем только переданные поля
    update_data = {}
    
    # Если передан новый ключ — шифруем его
    if data.api_key is not None:
        encrypted_key = encryptor.encrypt(data.api_key.strip())
        update_data["api_key_encrypted"] = encrypted_key
        logger.info(f"?? Updating key for user {user_id}: key_id={key_id}")
    
    if data.model_preference is not None:
        update_data["model_preference"] = data.model_preference
    if data.name is not None:
        update_data["name"] = data.name
    if data.is_default is not None:
        update_data["is_default"] = data.is_default
    if data.is_active is not None:
        update_data["is_active"] = data.is_active
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")
    
    try:
        result = supabase.table("user_api_keys")\
            .update(update_data)\
            .eq("id", key_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Ключ не найден")
        
        logger.info(f"? Key updated successfully: key_id={key_id}")
        return {"success": True, "message": "Ключ обновлён"}
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"? Failed to update key: {error_msg}")
        
        if "permission denied" in error_msg.lower() or "rls" in error_msg.lower():
            raise HTTPException(
                status_code=403,
                detail="Доступ запрещён. Проверьте RLS политики или доступ к ключу."
            )
        else:
            raise HTTPException(status_code=500, detail=f"Ошибка обновления: {error_msg}")


@router.post("/keys/{key_id}/test", response_model=TestKeyResponse)
async def test_key(
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Тестирование сохранённого API ключа"""
    supabase = get_db_client(current_user)
    if not supabase:
        raise HTTPException(status_code=500, detail="БД не подключена")
    encryptor = get_encryptor()
    user_id = current_user["id"]
    
    # Получаем ключ
    result = supabase.table("user_api_keys")\
        .select("*")\
        .eq("id", key_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Ключ не найден")
    
    key_data = result.data[0]
    api_key = encryptor.decrypt(key_data["api_key_encrypted"])
    
    # Тестируем ключ через ProviderManager
    from runtime.provider_manager import get_provider_manager

    try:
        provider = key_data["provider"]
        model = key_data.get("model_preference")
        
        if not model:
            raise HTTPException(
                status_code=400,
                detail=f"Модель не указана. Укажите model_preference при добавлении ключа."
            )

        # Тестируем через ProviderManager
        pm = get_provider_manager()
        result = await pm.test_connection(
            api_key=api_key,
            provider=provider,
            model=model,
        )
        
        # Если тест успешен — обновляем last_used_at
        if result["success"]:
            supabase.table("user_api_keys").update({
                "last_used_at": datetime.now().isoformat()
            }).eq("id", key_id).execute()
        
        return TestKeyResponse(
            success=result["success"],
            message=result["message"],
            model_tested=result.get("model_tested", model),
        )
        
    except Exception as e:
        return TestKeyResponse(
            success=False,
            message=f"Ошибка: {str(e)}",
            model_tested=None
        )


@router.post("/keys/test", response_model=TestKeyResponse)
async def test_key_direct(data: TestKeyRequest):
    """Тестирование API ключа (прямое, без сохранения)"""
    # Тест через API отключён — пользователь должен тестировать через чат
    raise HTTPException(
        status_code=400,
        detail="Тест через API недоступен. Добавьте ключ и используйте чат для проверки."
    )


# ============================================================================
# KEY STATUS CACHE ENDPOINTS
# ============================================================================

@router.get("/keys/status/batch")
async def get_keys_status_batch(
    current_user: dict = Depends(get_current_user),
    force_refresh: bool = False
):
    """
    Получение статуса всех ключей с кэшированием
    
    Кэширует результаты тестов на 5 минут, чтобы не дёргать API каждый раз.
    
    Args:
        force_refresh: Если True — игнорирует кэш и делает проверку заново
    """
    from runtime.provider_manager import get_provider_manager
    from core.encryption import get_encryptor

    user_id = current_user["id"]
    cache = get_cache_manager()
    cache_key = f"keys_status:{user_id}"
    
    # Проверяем кэш
    if not force_refresh:
        cached_result = await cache.get(cache_key)
        if cached_result:
            logger.info(f"📦 Cache hit for keys_status:{user_id}")
            return cached_result
    
    logger.info(f"🔄 Fetching fresh keys status for user:{user_id}")
    
    supabase = get_db_client(current_user)
    if not supabase:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    encryptor = get_encryptor()

    # Получаем список ключей
    result = supabase.table("user_api_keys")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("is_active", True)\
        .execute()

    if not result.data:
        keys_status = []
    else:
        pm = get_provider_manager()
        keys_status = []
        
        # Тестируем каждый ключ (без блокировки, параллельно)
        for key in result.data:
            if key["id"] == "system-gigachat":
                # Системный ключ — всегда успешен
                keys_status.append({
                    "key_id": "system-gigachat",
                    "provider": key["provider"],
                    "status": "success",
                    "message": "Системный ключ",
                    "last_checked": datetime.now().isoformat(),
                    "cached": False
                })
                continue
            
            try:
                api_key = encryptor.decrypt(key["api_key_encrypted"])
                provider = key["provider"]
                model = key.get("model_preference")
                
                if not model:
                    keys_status.append({
                        "key_id": key["id"],
                        "provider": provider,
                        "status": "error",
                        "message": "Модель не указана",
                        "last_checked": datetime.now().isoformat(),
                        "cached": False
                    })
                    continue
                
                # Тестируем подключение
                test_result = await pm.test_connection(
                    api_key=api_key,
                    provider=provider,
                    model=model,
                )
                
                keys_status.append({
                    "key_id": key["id"],
                    "provider": provider,
                    "status": "success" if test_result["success"] else "error",
                    "message": test_result["message"],
                    "model_tested": test_result.get("model_tested"),
                    "last_checked": datetime.now().isoformat(),
                    "cached": False
                })
                
            except Exception as e:
                keys_status.append({
                    "key_id": key["id"],
                    "provider": key["provider"],
                    "status": "error",
                    "message": str(e),
                    "last_checked": datetime.now().isoformat(),
                    "cached": False
                })
    
    # Сохраняем в кэш на 5 минут
    cache_result = {
        "keys": keys_status,
        "total": len(keys_status),
        "timestamp": datetime.now().isoformat(),
    }
    
    await cache.set(cache_key, cache_result, ttl=300)  # 5 минут
    
    return cache_result


@router.post("/keys/status/{key_id}/refresh")
async def refresh_key_status(
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Принудительное обновление статуса одного ключа
    
    Сбрасывает кэш и делает новую проверку.
    """
    from runtime.provider_manager import get_provider_manager
    from core.encryption import get_encryptor

    user_id = current_user["id"]
    supabase = get_db_client(current_user)
    if not supabase:
        raise HTTPException(status_code=500, detail="БД не подключена")

    encryptor = get_encryptor()
    
    # Получаем ключ
    key_result = supabase.table("user_api_keys")\
        .select("*")\
        .eq("id", key_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not key_result.data:
        raise HTTPException(status_code=404, detail="Ключ не найден")
    
    key_data = key_result.data[0]
    
    if key_id == "system-gigachat":
        return {
            "key_id": key_id,
            "provider": "gigachat",
            "status": "success",
            "message": "Системный ключ",
            "last_checked": datetime.now().isoformat()
        }
    
    try:
        api_key = encryptor.decrypt(key_data["api_key_encrypted"])
        provider = key_data["provider"]
        model = key_data.get("model_preference")
        
        if not model:
            return {
                "key_id": key_id,
                "provider": provider,
                "status": "error",
                "message": "Модель не указана",
                "last_checked": datetime.now().isoformat()
            }
        
        pm = get_provider_manager()
        test_result = await pm.test_connection(
            api_key=api_key,
            provider=provider,
            model=model,
        )
        
        # Сбрасываем кэш для всех ключей пользователя
        cache = get_cache_manager()
        await cache.delete(f"keys_status:{user_id}")
        
        return {
            "key_id": key_id,
            "provider": provider,
            "status": "success" if test_result["success"] else "error",
            "message": test_result["message"],
            "model_tested": test_result.get("model_tested"),
            "last_checked": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "key_id": key_id,
            "provider": key_data["provider"],
            "status": "error",
            "message": str(e),
            "last_checked": datetime.now().isoformat()
        }


# ============================================================================
# CHAT ENDPOINTS
# ============================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Чат с AI с автоматическим определением быстрого/медленного режима
    """
    from runtime.provider_manager import get_provider_manager
    from core.pipeline import get_pipeline

    supabase = get_db_client(current_user)
    if not supabase:
        raise HTTPException(status_code=500, detail="БД не подключена")

    encryptor = get_encryptor()
    user_id = current_user["id"]

    # Определяем какой ключ использовать
    api_key = None
    model = "auto"
    provider = None

    logger.info(f"?? Chat request: key_id={request.key_id}, model={request.model}, provider={request.provider}")

    if request.key_id:
        # Конкретный ключ
        logger.info(f"?? Looking up key_id: {request.key_id}")
        result = supabase.table("user_api_keys")\
            .select("*")\
            .eq("id", request.key_id)\
            .eq("user_id", user_id)\
            .execute()

        if result.data:
            key_data = result.data[0]
            logger.info(f"? Key found: provider={key_data['provider']}, model={key_data.get('model_preference')}, is_default={key_data.get('is_default')}")
            api_key = encryptor.decrypt(key_data["api_key_encrypted"])
            provider = key_data["provider"]  # ВСЕГДА из БД, не от фронтенда
            model = key_data.get("model_preference") or "auto"
        else:
            logger.warning(f"?? Key {request.key_id} not found for user {user_id}, falling back to default")
    else:
        logger.info("?? No key_id provided, using default key")

    if not api_key:
        # Ключ по умолчанию
        result = supabase.table("user_api_keys")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("is_default", True)\
            .eq("is_active", True)\
            .execute()

        if result.data:
            key_data = result.data[0]
            logger.info(f"? Default key found: provider={key_data['provider']}, model={key_data.get('model_preference')}")
            api_key = encryptor.decrypt(key_data["api_key_encrypted"])
            provider = key_data["provider"]  # ВСЕГДА из БД
            model = key_data.get("model_preference") or "auto"

    if not api_key:
        # Нет ключа у пользователя — ошибка!
        logger.error("? No API key found for user")
        raise HTTPException(
            status_code=400,
            detail="API ключ не настроен. Добавьте ключ в настройках."
        )

    logger.info(f"?? Using: provider={provider}, model={model}")

    # === ИСПОЛЬЗУЕМ ProviderManager ===
    pm = get_provider_manager()

    # === ПРОВЕРКА RATE LIMIT ===
    cache = get_cache_manager()
    is_limited, remaining = await cache.is_rate_limited(
        key=f"chat:{user_id}",
        limit=10,
        window=60
    )
    
    if is_limited:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many requests. Maximum 10 requests per minute.",
                "retry_after": 60
            }
        )

    # === ПОЛНЫЙ PIPELINE ===
    # Все запросы идут через полную систему (Pipeline)
    try:
            # === ФАЗА 1: ПЕРЕДАЁМ API КЛЮЧ В PIPELINE ===
            try:
                pipeline = get_pipeline()
                result = await pipeline.execute(
                    user_message=request.text,
                    context={"user_id": user_id, "key_id": request.key_id},
                    api_key=api_key,        # === ФАЗА 1: Передаём ключ ===
                    provider=provider       # === ФАЗА 1: Передаём провайдера ===
                )
            except Exception as pipeline_error:
                logger.error(f"? Pipeline execution failed: {pipeline_error}")
                # Fallback: если пайплайн упал - используем быстрый режим напрямую через ProviderManager
                provider_result = await pm.generate(
                    prompt=request.text,
                    system_prompt="Вы полезный ассистент PAD+ AI.",
                    api_key=api_key,
                    model=model,
                    provider=provider
                )
                response = provider_result.response
                
                # Обновляем last_used_at у ключа
                if request.key_id:
                    get_db_client(current_user).table("user_api_keys").update({
                        "last_used_at": datetime.now().isoformat()
                    }).eq("id", request.key_id).execute()
                
                return ChatResponse(
                    text=response.text,
                    model=response.model,
                    provider=response.provider,
                    usage=response.usage,
                    finish_reason=response.finish_reason,
                    timestamp=datetime.now().isoformat(),
                    is_fast_mode=True,
                    confidence=0.7,
                    truth_confidence=0.6,
                    meta={
                        "fallback_used": provider_result.fallback_used,
                        "fallback_from": provider_result.fallback_from,
                        "fallback_to": provider_result.fallback_to,
                    } if provider_result.fallback_used else None,
                )
            
            # Обновляем last_used_at у ключа
            if request.key_id:
                get_db_client(current_user).table("user_api_keys").update({
                    "last_used_at": datetime.now().isoformat()
                }).eq("id", request.key_id).execute()
            
            # Определяем финальный provider (может отличаться при fallback)
            if hasattr(result, 'provider'):
                final_provider = result.provider
                final_model = getattr(result, 'model', model)
            elif isinstance(result, dict):
                final_provider = result.get("provider", provider)
                final_model = result.get("model", model)
            else:
                final_provider = provider
                final_model = model
            
            # === СОХРАНЕНИЕ ДИАЛОГА И СООБЩЕНИЙ ===
            dialog_id = request.dialog_id

            try:
                if request.dialog_id:
                    # Обновляем существующий диалог
                    try:
                        current = supabase.table("dialogs").select("message_count").eq("id", dialog_id).execute()
                        current_count = current.data[0].get("message_count", 0) if current.data else 0
                        supabase.table("dialogs").update({
                            "message_count": current_count + 2,
                            "last_message_at": datetime.now().isoformat()
                        }).eq("id", dialog_id).execute()
                    except Exception as count_err:
                        supabase.table("dialogs").update({
                            "last_message_at": datetime.now().isoformat()
                        }).eq("id", dialog_id).execute()
                else:
                    # Создаем новый диалог
                    dialog_result = supabase.table("dialogs").insert({
                        "user_id": user_id,
                        "title": request.text[:100],
                        "message_count": 2,
                        "last_message_at": datetime.now().isoformat()
                    }).execute()

                    if dialog_result.data:
                        dialog_id = dialog_result.data[0]["id"]

                if dialog_id:
                    svc = get_supabase_service()
                    svc.table("messages").insert({
                        "dialog_id": dialog_id,
                        "role": "user",
                        "content": request.text,
                        "model": final_model,
                        "provider": final_provider,
                        "created_at": datetime.now().isoformat()
                    }).execute()

                    svc.table("messages").insert({
                        "dialog_id": dialog_id,
                        "role": "assistant",
                        "content": result.response if hasattr(result, 'response') else str(result),
                        "model": final_model,
                        "provider": final_provider,
                        "created_at": datetime.now().isoformat()
                    }).execute()
            except Exception as e:
                msg = str(e)[:200]
                logger.error(f"Не удалось сохранить диалог: {msg}")
                # Не прерываем чат, но логируем
            
            # === COGNITIVE UX LAYER: Преобразуем результат в полный формат ===
            try:
                if hasattr(result, 'to_dict'):
                    result_dict = result.to_dict(explain=request.explain)
                else:
                    result_dict = {
                        "answer": str(result.response) if hasattr(result, 'response') else str(result),
                        "cognitive": None,
                        "memory": None,
                        "emotion": None,
                        "meta": None,
                        "safety": None,
                        "truth": None,
                        "xray": None
                    }

                # Сохраняем в X-Ray
                try:
                    from api.xray_routes import set_latest_pipeline_result
                    set_latest_pipeline_result({
                        "timestamp": datetime.now().isoformat(),
                        "user_message": request.text[:200],
                        "result": result_dict,
                        "provider": final_provider,
                        "model": final_model,
                        "pipeline": {
                            "response": result.response[:500] if hasattr(result, 'response') else "",
                            "strategy": getattr(result, 'strategy', 'unknown'),
                            "intent": getattr(result, 'intent', 'unknown'),
                            "confidence": getattr(result, 'confidence', 0),
                            "truth_confidence": getattr(result, 'truth_confidence', 0),
                        }
                    })
                except Exception as xray_err:
                    logger.debug(f"X-Ray save: {xray_err}")
            except Exception as e:
                logger.warning(f"?? Не удалось преобразовать результат pipeline: {e}")
                result_dict = {
                    "answer": str(result.response) if hasattr(result, 'response') else str(result),
                    "cognitive": None,
                    "memory": None,
                    "emotion": None,
                    "meta": None,
                    "safety": None,
                    "truth": None,
                    "xray": None
                }
            
            return ChatResponse(
                text=result_dict.get("answer", result.response if hasattr(result, 'response') else str(result)),
                model=final_model,
                provider=final_provider,
                usage={"total_tokens": 0},
                finish_reason="stop",
                timestamp=datetime.now().isoformat(),
                dialog_id=dialog_id,
                cognitive=result_dict.get("cognitive"),
                memory=result_dict.get("memory"),
                emotion=result_dict.get("emotion"),
                meta=result_dict.get("meta"),
                safety=result_dict.get("safety"),
                truth=result_dict.get("truth"),
                xray=result_dict.get("xray"),
                confidence=result.confidence if hasattr(result, 'confidence') else 0.8,
                truth_confidence=result.truth_confidence if hasattr(result, 'truth_confidence') else 0.7,
                rag_used=result.rag_used if hasattr(result, 'rag_used') else False,
                facts_used=result.facts_used if hasattr(result, 'facts_used') else 0,
                is_fast_mode=False
            )

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {str(e)}")


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@router.get("/mind-state")
async def get_mind_state():
    """Полное состояние системы для dashboard"""
    state = {
        "emotion": {},
        "memory": {},
        "knowledge": {},
        "autonomy": {},
        "health": {},
        "pipeline": {}
    }
    
    try:
        from emotion.pad_model import get_pad_model
        pad = get_pad_model()
        state["emotion"] = pad.get_state().to_dict()
    except Exception as e:
        logger.warning(f"Endpoint error: {type(e).__name__}: {e}")
    
    # === MEMORY SYSTEMS ===
    try:
        from memory.rag import get_rag
        rag = get_rag()
        state["memory"]["rag"] = rag.get_stats()
    except Exception as e:
        logger.warning(f"RAG stats error: {type(e).__name__}: {e}")
        state["memory"]["rag"] = {"total_dialogs": 0}
    
    try:
        from memory.episodic import get_episodic_memory
        episodic = get_episodic_memory()
        ep_stats = episodic.get_stats()
        state["memory"]["episodic"] = {
            "total_episodes": ep_stats.get("total_episodes", 0)
        }
    except Exception as e:
        logger.warning(f"Episodic stats error: {type(e).__name__}: {e}")
        state["memory"]["episodic"] = {"total_episodes": 0}
    
    try:
        from memory.semantic import get_semantic_memory
        semantic = get_semantic_memory()
        sem_stats = semantic.get_stats()
        state["memory"]["semantic"] = {
            "total_knowledge": sem_stats.get("total_knowledge", 0)
        }
    except Exception as e:
        logger.warning(f"Semantic stats error: {type(e).__name__}: {e}")
        state["memory"]["semantic"] = {"total_knowledge": 0}
    
    # Факты теперь интегрированы в RAG, статистика не требуется
    state["memory"]["fact"] = {"total_facts": 0}
    
    try:
        from memory.roots import get_roots_memory
        roots = get_roots_memory()
        roots_stats = roots.get_stats()
        state["memory"]["roots"] = {
            "total_roots": roots_stats.get("total_roots", 0)
        }
    except Exception as e:
        logger.warning(f"Roots stats error: {type(e).__name__}: {e}")
        state["memory"]["roots"] = {"total_roots": 0}
    
    try:
        from knowledge.graph import get_knowledge_graph
        graph = get_knowledge_graph()
        state["knowledge"] = graph.get_stats()
    except Exception as e:
        logger.warning(f"Knowledge graph stats error: {type(e).__name__}: {e}")
        state["knowledge"] = {"nodes": 0, "edges": 0, "avg_confidence": 0}
    
    try:
        from core.safety_layer import get_safety_layer
        safety = get_safety_layer()
        state["safety"] = safety.get_stats()
    except Exception as e:
        logger.warning(f"Safety stats error: {type(e).__name__}: {e}")
    
    try:
        from core.health_monitor import get_health_monitor
        health = get_health_monitor()
        state["health"] = health.assess_health()
    except Exception as e:
        logger.warning(f"Health monitor error: {type(e).__name__}: {e}")
    
    try:
        from core.pipeline import get_pipeline
        pipeline = get_pipeline()
        state["pipeline"] = pipeline.get_stats()
    except Exception as e:
        logger.warning(f"Pipeline stats error: {type(e).__name__}: {e}")
    
    return state


@router.get("/events/recent")
async def get_recent_events(limit: int = 50):
    """История недавних событий для логов"""
    try:
        from core.event_bus import get_event_bus
        bus = get_event_bus()
        events = bus.get_history(limit)
        return {"events": events}
    except Exception as e:
        return {"events": [], "error": str(e)}


@router.get("/metrics/activity")
async def get_activity_metrics(hours: int = 24):
    """Метрики активности для графиков"""
    try:
        from analytics.metrics import get_metrics
        metrics = get_metrics()
        activity_data = metrics.get_activity_data(hours)
        last_hour_requests = 0

        if activity_data.get("dialogs_per_hour"):
            last_count = activity_data["dialogs_per_hour"][-1].get("count", 0)
            last_hour_requests = round(last_count / 60, 1)

        activity_data["requests_per_minute"] = last_hour_requests
        return activity_data
    except Exception as e:
        logger.warning(f"Activity metrics unavailable: {e}")
        return {
            "dialogs_per_hour": [],
            "requests_per_minute": 0,
            "avg_confidence": [],
            "emotion_history": []
        }


@router.get("/metrics/system")
async def get_system_metrics():
    """Системные метрики для dashboard"""
    try:
        import psutil
        cpu = round(psutil.cpu_percent(interval=0.1), 1)
        mem = round(psutil.virtual_memory().percent, 1)
        disk = round(psutil.disk_io_counters().read_bytes / 1024 / 1024, 1) if psutil.disk_io_counters() else 0
    except Exception:
        cpu = 0
        mem = 0
        disk = 0

    return {
        "cpu_usage": cpu,
        "memory_usage": mem,
        "disk_io": disk,
        "network_latency": 0,
        "active_connections": 0,
        "active_sessions": 0,
        "cache_hit_rate": 0,
        "max_connections": 1000,
    }


@router.get("/system/full-status")
async def get_full_system_status():
    """
    Полный статус всех систем PAD+ AI
    
    Агрегирует данные из:
    - Emotion (PAD model)
    - Memory systems (RAG, episodic, semantic, facts, persona)
    - Cognitive systems (pipeline, truth loop, safety)
    - Infrastructure (cache, sessions, events, websocket)
    """
    from datetime import datetime
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "version": "3.5.0",
        
        "emotion": {},
        "memory": {
            "rag": {},
            "episodic": {},
            "semantic": {},
            "facts": {"total_facts": 0, "verification_rate": 0.0},
            "persona": {}
        },
        "knowledge": {},
        "cognitive": {
            "pipeline": {},
            "truth_loop": {},
            "safety": {}
        },
        "health": {},
        "infrastructure": {
            "cache": {},
            "sessions": {},
            "events": {},
            "websocket": {}
        }
    }
    
    # === EMOTION SYSTEM ===
    try:
        from emotion.pad_model import get_pad_model
        pad = get_pad_model()
        status["emotion"] = pad.get_state().to_dict()
    except Exception:
        status["emotion"] = {"status": "unavailable"}
    
    # === MEMORY SYSTEMS ===
    try:
        from memory.rag import get_rag
        rag = get_rag()
        rag_stats = rag.get_stats() if hasattr(rag, 'get_stats') else {}
        status["memory"]["rag"] = {
            "documents": rag_stats.get("total_documents", 0),
            "collections": rag_stats.get("collections", 0),
        }
    except Exception:
        status["memory"]["rag"] = {"status": "unavailable"}
    
    try:
        from memory.episodic import get_episodic_memory
        episodic = get_episodic_memory()
        ep_stats = episodic.get_stats() if hasattr(episodic, 'get_stats') else {}
        status["memory"]["episodic"] = {
            "dialogs": ep_stats.get("total_dialogs", 0),
            "entries": ep_stats.get("total_entries", 0),
        }
    except Exception:
        status["memory"]["episodic"] = {"status": "unavailable"}
    
    try:
        from memory.semantic import get_semantic_memory
        semantic = get_semantic_memory()
        sem_stats = semantic.get_stats() if hasattr(semantic, 'get_stats') else {}
        status["memory"]["semantic"] = {
            "concepts": sem_stats.get("total_concepts", 0),
            "connections": sem_stats.get("total_connections", 0)
        }
    except Exception:
        status["memory"]["semantic"] = {"status": "unavailable"}
    
    try:
        from memory.persona import get_persona
        persona = get_persona()
        pers_stats = persona.get_stats() if hasattr(persona, 'get_stats') else {}
        status["memory"]["persona"] = {
            "traits": pers_stats.get("traits_count", 0),
            "consistency": 0,
            "adaptations": 0
        }
    except Exception:
        status["memory"]["persona"] = {"status": "unavailable"}
    
    # === KNOWLEDGE SYSTEM ===
    try:
        from knowledge.graph import get_knowledge_graph
        graph = get_knowledge_graph()
        graph_stats = graph.get_stats() if hasattr(graph, 'get_stats') else {}
        status["knowledge"] = {
            "entities": graph_stats.get("total_entities", 0),
            "relations": graph_stats.get("total_relations", 0),
            "graphs": graph_stats.get("graphs_count", 0)
        }
    except Exception:
        status["knowledge"] = {"status": "unavailable"}
    
    # === COGNITIVE SYSTEMS ===
    try:
        from core.pipeline import get_pipeline
        pipeline = get_pipeline()
        pipe_stats = pipeline.get_stats() if hasattr(pipeline, 'get_stats') else {}
        status["cognitive"]["pipeline"] = {
            "processed_today": pipe_stats.get("processed_today", 0),
            "avg_processing_time_sec": 0,
            "error_rate": 0,
        }
    except Exception:
        status["cognitive"]["pipeline"] = {"status": "unavailable"}
    
    try:
        from core.truth_loop import get_truth_loop
        truth = get_truth_loop()
        truth_stats = truth.get_stats() if hasattr(truth, 'get_stats') else {}
        status["cognitive"]["truth_loop"] = {
            "facts_checked_today": truth_stats.get("facts_checked_today", 0),
            "accuracy": 0,
            "corrections": 0
        }
    except Exception:
        status["cognitive"]["truth_loop"] = {"status": "unavailable"}
    
    try:
        from core.safety_layer import get_safety_layer
        safety = get_safety_layer()
        safety_stats = safety.get_stats() if hasattr(safety, 'get_stats') else {}
        status["cognitive"]["safety"] = {
            "blocked_today": safety_stats.get("blocked_today", 0),
            "threats_detected": safety_stats.get("threats_detected", 0),
            "false_positive_rate": 0
        }
    except Exception:
        status["cognitive"]["safety"] = {"status": "unavailable"}
    
    # === HEALTH MONITOR ===
    try:
        from core.health_monitor import get_health_monitor
        health = get_health_monitor()
        health_data = health.assess_health()
        status["health"] = health_data
    except Exception:
        status["health"] = {"status": "unavailable"}
    
    # === INFRASTRUCTURE ===
    try:
        from core.cache_manager import get_cache_manager
        cache = get_cache_manager()
        cache_stats = cache.get_stats() if hasattr(cache, 'get_stats') else {}
        status["infrastructure"]["cache"] = {
            "hit_rate": cache_stats.get("hit_rate", 0),
            "size_mb": cache_stats.get("size_mb", 0),
            "entries": cache_stats.get("entries", 0)
        }
    except Exception:
        status["infrastructure"]["cache"] = {"status": "unavailable"}
    
    try:
        from core.session_manager import get_session_manager
        sessions = get_session_manager()
        sess_stats = sessions.get_stats() if hasattr(sessions, 'get_stats') else {}
        status["infrastructure"]["sessions"] = {
            "active": sess_stats.get("active", 0),
            "total_today": sess_stats.get("total_today", 0),
        }
    except Exception:
        status["infrastructure"]["sessions"] = {"status": "unavailable"}
    
    try:
        from core.event_bus import get_event_bus
        events = get_event_bus()
        ev_stats = events.get_stats() if hasattr(events, 'get_stats') else {}
        status["infrastructure"]["events"] = {
            "queue_size": ev_stats.get("queue_size", 0),
            "processed_today": ev_stats.get("processed_today", 0),
            "errors_today": ev_stats.get("errors_today", 0)
        }
    except Exception:
        status["infrastructure"]["events"] = {"status": "unavailable"}
    
    try:
        from core.websocket_manager import get_websocket_manager
        ws = get_websocket_manager()
        ws_stats = ws.get_stats() if hasattr(ws, 'get_stats') else {}
        status["infrastructure"]["websocket"] = {
            "active_connections": ws_stats.get("active_connections", 0),
            "total_today": ws_stats.get("total_today", 0),
            "errors_today": ws_stats.get("errors_today", 0)
        }
    except Exception:
        status["infrastructure"]["websocket"] = {"status": "unavailable"}
    
    return status


# ============================================================================
# STREAMING CHAT ENDPOINT
# ============================================================================

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Потоковый чат с AI (SSE - Server Sent Events)
    """
    from runtime.provider_manager import get_provider_manager

    supabase = get_db_client(current_user)
    if not supabase:
        raise HTTPException(status_code=500, detail="БД не подключена")
    encryptor = get_encryptor()
    user_id = current_user["id"]

    # Определяем какой ключ использовать
    api_key = None
    model = "auto"
    provider = None

    if request.key_id:
        logger.info(f"?? Stream: looking up key_id={request.key_id}")
        key_result = supabase.table("user_api_keys")\
            .select("*")\
            .eq("id", request.key_id)\
            .eq("user_id", user_id)\
            .execute()

        if key_result.data:
            key_data = key_result.data[0]
            enc_len = len(key_data.get("api_key_encrypted", ""))
            logger.info(f"?? Stream: encrypted_len={enc_len}")
            api_key = encryptor.decrypt(key_data["api_key_encrypted"])
            logger.info(f"?? Stream: decrypted_len={len(api_key)}")
            provider = key_data["provider"]
            model = key_data.get("model_preference") or "auto"
    else:
        key_result = supabase.table("user_api_keys")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("is_default", True)\
            .eq("is_active", True)\
            .execute()

        if key_result.data:
            key_data = key_result.data[0]
            api_key = encryptor.decrypt(key_data["api_key_encrypted"])
            provider = key_data["provider"]  # ВСЕГДА из БД
            model = key_data.get("model_preference") or "auto"

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="API ключ не настроен. Добавьте ключ в настройках."
        )

    async def generate():
        try:
            pm = get_provider_manager()

            async for chunk in pm.generate_stream(
                prompt=request.text,
                system_prompt="Вы полезный ассистент PAD+ AI.",
                api_key=api_key,
                model=model,
                provider=provider  # Передаём provider, fallback внутри
            ):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            try:
                safe_err = str(e).encode("ascii", errors="replace").decode("ascii")
            except Exception:
                safe_err = "Провайдер недоступен (ошибка кодировки)"
            yield f"data: {json.dumps({'error': safe_err})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def frontend_health():
    """Проверка здоровья frontend API"""
    db_connected = check_database_connection()
    
    return {
        "status": "healthy",
        "database": "connected" if db_connected else "disconnected",
        "encryption": "enabled" if os.getenv("ENCRYPTION_KEY") else "disabled",
        "auth": "supabase"
    }


@router.get("/models")
async def list_models(provider: Optional[str] = None):
    """
    Список всех доступных моделей
    
    Args:
        provider: Опциональный фильтр по провайдеру
    """
    from runtime.llm_service import get_llm_service
    
    llm = get_llm_service()
    models = llm.get_available_models(provider)
    return {"models": models}


@router.get("/settings")
async def get_settings(current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    user_id = current_user["id"]
    result = supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
    if not result.data:
        return {
            "persona": {"tone": "friendly", "detail_level": "moderate", "emotion_level": "balanced", "specialization": "general"},
            "notifications": {"email": True, "push": False, "sound": True, "frequency": "immediate"},
            "appearance": {"theme": "dark", "font_size": "medium", "compact_mode": False}
        }
    s = result.data[0]
    return {
        "persona": {"tone": s.get("persona_tone"), "detail_level": s.get("persona_detail_level"), "emotion_level": s.get("persona_emotion_level"), "specialization": s.get("persona_specialization")},
        "notifications": {"email": s.get("notification_email"), "push": s.get("notification_push"), "sound": s.get("notification_sound"), "frequency": s.get("notification_frequency")},
        "appearance": {"theme": s.get("theme"), "font_size": s.get("font_size"), "compact_mode": s.get("compact_mode")}
    }


@router.patch("/settings")
async def update_settings(data: dict, current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    user_id = current_user["id"]
    settings_update = {}
    for section, values in data.items():
        if section == "persona":
            settings_update["persona_tone"] = values.get("tone")
            settings_update["persona_detail_level"] = values.get("detail_level")
            settings_update["persona_emotion_level"] = values.get("emotion_level")
            settings_update["persona_specialization"] = values.get("specialization")
        elif section == "notifications":
            settings_update["notification_email"] = values.get("email")
            settings_update["notification_push"] = values.get("push")
            settings_update["notification_sound"] = values.get("sound")
            settings_update["notification_frequency"] = values.get("frequency")
        elif section == "appearance":
            settings_update["theme"] = values.get("theme")
            settings_update["font_size"] = values.get("font_size")
            settings_update["compact_mode"] = values.get("compact_mode")
    if settings_update:
        existing = supabase.table("user_settings").select("id").eq("user_id", user_id).execute()
        if existing.data:
            supabase.table("user_settings").update(settings_update).eq("user_id", user_id).execute()
        else:
            settings_update["user_id"] = user_id
            supabase.table("user_settings").insert(settings_update).execute()
    return {"status": "ok"}



@router.get("/providers/{provider_id}/models")
async def list_provider_models(provider_id: str, current_user: dict = Depends(get_current_user)):
    """
    Список моделей конкретного провайдера — загружает АКТУАЛЬНЫЕ модели через LLMService
    """
    from runtime.llm_service import get_llm_service
    from core.encryption import get_encryptor

    supabase = get_db_client(current_user)
    if not supabase:
        raise HTTPException(status_code=500, detail="БД не подключена")
    user_id = current_user["id"]
    encryptor = get_encryptor()

    # Получаем API ключ пользователя для этого провайдера
    result = supabase.table("user_api_keys")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("provider", provider_id)\
        .eq("is_active", True)\
        .execute()

    api_key = None
    if result.data:
        api_key = encryptor.decrypt(result.data[0]["api_key_encrypted"])

    llm_service = get_llm_service()

    # Для OpenRouter пытаемся загрузить актуальные модели из API (если есть ключ)
    models = []
    if provider_id == "openrouter" and api_key:
        try:
            live_models = await llm_service.fetch_openrouter_models()
            if live_models:
                models = live_models
                logger.info(f"Загружено {len(models)} моделей из OpenRouter API")
        except Exception as e:
            logger.warning(f"Не удалось загрузить модели OpenRouter: {e}")

    # Если живые модели не загрузились — используем статический список
    if not models:
        models = llm_service.get_available_models(provider_id)
        logger.info(f"Используется статический список: {len(models)} моделей")

    # Добавляем Auto в начало списка
    auto_entry = {"id": f"{provider_id}/auto", "name": "Auto", "max_tokens": 128000, "supports_vision": True, "supports_function_calling": True, "cost": "auto", "provider": provider_id}
    models.insert(0, auto_entry)

    # Фильтруем дубликаты Auto
    seen = set()
    unique = []
    for m in models:
        if m["id"] not in seen:
            seen.add(m["id"])
            unique.append(m)

    return {"models": unique}



