"""
API Routes для управления пользователем и настройками

Эндпоинты:
- GET /api/v1/user/profile - Получить профиль
- PATCH /api/v1/user/profile - Обновить профиль
- PATCH /api/v1/user/password - Сменить пароль
- GET /api/v1/user/persona - Получить настройки persona
- PATCH /api/v1/user/persona - Обновить настройки persona
- POST /api/v1/user/avatar - Загрузить аватар
- DELETE /api/v1/user/avatar - Удалить аватар
"""

from fastapi import APIRouter, HTTPException, Depends, Header, UploadFile, File, Form
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import logging
import uuid

logger = logging.getLogger("padplus")

from core.supabase_client import get_supabase

router = APIRouter(prefix="/api/v1/user", tags=["User Management"])


# ============================================================================
# МОДЕЛИ ДАННЫХ
# ============================================================================

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class PersonaSettings(BaseModel):
    tone: Optional[str] = None  # friendly, serious, neutral
    detail_level: Optional[str] = None  # brief, moderate, detailed
    emotion_level: Optional[str] = None  # restrained, balanced, expressive
    specialization: Optional[str] = None  # general, technical, creative


class NotificationSettings(BaseModel):
    email: Optional[bool] = None
    push: Optional[bool] = None
    sound: Optional[bool] = None
    frequency: Optional[str] = None  # immediate, hourly, daily


class AppearanceSettings(BaseModel):
    theme: Optional[str] = None  # dark, light, auto
    font_size: Optional[str] = None  # small, medium, large
    compact_mode: Optional[bool] = None


class UserSettingsResponse(BaseModel):
    persona: dict
    notifications: dict
    appearance: dict


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

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


# ============================================================================
# PROFILE ENDPOINTS
# ============================================================================

