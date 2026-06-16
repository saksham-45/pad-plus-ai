"""
API Routes для управления историей диалогов

Эндпоинты:
- GET /api/v1/dialogs - Список диалогов (с пагинацией)
- GET /api/v1/dialogs/{id} - Детали диалога
- DELETE /api/v1/dialogs/{id} - Удалить диалог
- POST /api/v1/dialogs/{id}/export - Экспорт диалога
- POST /api/v1/dialogs/{id}/favorite - Добавить в избранное
- DELETE /api/v1/dialogs/{id}/favorite - Удалить из избранного
- GET /api/v1/dialogs/search - Поиск по диалогам
- GET /api/v1/dialogs/stats - Статистика диалогов
- DELETE /api/v1/dialogs - Очистить всю историю
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import json
import uuid

logger = logging.getLogger("padplus")

from core.supabase_client import get_supabase

router = APIRouter(prefix="/api/v1/dialogs", tags=["Dialog History"])


# ============================================================================
# МОДЕЛИ ДАННЫХ
# ============================================================================

class DialogResponse(BaseModel):
    id: str
    title: Optional[str]
    created_at: str
    updated_at: str
    message_count: int
    is_favorite: bool
    last_message_at: Optional[str]


class DialogDetailResponse(DialogResponse):
    messages: List[Dict[str, Any]]


class MessageCreate(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    model: Optional[str] = None
    provider: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ExportFormat(str):
    json = "json"
    txt = "txt"


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> dict:
    """Получает текущего пользователя из Supabase Auth"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")
    
    token = authorization[7:]
    
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    try:
        user_response = supabase.auth.get_user(token)
        
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Неверный токен")
        
        user = user_response.user
        
        profile_response = supabase.table("users")\
            .select("*")\
            .eq("id", user.id)\
            .execute()
        
        profile = profile_response.data[0] if profile_response.data else None
        
        return {
            "auth_user": user,
            "profile": profile,
            "id": user.id,
            "email": user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Ошибка аутентификации: {str(e)}")


# ============================================================================
# DIALOG ENDPOINTS
# ============================================================================

@router.get("")
async def list_dialogs(
    current_user: dict = Depends(get_current_user),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc"),
    is_favorite: Optional[bool] = None
):
    """
    Список диалогов пользователя с пагинацией
    
    Args:
        offset: Смещение (по умолчанию 0)
        limit: Количество результатов (1-100, по умолчанию 20)
        sort_by: Поле для сортировки (created_at, updated_at, title)
        sort_order: Порядок сортировки (asc, desc)
        is_favorite: Фильтр по избранному (True/False/None)
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Ограничиваем limit
    limit = min(max(limit, 1), 100)
    
    # Валидируем sort_by
    valid_sort_fields = ["created_at", "updated_at", "title", "message_count"]
    if sort_by not in valid_sort_fields:
        sort_by = "updated_at"
    
    # Валидируем sort_order
    descending = sort_order.lower() != "asc"
    
    # Строим запрос
    query = supabase.table("dialogs")\
        .select("*", count="exact")\
        .eq("user_id", user_id)
    
    # Применяем фильтр по избранному
    if is_favorite is not None:
        query = query.eq("is_favorite", is_favorite)
    
    # Сортировка
    query = query.order(f"{sort_by}", desc=descending)
    
    # Пагинация
    query = query.range(offset, offset + limit - 1)
    
    # Выполняем запрос
    result = query.execute()
    
    total = result.count if result.count else 0
    
    dialogs = []
    for dialog in result.data:
        dialogs.append(DialogResponse(
            id=dialog["id"],
            title=dialog.get("title"),
            created_at=dialog["created_at"],
            updated_at=dialog["updated_at"],
            message_count=dialog.get("message_count", 0),
            is_favorite=dialog.get("is_favorite", False),
            last_message_at=dialog.get("last_message_at")
        ))
    
    return {
        "data": dialogs,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < total
    }


@router.get("/stats")
async def get_dialog_stats(
    current_user: dict = Depends(get_current_user)
):
    """Статистика диалогов пользователя"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Общая статистика
    total_result = supabase.table("dialogs")\
        .select("id", count="exact")\
        .eq("user_id", user_id)\
        .execute()
    
    total_dialogs = total_result.count if total_result.count else 0
    
    # Избранные
    favorite_result = supabase.table("dialogs")\
        .select("id", count="exact")\
        .eq("user_id", user_id)\
        .eq("is_favorite", True)\
        .execute()
    
    favorite_dialogs = favorite_result.count if favorite_result.count else 0
    
    # Общее количество сообщений
    dialogs_result = supabase.table("dialogs")\
        .select("id")\
        .eq("user_id", user_id)\
        .execute()
    
    dialog_ids = [d["id"] for d in dialogs_result.data]
    
    total_messages = 0
    if dialog_ids:
        messages_result = supabase.table("messages")\
            .select("id", count="exact")\
            .in_("dialog_id", dialog_ids)\
            .execute()
        total_messages = messages_result.count if messages_result.count else 0
    
    # Активность по дням (последние 7 дней)
    from datetime import timedelta
    seven_days_ago = datetime.now() - timedelta(days=7)
    
    activity_result = supabase.table("dialogs")\
        .select("created_at")\
        .eq("user_id", user_id)\
        .gte("created_at", seven_days_ago.isoformat())\
        .execute()
    
    # Группируем по дням
    activity_by_day = {}
    for dialog in activity_result.data:
        day = dialog["created_at"][:10]  # YYYY-MM-DD
        activity_by_day[day] = activity_by_day.get(day, 0) + 1
    
    return {
        "total_dialogs": total_dialogs,
        "favorite_dialogs": favorite_dialogs,
        "total_messages": total_messages,
        "activity_by_day": activity_by_day
    }


@router.get("/{dialog_id}")
async def get_dialog(
    dialog_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Получение деталей диалога с сообщениями"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Получаем диалог
    dialog_result = supabase.table("dialogs")\
        .select("*")\
        .eq("id", dialog_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not dialog_result.data:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    
    dialog = dialog_result.data[0]
    
    # Получаем сообщения
    messages_result = supabase.table("messages")\
        .select("*")\
        .eq("dialog_id", dialog_id)\
        .order("created_at", asc=True)\
        .execute()
    
    messages = []
    for msg in messages_result.data:
        # Обработка поля metadata которое может быть строкой
        metadata = msg.get("metadata", {})
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        messages.append({
            "id": msg["id"],
            "role": msg["role"],
            "content": msg["content"],
            "model": msg.get("model"),
            "provider": msg.get("provider"),
            "created_at": msg["created_at"],
            "metadata": metadata
        })
    
    return {
        "id": dialog["id"],
        "title": dialog.get("title"),
        "created_at": dialog["created_at"],
        "updated_at": dialog["updated_at"],
        "message_count": dialog.get("message_count", 0),
        "is_favorite": dialog.get("is_favorite", False),
        "last_message_at": dialog.get("last_message_at"),
        "messages": messages
    }


@router.delete("/{dialog_id}")
async def delete_dialog(
    dialog_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Удаление диалога"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Проверяем, что диалог принадлежит пользователю
    result = supabase.table("dialogs")\
        .delete()\
        .eq("id", dialog_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    
    return {"success": True, "message": "Диалог удалён"}


@router.delete("")
async def delete_all_dialogs(
    current_user: dict = Depends(get_current_user)
):
    """Очистка всей истории диалогов"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    result = supabase.table("dialogs")\
        .delete()\
        .eq("user_id", user_id)\
        .execute()
    
    return {"success": True, "message": "История очищена"}


@router.post("/{dialog_id}/favorite")
async def toggle_favorite(
    dialog_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Добавить/удалить диалог из избранного"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Получаем текущее состояние
    result = supabase.table("dialogs")\
        .select("is_favorite")\
        .eq("id", dialog_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    
    current_favorite = result.data[0].get("is_favorite", False)
    
    # Переключаем
    result = supabase.table("dialogs")\
        .update({"is_favorite": not current_favorite})\
        .eq("id", dialog_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Ошибка обновления")
    
    return {
        "success": True,
        "is_favorite": not current_favorite
    }


@router.post("/{dialog_id}/export")
async def export_dialog(
    dialog_id: str,
    format: str = Query(default="json", pattern="^(json|txt)$"),
    current_user: dict = Depends(get_current_user)
):
    """Экспорт диалога в JSON или TXT формате"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Получаем диалог
    dialog_result = supabase.table("dialogs")\
        .select("*")\
        .eq("id", dialog_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not dialog_result.data:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    
    dialog = dialog_result.data[0]
    
    # Получаем сообщения
    messages_result = supabase.table("messages")\
        .select("*")\
        .eq("dialog_id", dialog_id)\
        .order("created_at", asc=True)\
        .execute()
    
    messages = []
    for msg in messages_result.data:
        messages.append({
            "role": msg["role"],
            "content": msg["content"],
            "model": msg.get("model"),
            "provider": msg.get("provider"),
            "created_at": msg["created_at"]
        })
    
    if format == "json":
        export_data = {
            "dialog": {
                "id": dialog["id"],
                "title": dialog.get("title"),
                "created_at": dialog["created_at"],
                "message_count": len(messages)
            },
            "messages": messages
        }
        
        return JSONResponse(
            content=export_data,
            headers={
                "Content-Disposition": f"attachment; filename=dialog_{dialog_id}.json"
            }
        )
    else:  # txt format
        txt_content = f"Диалог: {dialog.get('title', 'Без названия')}\n"
        txt_content += f"Дата создания: {dialog['created_at']}\n"
        txt_content += f"Количество сообщений: {len(messages)}\n"
        txt_content += "=" * 50 + "\n\n"
        
        for msg in messages:
            role_ru = "Пользователь" if msg["role"] == "user" else "Ассистент"
            txt_content += f"[{role_ru}] ({msg['created_at']}): \n{msg['content']}\n\n"
            txt_content += "-" * 30 + "\n\n"
        
        return JSONResponse(
            content=txt_content,
            headers={
                "Content-Type": "text/plain; charset=utf-8",
                "Content-Disposition": f"attachment; filename=dialog_{dialog_id}.txt"
            }
        )


@router.get("/search")
async def search_dialogs(
    query: str = Query(..., min_length=2),
    current_user: dict = Depends(get_current_user),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100)
):
    """
    Поиск по диалогам
    
    Использует полнотекстовой поиск PostgreSQL
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Сначала ищем сообщения, содержащие запрос
    messages_result = supabase.table("messages")\
        .select("id, dialog_id, role, content, created_at")\
        .eq("role", "user")\
        .filter("content", "ilike", f"%{query}%")\
        .execute()
    
    # Получаем уникальные dialog_id
    dialog_ids = list(set(msg["dialog_id"] for msg in messages_result.data))
    
    if not dialog_ids:
        return {
            "data": [],
            "total": 0,
            "offset": offset,
            "limit": limit,
            "highlights": []
        }
    
    # Получаем диалоги
    dialogs_result = supabase.table("dialogs")\
        .select("*")\
        .in_("id", dialog_ids)\
        .eq("user_id", user_id)\
        .order("updated_at", desc=True)\
        .range(offset, offset + limit - 1)\
        .execute()
    
    # Считаем общее количество
    total = len(dialog_ids)
    
    dialogs = []
    highlights = {}
    
    for dialog in dialogs_result.data:
        # Находим совпадения в сообщениях этого диалога
        dialog_messages = [m for m in messages_result.data if m["dialog_id"] == dialog["id"]]
        
        # Создаём подсветку
        highlights[dialog["id"]] = []
        for msg in dialog_messages[:3]:  # Показываем до 3 совпадений
            content = msg["content"]
            # Выделяем найденный текст
            highlighted = content.replace(query, f"<mark>{query}</mark>")
            highlights[dialog["id"]].append(highlighted)
        
        dialogs.append(DialogResponse(
            id=dialog["id"],
            title=dialog.get("title"),
            created_at=dialog["created_at"],
            updated_at=dialog["updated_at"],
            message_count=dialog.get("message_count", 0),
            is_favorite=dialog.get("is_favorite", False),
            last_message_at=dialog.get("last_message_at")
        ))
    
    return {
        "data": dialogs,
        "total": total,
        "offset": offset,
        "limit": limit,
        "highlights": highlights
    }


