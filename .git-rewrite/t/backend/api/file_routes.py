"""
API Routes для управления документами

Эндпоинты:
- POST /api/v1/documents/upload - Загрузка файла
- POST /api/v1/documents/from-url - Загрузка из интернета
- GET /api/v1/documents - Список документов
- GET /api/v1/documents/search - RAG поиск
- GET /api/v1/documents/stats - Статистика
- GET /api/v1/documents/collections - Список коллекций
- POST /api/v1/documents/collections - Создать коллекцию
- GET /api/v1/documents/settings - Настройки обработки
- GET /api/v1/documents/{id} - Детали документа
- DELETE /api/v1/documents/{id} - Удаление
"""

from fastapi import APIRouter, HTTPException, Depends, Header, UploadFile, File, Query, Body, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import logging
import uuid
import os
import io
import json
import hashlib
import httpx

logger = logging.getLogger("padplus")

router = APIRouter(prefix="/api/v1", tags=["Document Management"])

# Импорт Supabase
from core.supabase_client import get_supabase

# Импорт RAG для векторизации
try:
    from memory.rag import get_rag
    HAS_RAG = True
except ImportError:
    HAS_RAG = False

# Импорт LiteLLM для суммаризации
try:
    from runtime.litellm_service import get_litellm_service
    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False

# Парсинг документов
try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    from langdetect import detect
    HAS_LANG_DETECT = True
except ImportError:
    HAS_LANG_DETECT = False

# Константы
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
CHUNK_SIZE = 800  # токенов на чанк
CHUNK_OVERLAP = 80  # перекрытие 10%

ALLOWED_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain", "text/markdown", "text/csv", "text/html",
    "application/json", "application/xml",
]

# Категории для авто-тегирования
DOCUMENT_CATEGORIES = [
    "техническое", "философское", "личное", "образовательное",
    "творческое", "аналитическое", "бытовое"
]


# ============================================================================
# МОДЕЛИ ДАННЫХ
# ============================================================================

class DocumentResponse(BaseModel):
    id: str
    title: str
    filename: str
    file_type: str
    file_size: int
    collection_id: Optional[str] = None
    status: str
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    summary: Optional[str] = None
    created_at: str
    updated_at: str


class CollectionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    document_count: int
    created_at: str


class DocumentSettings(BaseModel):
    chunk_size: int = CHUNK_SIZE
    chunk_overlap: int = CHUNK_OVERLAP
    auto_summarize: bool = True
    auto_tag: bool = True
    summary_language: str = "ru"
    max_documents_per_collection: int = 1000


class SearchResult(BaseModel):
    document_id: str
    document_title: str
    chunk_text: str
    relevance: float
    tags: List[str] = []


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_user_id(authorization: Optional[str]) -> str:
    """Извлекает user_id из токена"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Требуется аутентификация")
    token = authorization.replace("Bearer ", "")
    return hashlib.md5(token.encode()).hexdigest()[:16]


def extract_text_from_file(content: bytes, file_type: str) -> str:
    """Извлекает текст из файла в зависимости от типа"""
    try:
        if file_type == "application/pdf" and HAS_PDF:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text

        elif file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"] and HAS_DOCX:
            doc = DocxDocument(io.BytesIO(content))
            return "\n".join([p.text for p in doc.paragraphs])

        elif file_type.startswith("text/"):
            return content.decode("utf-8", errors="ignore")

        else:
            return content.decode("utf-8", errors="ignore")

    except Exception as e:
        logger.error(f"❌ Ошибка извлечения текста: {e}")
        return ""


def extract_metadata(content: bytes, file_type: str, filename: str) -> Dict[str, Any]:
    """Извлекает метаданные документа"""
    metadata = {
        "filename": filename,
        "file_type": file_type,
        "size_bytes": len(content),
    }

    try:
        if HAS_LANG_DETECT:
            text_preview = content[:1000].decode("utf-8", errors="ignore")
            if len(text_preview) > 100:
                metadata["language"] = detect(text_preview)
    except Exception:
        pass

    if file_type == "application/pdf" and HAS_PDF:
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                metadata["pages"] = len(pdf.pages)
                if pdf.metadata:
                    metadata["author"] = pdf.metadata.get("Author", "")
                    metadata["title"] = pdf.metadata.get("Title", filename)
        except Exception:
            pass

    return metadata


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Разбивает текст на чанки с перекрытием"""
    char_size = chunk_size * 4
    char_overlap = overlap * 4

    chunks = []
    start = 0
    while start < len(text):
        end = start + char_size
        chunk = text[start:end]
        if end < len(text):
            last_period = chunk.rfind(".")
            if last_period > char_size * 0.5:
                chunk = chunk[:last_period + 1]
                end = start + last_period + 1
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - char_overlap

    return chunks if chunks else [text[:char_size]]


