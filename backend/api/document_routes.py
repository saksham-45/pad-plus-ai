"""
API Routes для управления документами RAG

Эндпоинты:
- POST /api/v1/documents/upload - Загрузить документ
- POST /api/v1/documents/from-url - Загрузить из интернета
- GET /api/v1/documents - Список документов
- GET /api/v1/documents/{id} - Детали документа
- DELETE /api/v1/documents/{id} - Удалить документ
- PATCH /api/v1/documents/{id} - Обновить документ
- GET /api/v1/documents/search - RAG поиск
- GET /api/v1/documents/settings - Настройки обработки
- GET /api/v1/collections - Список коллекций
- POST /api/v1/collections - Создать коллекцию
- DELETE /api/v1/collections/{id} - Удалить коллекцию
"""

from fastapi import APIRouter, HTTPException, Depends, Header, UploadFile, File, Form, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import uuid
import os
import io
import httpx

logger = logging.getLogger("padplus")

from core.supabase_client import get_db_client, get_supabase, get_supabase_service
from core.auth_manager import get_current_user_safe as get_current_user
from core.document_processor import process_document
import asyncio

router = APIRouter(prefix="/api/v1", tags=["Document Management"])


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
    supabase = get_supabase_service()
    user_id = current_user["id"]
    
    # Проверка типа файла (по расширению если MIME type не определён)
    allowed_extensions = [".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".json", ".xml", ".html"]
    file_extension = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    
    # Проверяем по расширению если MIME type не определён или не точный
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый тип файла: {file.filename}. Разрешены: PDF, DOCX, DOC, TXT, MD, CSV, JSON, XML, HTML"
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
        try:
            supabase.storage.from_("documents")\
                .upload(file_path, content, {"content-type": file.content_type or "application/octet-stream"})
        except Exception as storage_error:
            logger.error(f"Storage upload error: {storage_error}")
            # Bucket должен быть создан вручную в Supabase Dashboard
            raise HTTPException(status_code=500, detail=f"Ошибка загрузки в хранилище: bucket 'documents' не найден. Создайте его в Supabase Dashboard → Storage")
        
        # Получаем публичную ссылку
        file_url = supabase.storage.from_("documents").get_public_url(file_path)
        
        # Сохраняем метаданные в БД (через service_role для обхода RLS)
        db = get_db_client(current_user)
        if not db:
            raise HTTPException(status_code=500, detail="БД не подключена")
        
        result = db.table("documents")\
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
        
        # Запускаем фоновую обработку документа
        asyncio.create_task(process_document(document_id))
        
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
    db = get_db_client(current_user)
    if not db:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    user_id = current_user["id"]
    
    # Пробуем с фильтром is_deleted (колонка может отсутствовать до миграции)
    try:
        query = db.table("documents")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("is_deleted", False)
        
        if collection_id:
            query = query.eq("collection_id", collection_id)
        if status:
            query = query.eq("status", status)
        
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()
    except Exception:
        # Fallback: колонка is_deleted ещё не создана
        query = db.table("documents")\
            .select("*")\
            .eq("user_id", user_id)
        
        if collection_id:
            query = query.eq("collection_id", collection_id)
        if status:
            query = query.eq("status", status)
        
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()
    
    # Общее количество — только если первая страница
    total = 0
    if offset == 0:
        try:
            count_query = db.table("documents")\
                .select("id", count="exact")\
                .eq("user_id", user_id)
            try:
                count_query = count_query.eq("is_deleted", False)
                count_result = count_query.limit(0).execute()
            except Exception:
                count_result = count_query.limit(0).execute()
            total = count_result.count if count_result.count else 0
        except Exception as e:
            logger.warning(f"{__name__} error: {e}")
    
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
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < total if total > 0 else len(result.data) >= limit
    }


