"""
API Routes для управления документами RAG

Эндпоинты:
- POST /api/v1/documents/upload - Загрузить документ
- GET /api/v1/documents - Список документов
- GET /api/v1/documents/{id} - Детали документа
- DELETE /api/v1/documents/{id} - Удалить документ
- PATCH /api/v1/documents/{id} - Обновить документ
- GET /api/v1/collections - Список коллекций
- POST /api/v1/collections - Создать коллекцию
- DELETE /api/v1/collections/{id} - Удалить коллекцию
"""

from fastapi import APIRouter, HTTPException, Depends, Header, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import uuid
import os

logger = logging.getLogger("padplus")

from core.supabase_client import get_supabase

router = APIRouter(prefix="/api/v1", tags=["Document Management"])


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
        
        return {
            "auth_user": user,
            "id": user.id,
            "email": user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Ошибка аутентификации: {str(e)}")


# ============================================================================
# МОДЕЛИ ДАННЫХ
# ============================================================================

class DocumentResponse(BaseModel):
    id: str
    title: str
    filename: str
    file_type: str
    file_size: int
    collection_id: Optional[str]
    status: str  # pending, processing, completed, failed
    created_at: str
    updated_at: str


class CollectionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    document_count: int
    created_at: str


class CreateCollectionRequest(BaseModel):
    name: str
    description: Optional[str] = None


# ============================================================================
# DOCUMENT ENDPOINTS
# ============================================================================

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    collection_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Загрузка документа для RAG
    
    Поддерживаемые форматы: PDF, DOCX, TXT, MD
    Максимальный размер: 50MB
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Проверка типа файла
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
        "text/markdown",
        "text/csv",
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый тип файла: {file.content_type}. Разрешены: PDF, DOCX, TXT, MD"
        )
    
    # Проверка размера (50MB)
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс 50MB)")
    
    try:
        # Генерируем уникальное имя файла
        file_extension = file.filename.split(".")[-1] if "." in file.filename else ""
        document_id = str(uuid.uuid4())
        file_name = f"{document_id}.{file_extension}" if file_extension else document_id
        
        # Путь в хранилище
        file_path = f"documents/{user_id}/{file_name}"
        
        # Загружаем в Supabase Storage
        supabase.storage.from_bucket("documents")\
            .upload(file_path, content, {"content-type": file.content_type})
        
        # Получаем публичную ссылку
        file_url = supabase.storage.from_bucket("documents")\
            .get_public_url(file_path)
        
        # Сохраняем метаданные в БД
        result = supabase.table("documents")\
            .insert({
                "id": document_id,
                "user_id": user_id,
                "title": file.filename,
                "filename": file_name,
                "file_type": file.content_type,
                "file_size": len(content),
                "file_url": file_url,
                "file_path": file_path,
                "collection_id": collection_id,
                "status": "pending",
            })\
            .execute()
        
        document_data = result.data[0]
        
        # Запускаем обработку документа (в реальном приложении - фоновая задача)
        # await process_document.delay(document_id)
        
        return {
            "id": document_id,
            "title": file.filename,
            "filename": file_name,
            "file_type": file.content_type,
            "file_size": len(content),
            "status": "pending",
            "message": "Документ загружен. Обработка начнется в ближайшее время."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка загрузки документа: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки документа: {str(e)}")


@router.get("/documents")
async def list_documents(
    current_user: dict = Depends(get_current_user),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    collection_id: Optional[str] = None,
    status: Optional[str] = None
):
    """Список документов пользователя"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Строим запрос
    query = supabase.table("documents")\
        .select("*", count="exact")\
        .eq("user_id", user_id)
    
    if collection_id:
        query = query.eq("collection_id", collection_id)
    if status:
        query = query.eq("status", status)
    
    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
    
    result = query.execute()
    
    documents = []
    for doc in result.data:
        documents.append(DocumentResponse(
            id=doc["id"],
            title=doc.get("title", doc.get("filename", "Без названия")),
            filename=doc.get("filename", ""),
            file_type=doc.get("file_type", ""),
            file_size=doc.get("file_size", 0),
            collection_id=doc.get("collection_id"),
            status=doc.get("status", "pending"),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        ))
    
    return {
        "data": documents,
        "total": result.count if result.count else 0,
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < (result.count if result.count else 0)
    }


@router.get("/documents/stats")
async def get_document_stats(
    current_user: dict = Depends(get_current_user)
):
    """Статистика документов"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Общая статистика
    total_result = supabase.table("documents")\
        .select("id", count="exact")\
        .eq("user_id", user_id)\
        .execute()
    
    total_documents = total_result.count if total_result.count else 0
    
    # Статистика по статусам
    status_stats = {}
    for status in ["pending", "processing", "completed", "failed"]:
        result = supabase.table("documents")\
            .select("id", count="exact")\
            .eq("user_id", user_id)\
            .eq("status", status)\
            .execute()
        status_stats[status] = result.count if result.count else 0
    
    # Общий размер
    size_result = supabase.table("documents")\
        .select("file_size")\
        .eq("user_id", user_id)\
        .execute()
    total_size = sum(doc.get("file_size", 0) for doc in size_result.data)
    
    # Количество коллекций
    collections_result = supabase.table("document_collections")\
        .select("id", count="exact")\
        .eq("user_id", user_id)\
        .execute()
    total_collections = collections_result.count if collections_result.count else 0
    
    return {
        "total_documents": total_documents,
        "status_stats": status_stats,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "total_collections": total_collections,
    }


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Получение деталей документа"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    result = supabase.table("documents")\
        .select("*")\
        .eq("id", document_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    doc = result.data[0]
    return DocumentResponse(
        id=doc["id"],
        title=doc.get("title", doc.get("filename", "Без названия")),
        filename=doc.get("filename", ""),
        file_type=doc.get("file_type", ""),
        file_size=doc.get("file_size", 0),
        collection_id=doc.get("collection_id"),
        status=doc.get("status", "pending"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Удаление документа"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Получаем документ для удаления файла
    doc_result = supabase.table("documents")\
        .select("file_path")\
        .eq("id", document_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not doc_result.data:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    file_path = doc_result.data[0].get("file_path")
    
    # Удаляем файл из хранилища
    if file_path:
        supabase.storage.from_bucket("documents").remove([file_path])
    
    # Удаляем запись из БД
    supabase.table("documents")\
        .delete()\
        .eq("id", document_id)\
        .eq("user_id", user_id)\
        .execute()
    
    return {"success": True, "message": "Документ удалён"}


@router.patch("/documents/{document_id}")
async def update_document(
    document_id: str,
    title: Optional[str] = Form(None),
    collection_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Обновление метаданных документа"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if collection_id is not None:
        update_data["collection_id"] = collection_id
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")
    
    result = supabase.table("documents")\
        .update(update_data)\
        .eq("id", document_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    return {"success": True, "message": "Документ обновлёn"}


# ============================================================================
# COLLECTION ENDPOINTS
# ============================================================================

@router.get("/collections")
async def list_collections(
    current_user: dict = Depends(get_current_user)
):
    """Список коллекций пользователя"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    result = supabase.table("document_collections")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True)\
        .execute()
    
    collections = []
    for coll in result.data:
        # Считаем количество документов в коллекции
        doc_count = supabase.table("documents")\
            .select("id", count="exact")\
            .eq("collection_id", coll["id"])\
            .execute()
        
        collections.append(CollectionResponse(
            id=coll["id"],
            name=coll["name"],
            description=coll.get("description"),
            document_count=doc_count.count if doc_count.count else 0,
            created_at=coll["created_at"],
        ))
    
    return {"data": collections}


@router.post("/collections")
async def create_collection(
    data: CreateCollectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Создание коллекции"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    collection_id = str(uuid.uuid4())
    
    result = supabase.table("document_collections")\
        .insert({
            "id": collection_id,
            "user_id": user_id,
            "name": data.name,
            "description": data.description,
        })\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Ошибка создания коллекции")
    
    return {
        "id": collection_id,
        "name": data.name,
        "description": data.description,
        "message": "Коллекция создана"
    }


@router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Удаление коллекции"""
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Проверяем, что коллекция принадлежит пользователю
    coll_result = supabase.table("document_collections")\
        .select("id")\
        .eq("id", collection_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not coll_result.data:
        raise HTTPException(status_code=404, detail="Коллекция не найдена")
    
    # Удаляем коллекцию (документы остаются, но теряют связь с коллекцией)
    supabase.table("document_collections")\
        .delete()\
        .eq("id", collection_id)\
        .eq("user_id", user_id)\
        .execute()
    
    # Сбрасываем collection_id у документов
    supabase.table("documents")\
        .update({"collection_id": None})\
        .eq("collection_id", collection_id)\
        .execute()
    
    return {"success": True, "message": "Коллекция удалена"}