async def auto_tag_text(text: str) -> List[str]:
    """Авто-классификация текста по категориям"""
    text_lower = text[:2000].lower()
    tags = []
    keywords = {
        "техническое": ["код", "программ", "api", "сервер", "база данных", "функци", "алгоритм"],
        "образовательное": ["обучен", "учеб", "курс", "лекци", "знан", "пониман"],
        "философское": ["философ", "смысл", "жизн", "сознан", "мышлен", "истин"],
        "личное": ["я", "мой", "семь", "друг", "чувств", "мнен"],
        "творческое": ["творчеств", "искусств", "музык", "литератур", "поэз"],
        "аналитическое": ["анализ", "сравнен", "статистик", "данны", "исследован"],
        "бытовое": ["магазин", "еда", "дом", "работ", "встреч", "план"],
    }
    for tag, kw_list in keywords.items():
        if any(kw in text_lower for kw in kw_list):
            tags.append(tag)
    return tags if tags else ["общее"]


async def auto_summarize(text: str, language: str = "ru") -> str:
    """Авто-суммаризация документа через подключённый LLM"""
    if not HAS_LITELLM:
        return text[:500] + "..." if len(text) > 500 else text

    try:
        llm = get_litellm_service()
        prompt = f"Сделай краткое содержание текста на {language} языке (3-5 предложений):\n\n{text[:3000]}"

        from core.supabase_client import get_supabase
        supabase = get_supabase()
        result = supabase.table("user_api_keys").select("*").eq("is_default", True).limit(1).execute()

        api_key = None
        model = None
        if result.data:
            key_data = result.data[0]
            from core.encryption import get_encryptor
            encryptor = get_encryptor()
            api_key = encryptor.decrypt(key_data["api_key_encrypted"])
            model = key_data.get("model_preference") or "auto"

        if not api_key:
            return text[:500] + "..." if len(text) > 500 else text

        response = await llm.generate(
            prompt=prompt,
            system_prompt="Ты — ассистент для суммаризации текстов. Делай краткие выжимки.",
            api_key=api_key,
            model=model,
            temperature=0.3,
            max_tokens=300,
        )

        return response.text if response.text else text[:500] + "..."

    except Exception as e:
        logger.error(f"❌ Ошибка суммаризации: {e}")
        return text[:500] + "..." if len(text) > 500 else text


async def process_document(supabase, document_id: str, content: bytes, file_type: str, user_id: str, settings: Dict[str, Any]):
    """Полная обработка документа: парсинг → чанкинг → векторизация → тегирование → суммаризация"""
    try:
        text = extract_text_from_file(content, file_type)
        if not text:
            await supabase.table("documents").update({
                "status": "failed",
                "metadata": {"error": "Не удалось извлечь текст"}
            }).eq("id", document_id).execute()
            return

        metadata = extract_metadata(content, file_type, "document")
        chunks = chunk_text(text, settings.get("chunk_size", CHUNK_SIZE), settings.get("chunk_overlap", CHUNK_OVERLAP))

        if HAS_RAG:
            try:
                rag = get_rag()
                for i, chunk in enumerate(chunks):
                    rag.add_dialog(
                        user_message=f"[Документ chunk {i+1}]",
                        ai_response=chunk[:2000],
                        user_id=user_id,
                        metadata={"document_id": document_id, "chunk_index": i}
                    )
            except Exception as e:
                logger.error(f"❌ Ошибка векторизации: {e}")

        tags = []
        if settings.get("auto_tag", True):
            tags = await auto_tag_text(text)

        summary = None
        if settings.get("auto_summarize", True):
            summary = await auto_summarize(text, settings.get("summary_language", "ru"))

        await supabase.table("documents").update({
            "status": "completed",
            "metadata": {**metadata, "chunks_count": len(chunks), "language": metadata.get("language", "unknown")},
            "tags": tags,
            "summary": summary,
            "updated_at": datetime.now().isoformat()
        }).eq("id", document_id).execute()

        logger.info(f"✅ Документ обработан: {document_id} ({len(chunks)} чанков, {len(tags)} тегов)")

    except Exception as e:
        logger.error(f"❌ Ошибка обработки документа: {e}")
        await supabase.table("documents").update({
            "status": "failed",
            "metadata": {"error": str(e)}
        }).eq("id", document_id).execute()


# ============================================================================
# ENDPOINTS (ВАЖНО: специфичные маршруты ДО параметризованных!)
# ============================================================================

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    collection_id: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None)
):
    """Загрузка документа"""
    supabase = get_supabase()
    
    try:
        user_id = get_user_id(authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Нет авторизации")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Недопустимый тип: {file.content_type}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс 50MB)")

    file_id = str(uuid.uuid4())
    file_path = f"documents/{user_id}/{file_id}_{file.filename}"

    try:
        supabase.storage.from_bucket("user_files").upload(file_path, content, {"content-type": file.content_type})
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки в Storage: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки файла")

    result = supabase.table("documents").insert({
        "id": file_id,
        "user_id": user_id,
        "title": file.filename,
        "filename": file.filename,
        "file_type": file.content_type,
        "file_size": len(content),
        "file_url": file_path,
        "collection_id": collection_id,
        "status": "pending",
        "tags": [],
        "metadata": {},
    }).execute()

    settings = {"chunk_size": CHUNK_SIZE, "chunk_overlap": CHUNK_OVERLAP, "auto_summarize": True, "auto_tag": True}
    await process_document(supabase, file_id, content, file.content_type, user_id, settings)

    return {"id": file_id, "title": file.filename, "status": "completed", "message": "Документ загружен и обработан"}