@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Получение информации о профиле пользователя"""
    profile = current_user.get("profile")
    
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    
    return {
        "id": profile["id"],
        "email": profile["email"],
        "full_name": profile.get("full_name"),
        "avatar_url": profile.get("avatar_url"),
        "created_at": profile.get("created_at"),
        "email_verified": profile.get("email_verified", False)
    }


@router.patch("/profile")
async def update_profile(
    data: UserProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Обновление профиля пользователя"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    update_data = {}
    
    # Обновляем email через Supabase Auth
    if data.email and data.email != current_user["email"]:
        try:
            supabase.auth.update_user({"email": data.email})
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка обновления email: {str(e)}")
    
    # Обновляем full_name в профиле
    if data.full_name is not None:
        update_data["full_name"] = data.full_name
    
    if update_data:
        result = supabase.table("users")\
            .update(update_data)\
            .eq("id", user_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Профиль не найден")
    
    return {"success": True, "message": "Профиль обновлёn"}


@router.patch("/password")
async def change_password(
    data: PasswordChange,
    current_user: dict = Depends(get_current_user)
):
    """Смена пароля пользователя"""
    supabase = get_supabase()
    
    try:
        # Сначала пробуем войти с текущим паролем для проверки
        supabase.auth.sign_in_with_password({
            "email": current_user["email"],
            "password": data.current_password
        })
        
        # Если успешно - обновляем пароль
        supabase.auth.update_user({"password": data.new_password})
        
        return {"success": True, "message": "Пароль изменён"}
        
    except Exception as e:
        if "Invalid login credentials" in str(e):
            raise HTTPException(status_code=400, detail="Неверный текущий пароль")
        raise HTTPException(status_code=500, detail=f"Ошибка смены пароля: {str(e)}")


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Загрузка аватара пользователя"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Проверяем тип файла
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Недопустимый тип файла")
    
    # Проверяем размер (макс 5MB)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс 5MB)")
    
    try:
        # Загружаем в Supabase Storage
        file_extension = file.filename.split(".")[-1]
        file_path = f"avatars/{user_id}.{file_extension}"
        
        supabase.storage.from_("avatars")\
            .upload(file_path, content, {"content-type": file.content_type})
        
        # Получаем публичную ссылку
        avatar_url = supabase.storage.from_("avatars").get_public_url(file_path)
        
        # Обновляем профиль
        supabase.table("users")\
            .update({"avatar_url": avatar_url})\
            .eq("id", user_id)\
            .execute()
        
        return {"success": True, "avatar_url": avatar_url}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки аватара: {str(e)}")


@router.delete("/avatar")
async def delete_avatar(current_user: dict = Depends(get_current_user)):
    """Удаление аватара пользователя"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    try:
        # Удаляем файл из хранилища
        file_path = f"avatars/{user_id}"
        supabase.storage.from_("avatars").remove([file_path])
        
        # Обновляем профиль
        supabase.table("users")\
            .update({"avatar_url": None})\
            .eq("id", user_id)\
            .execute()
        
        return {"success": True, "message": "Аватар удалён"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления аватара: {str(e)}")


# ============================================================================
# PERSONA SETTINGS ENDPOINTS
# ============================================================================

@router.get("/persona")
async def get_persona_settings(current_user: dict = Depends(get_current_user)):
    """Получение настроек persona"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    result = supabase.table("user_settings")\
        .select("persona_tone, persona_detail_level, persona_emotion_level, persona_specialization")\
        .eq("user_id", user_id)\
        .execute()
    
    if not result.data:
        # Возвращаем настройки по умолчанию
        return {
            "tone": "friendly",
            "detail_level": "moderate",
            "emotion_level": "balanced",
            "specialization": "general"
        }
    
    settings = result.data[0]
    return {
        "tone": settings.get("persona_tone", "friendly"),
        "detail_level": settings.get("persona_detail_level", "moderate"),
        "emotion_level": settings.get("persona_emotion_level", "balanced"),
        "specialization": settings.get("persona_specialization", "general")
    }


@router.patch("/persona")
async def update_persona_settings(
    data: PersonaSettings,
    current_user: dict = Depends(get_current_user)
):
    """Обновление настроек persona"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    update_data = {}
    if data.tone is not None:
        update_data["persona_tone"] = data.tone
    if data.detail_level is not None:
        update_data["persona_detail_level"] = data.detail_level
    if data.emotion_level is not None:
        update_data["persona_emotion_level"] = data.emotion_level
    if data.specialization is not None:
        update_data["persona_specialization"] = data.specialization
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")
    
    # Проверяем, есть ли уже настройки
    existing = supabase.table("user_settings")\
        .select("id")\
        .eq("user_id", user_id)\
        .execute()
    
    if existing.data:
        # Обновляем существующие
        result = supabase.table("user_settings")\
            .update(update_data)\
            .eq("user_id", user_id)\
            .execute()
    else:
        # Создаём новые
        update_data["user_id"] = user_id
        result = supabase.table("user_settings")\
            .insert(update_data)\
            .execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Ошибка сохранения настроеk")
    
    return {"success": True, "message": "Настройки persona обновлены"}


# ============================================================================
# NOTIFICATION SETTINGS ENDPOINTS
# ============================================================================

@router.get("/notifications")
async def get_notification_settings(current_user: dict = Depends(get_current_user)):
    """Получение настроеk уведомлений"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    result = supabase.table("user_settings")\
        .select("notification_email, notification_push, notification_sound, notification_frequency")\
        .eq("user_id", user_id)\
        .execute()
    
    if not result.data:
        return {
            "email": True,
            "push": False,
            "sound": True,
            "frequency": "immediate"
        }
    
    settings = result.data[0]
    return {
        "email": settings.get("notification_email", True),
        "push": settings.get("notification_push", False),
        "sound": settings.get("notification_sound", True),
        "frequency": settings.get("notification_frequency", "immediate")
    }


@router.patch("/notifications")
async def update_notification_settings(
    data: NotificationSettings,
    current_user: dict = Depends(get_current_user)
):
    """Обновление настроеk уведомлений"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    update_data = {}
    if data.email is not None:
        update_data["notification_email"] = data.email
    if data.push is not None:
        update_data["notification_push"] = data.push
    if data.sound is not None:
        update_data["notification_sound"] = data.sound
    if data.frequency is not None:
        update_data["notification_frequency"] = data.frequency
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")
    
    existing = supabase.table("user_settings")\
        .select("id")\
        .eq("user_id", user_id)\
        .execute()
    
    if existing.data:
        result = supabase.table("user_settings")\
            .update(update_data)\
            .eq("user_id", user_id)\
            .execute()
    else:
        update_data["user_id"] = user_id
        result = supabase.table("user_settings")\
            .insert(update_data)\
            .execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Ошибка сохранения настроеk")
    
    return {"success": True, "message": "Настройки уведомлений обновлены"}


# ============================================================================
# APPEARANCE SETTINGS ENDPOINTS
# ============================================================================

@router.get("/appearance")
async def get_appearance_settings(current_user: dict = Depends(get_current_user)):
    """Получение настроеk внешнего вида"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    result = supabase.table("user_settings")\
        .select("theme, font_size, compact_mode")\
        .eq("user_id", user_id)\
        .execute()
    
    if not result.data:
        return {
            "theme": "dark",
            "font_size": "medium",
            "compact_mode": False
        }
    
    settings = result.data[0]
    return {
        "theme": settings.get("theme", "dark"),
        "font_size": settings.get("font_size", "medium"),
        "compact_mode": settings.get("compact_mode", False)
    }


@router.patch("/appearance")
async def update_appearance_settings(
    data: AppearanceSettings,
    current_user: dict = Depends(get_current_user)
):
    """Обновление настроеk внешнего вида"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    update_data = {}
    if data.theme is not None:
        update_data["theme"] = data.theme
    if data.font_size is not None:
        update_data["font_size"] = data.font_size
    if data.compact_mode is not None:
        update_data["compact_mode"] = data.compact_mode
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")
    
    existing = supabase.table("user_settings")\
        .select("id")\
        .eq("user_id", user_id)\
        .execute()
    
    if existing.data:
        result = supabase.table("user_settings")\
            .update(update_data)\
            .eq("user_id", user_id)\
            .execute()
    else:
        update_data["user_id"] = user_id
        result = supabase.table("user_settings")\
            .insert(update_data)\
            .execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Ошибка сохранения настроеk")
    
    return {"success": True, "message": "Настройки внешнего вида обновлены"    }





# ============================================================================
# FULL SETTINGS ENDPOINT
# ============================================================================

@router.get("/settings")
async def get_all_settings(current_user: dict = Depends(get_current_user)):
    """Получение всех настроеk пользователя"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    result = supabase.table("user_settings")\
        .select("*")\
        .eq("user_id", user_id)\
        .execute()
    
    if not result.data:
        return {
            "persona": {
                "tone": "friendly",
                "detail_level": "moderate",
                "emotion_level": "balanced",
                "specialization": "general"
            },
            "notifications": {
                "email": True,
                "push": False,
                "sound": True,
                "frequency": "immediate"
            },
            "appearance": {
                "theme": "dark",
                "font_size": "medium",
                "compact_mode": False
            }
        }
    
    settings = result.data[0]
    return {
        "persona": {
            "tone": settings.get("persona_tone", "friendly"),
            "detail_level": settings.get("persona_detail_level", "moderate"),
            "emotion_level": settings.get("persona_emotion_level", "balanced"),
            "specialization": settings.get("persona_specialization", "general")
        },
        "notifications": {
            "email": settings.get("notification_email", True),
            "push": settings.get("notification_push", False),
            "sound": settings.get("notification_sound", True),
            "frequency": settings.get("notification_frequency", "immediate")
        },
        "appearance": {
            "theme": settings.get("theme", "dark"),
            "font_size": settings.get("font_size", "medium"),
            "compact_mode": settings.get("compact_mode", False)
        }
    }