@router.get("/documents/stats")
async def get_document_stats(
    current_user: dict = Depends(get_current_user)
):
    """Статистика документов"""
    db = get_db_client(current_user)
    if not db:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    user_id = current_user["id"]
    
    # Вспомогательная функция: запрос с опциональным is_deleted
    def query_docs(select_col, count=None, extra_eq=None):
        q = db.table("documents").select(select_col, count=count).eq("user_id", user_id)
        try:
            if extra_eq:
                q = q.eq(*extra_eq)
            return q.limit(0).execute() if count else q.limit(1000).execute()
        except Exception:
            # колонка is_deleted отсутствует — пробуем без неё
            if extra_eq and extra_eq[0] == 'is_deleted':
                q = db.table("documents").select(select_col, count=count).eq("user_id", user_id)
                return q.limit(0).execute() if count else q.limit(1000).execute()
            raise

    # Общая статистика (только активные)
    total_documents = 0
    try:
        r = query_docs("id", count="exact", extra_eq=("is_deleted", False))
        total_documents = r.count if r.count else 0
    except Exception as e:
        logger.warning(f"{__name__} total count error: {e}")

    # Статистика по статусам (только активные)
    status_stats = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
    try:
        r = query_docs("status", extra_eq=("is_deleted", False))
        for doc in r.data or []:
            s = doc.get("status", "pending")
            if s in status_stats:
                status_stats[s] += 1
    except Exception as e:
        logger.warning(f"{__name__} status stats error: {e}")

    # Общий размер (только активные)
    total_size = 0
    try:
        r = query_docs("file_size", extra_eq=("is_deleted", False))
        total_size = sum(doc.get("file_size", 0) for doc in r.data or [])
    except Exception as e:
        logger.warning(f"{__name__} size error: {e}")

    # Количество коллекций
    total_collections = 0
    try:
        r = db.table("document_collections")\
            .select("id", count="exact")\
            .eq("user_id", user_id)\
            .limit(0)\
            .execute()
        total_collections = r.count if r.count else 0
    except Exception as e:
        logger.warning(f"{__name__} collections error: {e}")

    # Количество в корзине
    trash_count = 0
    try:
        r = query_docs("id", count="exact", extra_eq=("is_deleted", True))
        trash_count = r.count if r.count else 0
    except Exception as e:
        logger.warning(f"{__name__} trash count error: {e}")
    
    return {
        "total_documents": total_documents,
        "completed_documents": status_stats.get("completed", 0),
        "status_stats": status_stats,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "total_collections": total_collections,
        "trash_count": trash_count,
    }


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Получение деталей документа"""
    db = get_db_client(current_user)
    if not db:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    user_id = current_user["id"]
    
    result = db.table("documents")\
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
async def soft_delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Мягкое удаление документа — отправляет в корзину"""
    db = get_db_client(current_user)
    if not db:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    user_id = current_user["id"]
    
    # Пробуем soft-delete, fallback на hard-delete если колонки нет
    try:
        result = db.table("documents")\
            .update({"is_deleted": True, "deleted_at": "now()"})\
            .eq("id", document_id)\
            .eq("user_id", user_id)\
            .eq("is_deleted", False)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Документ не найден")
        
        return {"success": True, "message": "Документ перемещён в корзину"}
    except Exception:
        # Fallback: колонка is_deleted ещё не создана — hard-delete
        storage = get_supabase()
        
        doc_result = db.table("documents")\
            .select("file_path")\
            .eq("id", document_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Документ не найден")
        
        file_path = doc_result.data[0].get("file_path")
        
        if file_path and storage:
            try:
                storage.storage.from_("documents").remove([file_path])
            except Exception:
                pass
        
        db.table("documents")\
            .delete()\
            .eq("id", document_id)\
            .eq("user_id", user_id)\
            .execute()
        
        return {"success": True, "message": "Документ удалён"}


@router.get("/documents/trash")
async def list_trash(
    current_user: dict = Depends(get_current_user)
):
    """Список документов в корзине"""
    db = get_db_client(current_user)
    if not db:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    user_id = current_user["id"]
    
    try:
        result = db.table("documents")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("is_deleted", True)\
            .order("deleted_at", desc=True)\
            .execute()
    except Exception:
        # Колонка is_deleted отсутствует — корзина пуста
        return {"data": []}
    
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
    
    return {"data": documents}


@router.post("/documents/{document_id}/restore")
async def restore_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Восстановление документа из корзины"""
    db = get_db_client(current_user)
    if not db:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    user_id = current_user["id"]
    
    try:
        result = db.table("documents")\
            .update({"is_deleted": False, "deleted_at": None})\
            .eq("id", document_id)\
            .eq("user_id", user_id)\
            .eq("is_deleted", True)\
            .execute()
    except Exception:
        raise HTTPException(status_code=400, detail="Корзина не поддерживается — накатите миграцию")
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Документ не найден в корзине")
    
    return {"success": True, "message": "Документ восстановлен"}


@router.delete("/documents/trash/clear")
async def clear_trash(
    current_user: dict = Depends(get_current_user),
    document_id: Optional[str] = Query(None, description="Удалить конкретный документ из корзины навсегда"),
):
    """Очистка корзины — безвозвратное удаление файлов из Storage и БД"""
    db = get_db_client(current_user)
    storage = get_supabase()
    if not db or not storage:
        raise HTTPException(status_code=500, detail="БД или Storage не подключены")
    
    user_id = current_user["id"]
    
    # Выбираем документы для удаления
    try:
        query = db.table("documents")\
            .select("id, file_path")\
            .eq("user_id", user_id)\
            .eq("is_deleted", True)
        
        if document_id:
            query = query.eq("id", document_id)
        
        result = query.execute()
    except Exception:
        raise HTTPException(status_code=400, detail="Корзина не поддерживается — накатите миграцию")
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Нет документов для удаления")
    
    # Удаляем файлы из Storage
    file_paths = [d["file_path"] for d in result.data if d.get("file_path")]
    if file_paths:
        try:
            storage.storage.from_("documents").remove(file_paths)
        except Exception as e:
            logger.warning(f"Ошибка удаления файлов из Storage: {e}")
    
    # Удаляем записи из БД
    try:
        delete_query = db.table("documents")\
            .delete()\
            .eq("user_id", user_id)\
            .eq("is_deleted", True)
        
        if document_id:
            delete_query = delete_query.eq("id", document_id)
        
        delete_query.execute()
    except Exception:
        delete_query = db.table("documents")\
            .delete()\
            .eq("user_id", user_id)
        if document_id:
            delete_query = delete_query.eq("id", document_id)
        delete_query.execute()
    
    count = len(result.data)
    return {"success": True, "message": f"Удалено навсегда: {count}"}


@router.patch("/documents/{document_id}")
async def update_document(
    document_id: str,
    title: Optional[str] = Form(None),
    collection_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Обновление метаданных документа"""
    db = get_db_client(current_user)
    if not db:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    user_id = current_user["id"]
    
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if collection_id is not None:
        update_data["collection_id"] = collection_id
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")
    
    result = db.table("documents")\
        .update(update_data)\
        .eq("id", document_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    return {"success": True, "message": "Документ обновлён"}


# ============================================================================
# COLLECTION ENDPOINTS
# ============================================================================

@router.get("/collections")
async def list_collections(
    current_user: dict = Depends(get_current_user)
):
    """Список коллекций пользователя"""
    db = get_db_client(current_user)
    if not db:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    user_id = current_user["id"]
    
    result = db.table("document_collections")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True)\
        .execute()
    
    collections = []
    for coll in result.data:
        # Считаем количество документов в коллекции
        doc_count = 0
        try:
            dc = db.table("documents")\
                .select("id", count="exact")\
                .eq("collection_id", coll["id"])\
                .eq("is_deleted", False)\
                .limit(0)\
                .execute()
            doc_count = dc.count if dc.count else 0
        except Exception as e:
            logger.warning(f"{__name__} error: {e}")
        
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
    db = get_db_client(current_user)
    if not db:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    user_id = current_user["id"]
    
    collection_id = str(uuid.uuid4())
    
    result = db.table("document_collections")\
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
    db = get_db_client(current_user)
    if not db:
        raise HTTPException(status_code=500, detail="БД не подключена")
    
    user_id = current_user["id"]
    
    # Проверяем, что коллекция принадлежит пользователю
    coll_result = db.table("document_collections")\
        .select("id")\
        .eq("id", collection_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not coll_result.data:
        raise HTTPException(status_code=404, detail="Коллекция не найдена")
    
    # Удаляем коллекцию (документы остаются, но теряют связь с коллекцией)
    db.table("document_collections")\
        .delete()\
        .eq("id", collection_id)\
        .eq("user_id", user_id)\
        .execute()
    
    return {"success": True, "message": "Коллекция удалена"}


# ============================================================================
# SEARCH ENDPOINT (RAG поиск по документам)
# ============================================================================

@router.get("/documents/search")
async def search_documents(
    q: str = Query(..., min_length=1),
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=10, ge=1, le=50),
    threshold: float = Query(default=0.5, ge=0.0, le=1.0),
):
    """Векторный поиск по документам пользователя.

    Использует pgvector cosine similarity для поиска релевантных чанков.
    """
    try:
        user_id = current_user["id"]
        results = await search_document_chunks(
            query=q,
            user_id=user_id,
            limit=limit,
            similarity_threshold=threshold,
        )
        return {"query": q, "results": results, "total": len(results)}
    except ImportError:
        raise HTTPException(status_code=500, detail="RAG не доступен")
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"query": q, "results": [], "total": 0, "error": str(e)}