@router.post("/from-url")
async def upload_from_url(
    url: str = Body(..., embed=True),
    collection_id: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """Загрузка документа из интернета"""
    supabase = get_supabase()
    user_id = get_user_id(authorization)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Не удалось скачать файл")

        content = response.content
        content_type = response.headers.get("content-type", "application/octet-stream")
        filename = url.split("/")[-1] or "document"

    if "pdf" in content_type:
        file_type = "application/pdf"
    elif "word" in content_type or "docx" in content_type:
        file_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif "text" in content_type:
        file_type = "text/plain"
    else:
        file_type = "application/octet-stream"

    file_id = str(uuid.uuid4())
    file_path = f"documents/{user_id}/{file_id}_{filename}"

    try:
        supabase.storage.from_bucket("user_files").upload(file_path, content, {"content-type": file_type})
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка сохранения файла")

    result = supabase.table("documents").insert({
        "id": file_id,
        "user_id": user_id,
        "title": filename,
        "filename": filename,
        "file_type": file_type,
        "file_size": len(content),
        "file_url": file_path,
        "collection_id": collection_id,
        "status": "pending",
        "tags": [],
        "metadata": {"source_url": url},
    }).execute()

    settings = {"chunk_size": CHUNK_SIZE, "chunk_overlap": CHUNK_OVERLAP, "auto_summarize": True, "auto_tag": True}
    await process_document(supabase, file_id, content, file_type, user_id, settings)

    return {"id": file_id, "title": filename, "status": "completed", "message": "Документ загружен из URL"}


@router.get("/documents")
async def list_documents(
    authorization: Optional[str] = Header(None),
    collection_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Список документов пользователя"""
    supabase = get_supabase()
    user_id = get_user_id(authorization)

    query = supabase.table("documents").select("*", count="exact").eq("user_id", user_id)
    if collection_id:
        query = query.eq("collection_id", collection_id)
    if status:
        query = query.eq("status", status)

    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
    result = query.execute()

    return {
        "data": result.data,
        "total": result.count if result.count else 0,
        "limit": limit,
        "offset": offset
    }


@router.get("/documents/search")
async def search_documents(
    q: str = Query(..., min_length=1),
    authorization: Optional[str] = Header(None),
    collection_id: Optional[str] = None,
    limit: int = Query(default=10, ge=1, le=50)
):
    """RAG поиск по документам"""
    if not HAS_RAG:
        raise HTTPException(status_code=500, detail="RAG не доступен")

    user_id = get_user_id(authorization)
    rag = get_rag()
    results = rag.hybrid_search(q, n_results=limit, user_id=user_id)

    return {"query": q, "results": results, "total": len(results)}


@router.get("/documents/stats")
async def get_document_stats(authorization: Optional[str] = Header(None)):
    """Статистика документов"""
    supabase = get_supabase()
    user_id = get_user_id(authorization)

    total = supabase.table("documents").select("id", count="exact").eq("user_id", user_id).execute()
    completed = supabase.table("documents").select("id", count="exact").eq("user_id", user_id).eq("status", "completed").execute()
    size = supabase.table("documents").select("file_size").eq("user_id", user_id).execute()

    total_size = sum(d.get("file_size", 0) for d in size.data) if size.data else 0
    collections = supabase.table("document_collections").select("id", count="exact").eq("user_id", user_id).execute()

    return {
        "total_documents": total.count if total.count else 0,
        "completed_documents": completed.count if completed.count else 0,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "total_collections": collections.count if collections.count else 0,
    }


@router.get("/documents/settings")
async def get_settings(authorization: Optional[str] = Header(None)):
    """Настройки обработки документов"""
    return {
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "auto_summarize": True,
        "auto_tag": True,
        "summary_language": "ru",
        "max_documents_per_collection": 1000,
    }


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    authorization: Optional[str] = Header(None)
):
    """Детали документа"""
    supabase = get_supabase()
    user_id = get_user_id(authorization)

    result = supabase.table("documents").select("*").eq("id", document_id).eq("user_id", user_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Документ не найден")

    return result.data[0]


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    authorization: Optional[str] = Header(None)
):
    """Удаление документа"""
    supabase = get_supabase()
    user_id = get_user_id(authorization)

    doc_result = supabase.table("documents").select("file_url").eq("id", document_id).eq("user_id", user_id).execute()

    if not doc_result.data:
        raise HTTPException(status_code=404, detail="Документ не найден")

    file_path = doc_result.data[0].get("file_url")
    if file_path:
        try:
            supabase.storage.from_bucket("user_files").remove([file_path])
        except Exception:
            pass

    supabase.table("documents").delete().eq("id", document_id).eq("user_id", user_id).execute()

    return {"success": True, "message": "Документ удалён"}