# ============================================================================
# SETTINGS ENDPOINT
# ============================================================================

CHUNK_SIZE = 800
CHUNK_OVERLAP = 80


@router.get("/documents/settings")
async def get_document_settings(current_user: dict = Depends(get_current_user)):
    """Настройки обработки документов"""
    return {
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "auto_summarize": True,
        "auto_tag": True,
        "summary_language": "ru",
        "max_documents_per_collection": 1000,
    }


# ============================================================================
# URL UPLOAD ENDPOINT
# ============================================================================

@router.post("/documents/from-url")
async def upload_from_url(
    data: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Загрузка документа из URL"""
    url = data.get("url", "")
    if not url:
        raise HTTPException(status_code=400, detail="URL обязателен")
    if len(url) > 2048:
        raise HTTPException(status_code=400, detail="URL слишком длинный")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Не удалось скачать: {resp.status_code}")
            content = resp.content
            content_type = resp.headers.get("content-type", "application/octet-stream")
            filename = url.split("/")[-1] or "document"
    except httpx.TimeoutException:
        raise HTTPException(status_code=408, detail="Таймаут при скачивании")
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Ошибка сети: {str(e)}")

    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Файл слишком большой (макс 50MB)")

    supabase = get_supabase_service()
    db = get_db_client(current_user)
    user_id = current_user["id"]
    collection_id = data.get("collection_id")
    document_id = str(uuid.uuid4())
    file_name = f"{document_id}_{filename}"
    file_path = f"documents/{user_id}/{file_name}"

    try:
        supabase.storage.from_("documents").upload(
            file_path, content, {"content-type": content_type}
        )
        file_url = supabase.storage.from_("documents").get_public_url(file_path)

        db.table("documents").insert({
            "id": document_id, "user_id": user_id, "title": filename,
            "filename": file_name, "file_type": content_type,
            "file_size": len(content), "file_url": file_url,
            "file_path": file_path, "collection_id": collection_id,
            "status": "pending",
        }).execute()

        asyncio.create_task(process_document(document_id))

        return {"id": document_id, "title": filename, "status": "pending", "message": "Документ загружен из URL"}
    except Exception as e:
        logger.error(f"URL upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")


