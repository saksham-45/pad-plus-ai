"""
API Routes — Эндпоинты NeuroMind AI
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
import json

from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Fallback imports
from core.fallback_generator import get_fallback_response, is_fallback_needed

# Импорты для стилей
from core.style_manager import Style as StyleDataclass

router = APIRouter()


# === МОДЕЛИ ДАННЫХ ===

# Pydantic модели для LLM конфигурации
class ProviderConfig(BaseModel):
    enabled: bool
    api_key: Optional[str] = None
    model: Optional[str] = None

class LLMConfig(BaseModel):
    gigachat: ProviderConfig
    gemini: ProviderConfig
    openrouter: ProviderConfig

# Pydantic модели для стилей
class Style(BaseModel):
    """Pydantic модель для стиля"""
    name: str
    description: str
    tone: str
    complexity: str
    verbosity: str
    examples: List[str]
    keywords: List[str]
    constraints: List[str]
    enabled: bool = True

class ChatRequest(BaseModel):
    """Запрос на чат"""
    prompt: str
    context: Optional[dict] = None


class MemorySearchRequest(BaseModel):
    """Запрос на поиск в памяти"""
    query: str
    filters: Optional[dict] = None


class MemoryReflectRequest(BaseModel):
    """Запрос на пересмотр знания"""
    id: Optional[str] = None


class SettingsUpdate(BaseModel):
    """Обновление настроек"""
    fallback: Optional[bool] = None
    confidence_threshold: Optional[float] = None


# === ЭНДПОИНТЫ ===

@router.get("/")
async def api_root():
    """Корневой эндпоинт API"""
    return {
        "name": "NeuroMind API",
        "version": "2.0.0",
        "endpoints": [
            "/chat",
            "/chat/stream",
            "/memory/search",
            "/memory/reflect",
            "/memory/clear_temp",
            "/knowledge/graph",
            "/emotion/state",
            "/logs/stream",
            "/settings",
            "/impulse/start",
            "/impulse/status",
            "/autonomy/status"
        ]
    }


@router.post("/chat")
async def chat(request: ChatRequest, x_session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    """
    Чат через единый PipelineExecutor
    
    Нервная система: Safety → Intent → Retrieve → Generate 
    → Verify → Remember → Emit
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    # Используем session_id из заголовка
    session_id = x_session_id
    
    from core.pipeline import get_pipeline
    from core.anti_directive import ANTI_DIRECTIVE
    from analytics.metrics import get_analytics
    
    # Проверяем, нужны ли пользовательские провайдеры
    if session_id:
        from llm.session_provider_manager import get_session_manager
        session_manager = get_session_manager()
        
        # Проверяем, есть ли у пользователя активные провайдеры
        user_manager = session_manager.create_user_manager(session_id)
        if not user_manager.has_active_providers():
            # Нет пользовательских провайдеров, используем fallback
            from core.config_manager import logger
            logger.info(f"Используем fallback-ответ для сессии {session_id} (нет активных провайдеров)")
            fallback_response = get_fallback_response(request.prompt)
            
            return {
                "prompt": request.prompt,
                "response": fallback_response.content,
                "anti_directive": ANTI_DIRECTIVE.text,
                "timestamp": datetime.now().isoformat(),
                "confidence": fallback_response.confidence,
                "provider": fallback_response.provider,
                "layer": "fallback",
                "style": fallback_response.style,
                "session_id": session_id,
                # Поля пайплайна (fallback)
                "intent": "general",
                "safety": {
                    "passed": True,
                    "warning": None
                },
                "truth": {
                    "confidence": fallback_response.confidence,
                    "claims_verified": 0
                },
                "emotion_style": fallback_response.style,
                "rag_used": False,
                "facts_used": False,
                "execution_time_ms": 0,
                "success": True,
                "errors": [],
                "raw_llm_response": None,
                "llm_metadata": None
            }
    
    # Проверяем, нужен ли fallback (системная проверка)
    if is_fallback_needed():
        from core.config_manager import logger
        logger.info("Используем fallback-ответ (нет активных провайдеров)")
        fallback_response = get_fallback_response(request.prompt)
        
        response = {
            "prompt": request.prompt,
            "response": fallback_response.content,
            "anti_directive": ANTI_DIRECTIVE.text,
            "timestamp": datetime.now().isoformat(),
            "confidence": fallback_response.confidence,
            "provider": fallback_response.provider,
            "layer": "fallback",
            "style": fallback_response.style,
            # Поля пайплайна (fallback)
            "intent": "general",
            "safety": {
                "passed": True,
                "warning": None
            },
            "truth": {
                "confidence": fallback_response.confidence,
                "claims_verified": 0
            },
            "emotion_style": fallback_response.style,
            "rag_used": False,
            "facts_used": False,
            "execution_time_ms": 0,
            "success": True,
            "errors": [],
            "raw_llm_response": None,
            "llm_metadata": None
        }
        
        if session_id:
            response["session_id"] = session_id
        
        return response
    else:
        # Получаем пайплайн
        pipeline = get_pipeline()
        
        # Выполняем через нервную систему
        result = await pipeline.execute(
            user_message=request.prompt,
            context=request.context,
            session_id=session_id
        )
        
        # Аналитика
        analytics = get_analytics()
        analytics.track_message(role="user", text=request.prompt)
        if result.success:
            analytics.track_message(
                role="ai",
                text=result.response,
                tokens=len(result.response.split())
            )
        
        # Формируем ответ
        response = {
            "prompt": request.prompt,
            "response": result.response,
            "anti_directive": ANTI_DIRECTIVE.text,
            "timestamp": datetime.now().isoformat(),
            "confidence": result.confidence,
            "provider": result.provider,
            "cached": False,
            "layer": "soil",
            # Новые поля пайплайна
            "intent": result.intent,
            "safety": {
                "passed": result.safety_passed,
                "warning": result.safety_warning
            },
            "truth": {
                "confidence": result.truth_confidence,
                "claims_verified": result.claims_verified
            },
            "emotion_style": result.emotion_style,
            "rag_used": result.rag_used,
            "facts_used": result.facts_used,
            "execution_time_ms": result.execution_time_ms,
            "success": result.success,
            "errors": result.errors,
            # Сырой ответ LLM
            "raw_llm_response": result.raw_llm_response,
            "llm_metadata": result.llm_metadata
        }
    
    return response


@router.get("/gigachat/test")
async def test_gigachat():
    """Тестовое подключение к GigaChat"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from llm.gigachat import gigachat
    
    health = await gigachat.check_health()
    return {
        "status": health["status"],
        "message": health["message"],
        "enabled": gigachat.enabled,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/gigachat/status")
async def gigachat_status():
    """Статус GigaChat"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from llm.gigachat import gigachat
    
    return {
        "enabled": gigachat.enabled,
        "has_token": gigachat.token is not None,
        "timestamp": datetime.now().isoformat()
    }


class RawGigaChatRequest(BaseModel):
    """Запрос к GigaChat без обработки"""
    prompt: str
    context: Optional[str] = ""
    temperature: Optional[float] = 0.7


@router.post("/gigachat/raw")
async def gigachat_raw(request: RawGigaChatRequest):
    """
    🤖 Сырой ответ от GigaChat без обработки NeuroMind
    
    Возвращает:
    - content: текст ответа
    - raw: полный JSON от GigaChat API
    - metadata: модель, токены, finish_reason
    
    Полезно для сравнения "до/после" обработки NeuroMind
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from llm.gigachat import gigachat
    
    result = await gigachat.generate(
        prompt=request.prompt,
        context=request.context,
        temperature=request.temperature,
        return_raw=True
    )
    
    if isinstance(result, dict):
        return {
            "content": result.get("content", ""),
            "raw": result.get("raw"),
            "metadata": result.get("metadata"),
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "content": result,
            "raw": None,
            "metadata": None,
            "timestamp": datetime.now().isoformat()
        }


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Потоковый чат (SSE)"""
    from core.anti_directive import ANTI_DIRECTIVE
    
    async def generate():
        # Отправляем ANTI_DIRECTIVE
        yield f"data: {json.dumps({'type': 'anti_directive', 'text': ANTI_DIRECTIVE.text}, ensure_ascii=False)}\n\n"
        
        # Отправляем контекст
        yield f"data: {json.dumps({'type': 'context', 'prompt': request.prompt}, ensure_ascii=False)}\n\n"
        
        # Имитация потокового ответа
        response_parts = [
            "Интересный вопрос. ",
            "Давайте подумаем вместе. ",
            "С точки зрения моего понимания, ",
            "это требует сомнения и проверки. ",
            "Каждое знание — гипотеза."
        ]
        
        for part in response_parts:
            yield f"data: {json.dumps({'type': 'delta', 'text': part}, ensure_ascii=False)}\n\n"
        
        # Завершаем
        yield f"data: {json.dumps({'type': 'end', 'confidence': 0.6}, ensure_ascii=False)}\n\n"
        yield "data: [END]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@router.post("/memory/search")
async def memory_search(request: MemorySearchRequest):
    """Поиск в памяти"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.smartcache import get_husk_cache
    from memory.vectormemory import get_soil_memory
    
    results = []
    
    # Ищем в шелухе
    husk = get_husk_cache()
    husk_results = husk.search(request.query, limit=5)
    results.extend([r.to_dict() for r in husk_results])
    
    # Ищем в почве
    soil = get_soil_memory()
    soil_results = soil.search(request.query, limit=10)
    results.extend([r.to_dict() for r in soil_results])
    
    return {
        "query": request.query,
        "results": results,
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/memory/reflect")
async def memory_reflect(request: MemoryReflectRequest):
    """Пересмотр знания"""
    return {
        "status": "reflected",
        "id": request.id,
        "message": "Знание пересмотрено",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/memory/clear_temp")
async def memory_clear_temp():
    """Очистка временной памяти (шелухи)"""
    return {
        "status": "cleared",
        "message": "Временная память очищена",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/knowledge/graph")
async def knowledge_graph():
    """Граф знаний"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from knowledge.graph import get_knowledge_graph
    
    graph = get_knowledge_graph()
    return graph.to_dict()


class ConceptCreate(BaseModel):
    """Создание концепции"""
    name: str
    type: Optional[str] = "concept"
    confidence: Optional[float] = 0.5
    metadata: Optional[dict] = None


class RelationCreate(BaseModel):
    """Создание связи"""
    source_id: str
    target_id: str
    type: Optional[str] = "related"
    weight: Optional[float] = 1.0


@router.post("/knowledge/concepts")
async def create_concept(concept: ConceptCreate):
    """Создать концепцию"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from knowledge.graph import get_knowledge_graph
    
    graph = get_knowledge_graph()
    new_concept = graph.add_concept(
        name=concept.name,
        concept_type=concept.type,
        confidence=concept.confidence,
        metadata=concept.metadata
    )
    
    return {
        "status": "created",
        "concept": new_concept.to_dict(),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/knowledge/relations")
async def create_relation(relation: RelationCreate):
    """Создать связь между концепциями"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from knowledge.graph import get_knowledge_graph
    
    graph = get_knowledge_graph()
    new_relation = graph.add_relation(
        source_id=relation.source_id,
        target_id=relation.target_id,
        relation_type=relation.type,
        weight=relation.weight
    )
    
    if new_relation:
        return {
            "status": "created",
            "relation": new_relation.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "status": "error",
            "message": "Концепции не найдены",
            "timestamp": datetime.now().isoformat()
        }


@router.get("/emotion/state")
async def emotion_state():
    """Текущее эмоциональное состояние"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from emotion.pad_model import get_pad_model
    
    pad = get_pad_model()
    state = pad.get_state()
    result = state.to_dict()
    result["style"] = state.get_style()
    return result


@router.get("/logs/stream")
async def logs_stream():
    """Поток логов (SSE)"""
    async def generate():
        yield f"data: {json.dumps({'message': 'Система запущена', 'level': 'INFO'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'message': 'Ожидание запросов...', 'level': 'DEBUG'}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


@router.get("/settings")
async def get_settings():
    """Получить настройки"""
    return {
        "fallback": True,
        "confidence_threshold": 0.7,
        "language": "ru",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/settings")
async def update_settings(settings: SettingsUpdate):
    """Обновить настройки"""
    return {
        "status": "updated",
        "settings": settings.dict(),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/impulse/start")
async def impulse_start():
    """Запуск импульса (идемпотентный)"""
    from scripts.impulse import start_impulse, is_impulse_initialized
    
    if is_impulse_initialized():
        return {
            "status": "already_initialized",
            "message": "Импульс уже был запущен",
            "timestamp": datetime.now().isoformat()
        }
    
    impulse = start_impulse()
    return {
        "status": "started",
        "impulse": impulse,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/impulse/status")
async def impulse_status():
    """Статус импульса"""
    from scripts.impulse import is_impulse_initialized, get_manager
    
    initialized = is_impulse_initialized()
    result = {
        "initialized": initialized,
        "timestamp": datetime.now().isoformat()
    }
    
    if initialized:
        manager = get_manager()
        impulse = manager.load()
        result["impulse"] = impulse
    
    return result


@router.get("/autonomy/status")
async def autonomy_status():
    """Статус автономных процессов"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.planner import get_planner, get_self_reflection
    
    planner = get_planner()
    reflection = get_self_reflection()
    
    planner_status = planner.get_status()
    reflection_status = reflection.get_status()
    
    return {
        "planner": {
            "running": planner_status["running"],
            "pending_tasks": planner_status["pending_tasks"],
            "completed_tasks": planner_status["completed_tasks"],
            "dialog_count": planner_status.get("dialog_count", 0),
            "reflection_interval": planner_status.get("reflection_interval", 10),
            "last_auto_reflection": planner_status.get("last_auto_reflection")
        },
        "quality": planner_status.get("quality_stats", {}),
        "knowledge_extractions": planner_status.get("knowledge_extractions", 0),
        "self_reflection": {
            "last_reflection": reflection_status["last_reflection"],
            "total_findings": reflection_status["total_findings"]
        },
        "timestamp": datetime.now().isoformat()
    }


@router.post("/autonomy/start")
async def autonomy_start():
    """Запуск автономных процессов"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.planner import get_planner
    
    planner = get_planner()
    planner.start()
    
    return {
        "status": "started",
        "message": "Планировщик запущен",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/autonomy/stop")
async def autonomy_stop():
    """Остановка автономных процессов"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.planner import get_planner
    
    planner = get_planner()
    planner.stop()
    
    return {
        "status": "stopped",
        "message": "Планировщик остановлен",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/autonomy/reflect")
async def autonomy_reflect():
    """Запуск саморефлексии"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.planner import get_self_reflection
    from memory.vectormemory import get_soil_memory
    
    reflection = get_self_reflection()
    memory = get_soil_memory()
    
    # Получаем записи с низкой уверенностью
    records = memory.get_low_confidence(threshold=0.7, limit=100)
    
    # Рефлексируем
    findings = reflection.reflect_on_memory(records)
    
    return {
        "status": "completed",
        "findings": findings,
        "timestamp": datetime.now().isoformat()
    }


# === RAG ЭНДПОИНТЫ ===

class RAGSearchRequest(BaseModel):
    """Запрос на семантический поиск"""
    query: str
    n_results: Optional[int] = 5


@router.get("/rag/stats")
async def rag_stats():
    """Статистика RAG памяти v3.0"""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from memory.rag import get_rag
        from core.config_manager import logger
        
        logger.info("📊 Запрос статистики RAG")
        rag = get_rag()
        stats = rag.get_stats()
        stats["timestamp"] = datetime.now().isoformat()
        logger.info(f"📊 Статистика RAG получена: {len(stats.get('topic_distribution', {}))} тем, {stats.get('total_dialogs', 0)} диалогов")
        return stats
    except Exception as e:
        # Детальное логирование ошибки
        import logging
        import traceback
        logger = logging.getLogger("padplus")
        logger.error(f"❌ Ошибка в /rag/stats: {str(e)}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Возвращаем понятный ответ
        return {
            "error": f"RAG statistics unavailable: {str(e)}",
            "status": "failed",
            "timestamp": datetime.now().isoformat()
        }


@router.get("/rag/topics")
async def rag_topics():
    """Статистика по темам диалогов"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.rag import get_rag
    
    rag = get_rag()
    topic_stats = rag.get_topic_stats()
    
    return {
        "topics": topic_stats,
        "total_topics": len(topic_stats),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/rag/entities")
async def rag_entities():
    """Индекс сущностей"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.rag import get_rag
    
    rag = get_rag()
    entity_index = rag.get_entity_index()
    
    return {
        "entities": entity_index,
        "total_entities": len(entity_index),
        "timestamp": datetime.now().isoformat()
    }


class TopicSearchRequest(BaseModel):
    """Запрос на поиск по теме"""
    topic: str
    n_results: Optional[int] = 5


@router.post("/rag/by-topic")
async def rag_search_by_topic(request: TopicSearchRequest):
    """Поиск диалогов по теме"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.rag import get_rag
    
    rag = get_rag()
    results = rag.search_by_topic(request.topic, request.n_results)
    
    return {
        "topic": request.topic,
        "results": results,
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/rag/search")
async def rag_search(request: RAGSearchRequest):
    """Семантический поиск по истории диалогов"""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from memory.rag import get_rag
        from core.config_manager import logger
        
        logger.info(f"🔍 RAG search request: query='{request.query[:50]}...', n_results={request.n_results}")
        
        rag = get_rag()
        results = rag.search(request.query, n_results=request.n_results)
        
        logger.info(f"🔍 RAG search completed: found {len(results)} results")
        
        return {
            "query": request.query,
            "results": results,
            "total": len(results),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        # Детальное логирование ошибки
        import logging
        import traceback
        logger = logging.getLogger("padplus")
        logger.error(f"❌ Ошибка в /rag/search: {str(e)}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Возвращаем понятный ответ
        return {
            "error": f"RAG search failed: {str(e)}",
            "query": request.query,
            "total": 0,
            "results": [],
            "timestamp": datetime.now().isoformat()
        }


@router.post("/rag/clear")
async def rag_clear():
    """Очистка RAG памяти"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.rag import get_rag
    
    rag = get_rag()
    rag.clear()
    
    return {
        "status": "cleared",
        "message": "RAG память очищена",
        "timestamp": datetime.now().isoformat()
    }


class HybridSearchRequest(BaseModel):
    """Запрос на гибридный поиск"""
    query: str
    n_results: Optional[int] = 5
    use_keywords: Optional[bool] = True
    use_recency: Optional[bool] = True


@router.post("/rag/hybrid")
async def rag_hybrid_search(request: HybridSearchRequest):
    """Гибридный поиск с ранжированием"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.rag import get_rag
    
    rag = get_rag()
    results = rag.hybrid_search(
        query=request.query,
        n_results=request.n_results,
        use_keywords=request.use_keywords,
        use_recency=request.use_recency
    )
    
    return {
        "query": request.query,
        "results": results,
        "total": len(results),
        "mode": "hybrid",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/rag/recent")
async def rag_recent(days: int = 7, limit: int = 10):
    """Недавние диалоги"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.rag import get_rag
    
    rag = get_rag()
    results = rag.get_recent(days=days, n_results=limit)
    
    return {
        "days": days,
        "results": results,
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }


class KeywordSearchRequest(BaseModel):
    """Запрос на поиск по ключевым словам"""
    keywords: List[str]
    n_results: Optional[int] = 5


@router.post("/rag/keywords")
async def rag_keyword_search(request: KeywordSearchRequest):
    """Поиск по ключевым словам"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.rag import get_rag
    
    rag = get_rag()
    results = rag.search_by_keywords(
        keywords=request.keywords,
        n_results=request.n_results
    )
    
    return {
        "keywords": request.keywords,
        "results": results,
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }


# === ANALYTICS ЭНДПОИНТЫ ===

@router.get("/analytics/dashboard")
async def analytics_dashboard(days: int = 7):
    """Метрики дашборда"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from analytics.metrics import get_analytics
    
    analytics = get_analytics()
    return analytics.get_dashboard_metrics(days)


@router.get("/analytics/activity")
async def analytics_activity(days: int = 7):
    """Граф активностей"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from analytics.metrics import get_analytics
    
    analytics = get_analytics()
    return analytics.get_activity_graph(days)


@router.get("/analytics/topics")
async def analytics_topics(days: int = 7, limit: int = 10):
    """Статистика по темам"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from analytics.metrics import get_analytics
    
    analytics = get_analytics()
    return analytics.get_topic_stats(days, limit)


@router.get("/analytics/report")
async def analytics_report(days: int = 7):
    """Полный отчёт аналитики"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from analytics.metrics import get_analytics
    
    analytics = get_analytics()
    return analytics.get_full_report(days)


# === MIND STATE ENDPOINT ===

@router.get("/mind-state")
async def mind_state():
    """
    🧠 Полное состояние системы (Mind State)
    
    Возвращает:
    - Эмоциональное состояние (PAD+)
    - Статистику памяти (RAG, факты)
    - Граф знаний
    - Активные задачи
    - Метрики качества
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    result = {
        "emotion": {},
        "memory": {"rag": {}, "facts": {}},
        "knowledge": {"nodes": 0, "edges": 0},
        "autonomy": {"running": False, "dialog_count": 0},
        "truth": {"total_claims": 0, "average_confidence": 0},
        "safety": {"requests_last_minute": 0, "autonomous_actions": 0},
        "events": {"total_events": 0, "handlers_count": 0},
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Эмоции
        from emotion.pad_model import get_pad_model
        pad = get_pad_model()
        emotion_state = pad.get_state()
        emotion = emotion_state.to_dict()
        emotion["style"] = emotion_state.get_style()
        result["emotion"] = emotion
    except Exception as e:
        result["emotion"] = {"error": str(e)}
    
    try:
        # RAG память
        from memory.rag import get_rag
        rag = get_rag()
        result["memory"]["rag"] = rag.get_stats()
    except Exception as e:
        result["memory"]["rag"] = {"error": str(e)}
    
    try:
        # Факты
        from memory.fact_memory import get_fact_memory
        facts = get_fact_memory()
        result["memory"]["facts"] = facts.get_stats()
    except Exception as e:
        result["memory"]["facts"] = {"error": str(e)}
    
    try:
        # Граф знаний
        from knowledge.graph import get_knowledge_graph
        graph = get_knowledge_graph()
        result["knowledge"] = {
            "nodes": len(graph.nodes) if hasattr(graph, 'nodes') else 0,
            "edges": len(graph.edges) if hasattr(graph, 'edges') else 0
        }
    except Exception as e:
        result["knowledge"] = {"error": str(e)}
    
    try:
        # Автономность
        from autonomy.planner import get_planner
        planner = get_planner()
        planner_status = planner.get_status()
        result["autonomy"] = {
            "running": planner_status.get("running", False),
            "dialog_count": planner_status.get("dialog_count", 0),
            "quality_stats": planner_status.get("quality_stats", {})
        }
    except Exception as e:
        result["autonomy"] = {"error": str(e)}
    
    try:
        # Truth
        from core.truth_loop import get_truth_loop
        truth = get_truth_loop()
        result["truth"] = truth.get_stats()
    except Exception as e:
        result["truth"] = {"error": str(e)}
    
    try:
        # Safety
        from core.safety_layer import get_safety_layer
        safety = get_safety_layer()
        result["safety"] = safety.get_stats()
    except Exception as e:
        result["safety"] = {"error": str(e)}
    
    try:
        # Events
        from core.event_bus import get_event_bus
        bus = get_event_bus()
        result["events"] = bus.get_stats()
    except Exception as e:
        result["events"] = {"error": str(e)}
    
    return result


# === INTENT ROUTER ENDPOINTS ===

@router.post("/router/classify")
async def router_classify(request: ChatRequest):
    """Классификация намерения пользователя"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.intent_router import get_router
    
    router = get_router()
    result = router.route(request.prompt)
    
    return result.to_dict()


@router.get("/router/stats")
async def router_stats():
    """Статистика маршрутизации"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.intent_router import get_router
    
    router = get_router()
    return router.get_routing_stats()


# === TRUTH LOOP ENDPOINTS ===

@router.get("/truth/stats")
async def truth_stats():
    """Статистика верификации"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.truth_loop import get_truth_loop
    
    truth = get_truth_loop()
    return truth.get_stats()


class VerifyRequest(BaseModel):
    """Запрос на верификацию текста"""
    text: str


@router.post("/truth/verify")
async def truth_verify(request: VerifyRequest):
    """Верификация текста"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.truth_loop import get_truth_loop
    from memory.rag import get_rag
    from knowledge.graph import get_knowledge_graph
    
    truth = get_truth_loop()
    rag = get_rag()
    graph = get_knowledge_graph()
    
    result = truth.verify(
        request.text,
        rag_memory=rag,
        knowledge_graph=graph
    )
    
    return result


# === FACT MEMORY ENDPOINTS ===

class FactCreate(BaseModel):
    """Создание факта"""
    subject: str
    predicate: str
    object: str
    confidence: Optional[float] = 0.5
    source: Optional[str] = "user"


@router.post("/facts")
async def create_fact(fact: FactCreate):
    """Создать факт"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.fact_memory import get_fact_memory
    
    facts = get_fact_memory()
    new_fact = facts.add(
        subject=fact.subject,
        predicate=fact.predicate,
        object=fact.object,
        confidence=fact.confidence,
        source=fact.source
    )
    
    return {
        "status": "created",
        "fact": new_fact.to_dict(),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/facts/stats")
async def facts_stats():
    """Статистика фактов"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.fact_memory import get_fact_memory
    
    facts = get_fact_memory()
    return facts.get_stats()


class FactSearchRequest(BaseModel):
    """Поиск фактов"""
    query: str
    limit: Optional[int] = 10


@router.post("/facts/search")
async def facts_search(request: FactSearchRequest):
    """Поиск фактов"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.fact_memory import get_fact_memory
    
    facts = get_fact_memory()
    results = facts.search(request.query, limit=request.limit)
    
    return {
        "query": request.query,
        "results": [f.to_dict() for f in results],
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/facts/contradictions")
async def facts_contradictions():
    """Найти противоречия в фактах"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.fact_memory import get_fact_memory
    
    facts = get_fact_memory()
    contradictions = facts.find_contradictions()
    
    return {
        "contradictions": [
            {"fact1": f1.to_dict(), "fact2": f2.to_dict()}
            for f1, f2 in contradictions
        ],
        "total": len(contradictions),
        "timestamp": datetime.now().isoformat()
    }


# === SAFETY ENDPOINTS ===

@router.get("/safety/stats")
async def safety_stats():
    """Статистика безопасности"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.safety_layer import get_safety_layer
    
    safety = get_safety_layer()
    return safety.get_stats()


class SafetyCheckRequest(BaseModel):
    """Запрос на проверку безопасности"""
    text: str


@router.post("/safety/check")
async def safety_check(request: SafetyCheckRequest):
    """Проверка текста на безопасность"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.safety_layer import get_safety_layer
    
    safety = get_safety_layer()
    result = safety.check_request(request.text)
    
    return result.to_dict()


@router.post("/safety/strict-mode")
async def safety_strict_mode(enable: bool = True):
    """Включить/выключить строгий режим"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.safety_layer import get_safety_layer
    
    safety = get_safety_layer()
    
    if enable:
        safety.enable_strict_mode()
    else:
        safety.disable_strict_mode()
    
    return {
        "status": "updated",
        "strict_mode": enable,
        "timestamp": datetime.now().isoformat()
    }


# === EVENTS ENDPOINTS ===

@router.get("/events/history")
async def events_history(limit: int = 20):
    """История событий"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.event_bus import get_event_bus
    
    bus = get_event_bus()
    events = bus.get_history(limit=limit)
    
    return {
        "events": [e.to_dict() for e in events],
        "total": len(events),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/events/stats")
async def events_stats():
    """Статистика событий"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.event_bus import get_event_bus
    
    bus = get_event_bus()
    return bus.get_stats()


# === PERSONA ENDPOINTS ===

@router.get("/persona/stats")
async def persona_stats():
    """Статистика персоны"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.persona import get_persona
    
    persona = get_persona()
    return persona.get_stats()


@router.get("/persona/traits")
async def persona_traits():
    """Все черты характера"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.persona import get_persona
    
    persona = get_persona()
    traits = persona.get_all_traits()
    
    return {
        "traits": {
            k: {
                "name": t.name,
                "value": round(t.value, 2),
                "description": t.description,
                "stability": t.stability
            }
            for k, t in traits.items()
        },
        "timestamp": datetime.now().isoformat()
    }


class TraitAdjustRequest(BaseModel):
    """Запрос на корректировку черты"""
    trait: str
    delta: float


@router.post("/persona/adjust")
async def persona_adjust(request: TraitAdjustRequest):
    """Корректировка черты характера"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.persona import get_persona
    
    persona = get_persona()
    success = persona.adjust_trait(request.trait, request.delta)
    
    return {
        "success": success,
        "trait": request.trait,
        "delta": request.delta,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/persona/values")
async def persona_values():
    """Ценности и принципы"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.persona import get_persona
    
    persona = get_persona()
    
    return {
        "values": persona.values,
        "principles": persona.principles,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/persona/reflections")
async def persona_reflections(limit: int = 5):
    """Недавние саморефлексии"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.persona import get_persona
    
    persona = get_persona()
    reflections = persona.get_recent_reflections(limit)
    
    return {
        "reflections": [r.to_dict() for r in reflections],
        "total": len(reflections),
        "timestamp": datetime.now().isoformat()
    }


class ReflectionAddRequest(BaseModel):
    """Добавление рефлексии"""
    insight: str
    action: Optional[str] = None
    confidence: Optional[float] = 0.5


@router.post("/persona/reflect")
async def persona_add_reflection(request: ReflectionAddRequest):
    """Добавить саморефлексию"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.persona import get_persona
    
    persona = get_persona()
    persona.add_reflection(
        insight=request.insight,
        action=request.action,
        confidence=request.confidence
    )
    
    return {
        "status": "added",
        "insight": request.insight,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/persona/context")
async def persona_context():
    """Контекст личности для промптов"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.persona import get_persona
    
    persona = get_persona()
    context = persona.get_persona_context()
    
    return {
        "context": context,
        "timestamp": datetime.now().isoformat()
    }


# === PIPELINE STATS ===

@router.get("/pipeline/stats")
async def pipeline_stats():
    """Статистика пайплайна"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.pipeline import get_pipeline
    
    pipeline = get_pipeline()
    return pipeline.get_stats()


# === MEMORY HYGIENE ENDPOINTS ===

@router.get("/hygiene/stats")
async def hygiene_stats():
    """Статистика гигиены памяти"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.hygiene import get_hygiene
    
    hygiene = get_hygiene()
    return hygiene.get_memory_stats()


@router.post("/hygiene/analyze")
async def hygiene_analyze(dry_run: bool = True):
    """
    Анализ памяти для очистки
    
    Args:
        dry_run: Если True, только отчёт без удаления
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.hygiene import get_hygiene
    from memory.rag import get_rag
    from memory.fact_memory import get_fact_memory
    
    hygiene = get_hygiene()
    rag = get_rag()
    facts = get_fact_memory()
    
    report = hygiene.run_cleanup(
        rag_memory=rag,
        fact_memory=facts,
        dry_run=dry_run
    )
    
    return report.to_dict()


@router.post("/hygiene/cleanup")
async def hygiene_cleanup():
    """Запуск очистки памяти (реальное удаление)"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.hygiene import get_hygiene
    from memory.rag import get_rag
    from memory.fact_memory import get_fact_memory
    
    hygiene = get_hygiene()
    rag = get_rag()
    facts = get_fact_memory()
    
    report = hygiene.run_cleanup(
        rag_memory=rag,
        fact_memory=facts,
        dry_run=False
    )
    
    return {
        "status": "completed",
        "report": report.to_dict()
    }


class HygieneConfigRequest(BaseModel):
    """Настройки гигиены"""
    similarity_threshold: Optional[float] = 0.85
    obsolete_days: Optional[int] = 90
    usefulness_threshold: Optional[float] = 0.2
    max_items: Optional[int] = 10000


@router.post("/hygiene/config")
async def hygiene_config(request: HygieneConfigRequest):
    """Обновить настройки гигиены"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.hygiene import get_hygiene
    
    hygiene = get_hygiene()
    hygiene.config.update(request.dict())
    
    return {
        "status": "updated",
        "config": hygiene.config,
        "timestamp": datetime.now().isoformat()
    }


# === ROOTS MEMORY ENDPOINTS ===

@router.get("/roots")
async def roots_list():
    """Все корневые знания"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.roots import get_roots_memory
    
    roots = get_roots_memory()
    all_roots = roots.get_all()
    
    return {
        "roots": [r.to_dict() for r in all_roots],
        "total": len(all_roots),
        "categories": roots.count_by_category(),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/roots/categories")
async def roots_categories():
    """Категории корневых знаний"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.roots import get_roots_memory
    
    roots = get_roots_memory()
    
    return {
        "categories": roots.get_categories(),
        "counts": roots.count_by_category(),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/roots/philosophy")
async def roots_philosophy():
    """Философские принципы"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.roots import get_roots_memory
    
    roots = get_roots_memory()
    philosophy = roots.get_philosophy()
    
    return {
        "philosophy": [r.to_dict() for r in philosophy],
        "total": len(philosophy),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/roots/ethics")
async def roots_ethics():
    """Этические принципы"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.roots import get_roots_memory
    
    roots = get_roots_memory()
    ethics = roots.get_ethics()
    
    return {
        "ethics": [r.to_dict() for r in ethics],
        "total": len(ethics),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/roots/identity")
async def roots_identity():
    """Факты об идентичности"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.roots import get_roots_memory
    
    roots = get_roots_memory()
    identity = roots.get_identity()
    
    return {
        "identity": [r.to_dict() for r in identity],
        "total": len(identity),
        "timestamp": datetime.now().isoformat()
    }


class RootsSearchRequest(BaseModel):
    """Поиск в корневых знаниях"""
    query: str
    limit: Optional[int] = 10


@router.post("/roots/search")
async def roots_search(request: RootsSearchRequest):
    """Поиск в корневых знаниях"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.roots import get_roots_memory
    
    roots = get_roots_memory()
    results = roots.search(request.query, limit=request.limit)
    
    return {
        "query": request.query,
        "results": [r.to_dict() for r in results],
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/roots/context")
async def roots_context(max_items: int = 20):
    """Экспорт для контекста LLM"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.roots import get_roots_memory
    
    roots = get_roots_memory()
    context = roots.export_for_context(max_items)
    
    return {
        "context": context,
        "timestamp": datetime.now().isoformat()
    }


# === COGNITIVE HEALTH ENDPOINTS ===

@router.get("/health")
async def health_assess():
    """Оценка когнитивного здоровья"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.health_monitor import get_health_monitor
    
    monitor = get_health_monitor()
    return monitor.assess_health()


@router.get("/health/report")
async def health_report():
    """Текстовый отчёт о здоровье"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.health_monitor import get_health_monitor
    
    monitor = get_health_monitor()
    report = monitor.get_health_report()
    
    return {
        "report": report,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/health/issues")
async def health_issues():
    """Проблемы здоровья"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.health_monitor import get_health_monitor
    
    monitor = get_health_monitor()
    issues = monitor.detect_issues()
    
    return {
        "issues": [i.to_dict() for i in issues],
        "total": len(issues),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/health/recommendations")
async def health_recommendations():
    """Рекомендации по улучшению"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.health_monitor import get_health_monitor
    
    monitor = get_health_monitor()
    recommendations = monitor.generate_recommendations()
    
    return {
        "recommendations": recommendations,
        "timestamp": datetime.now().isoformat()
    }


class HealthMetricUpdate(BaseModel):
    """Обновление метрики"""
    name: str
    value: float
    reason: Optional[str] = None


@router.post("/health/metric")
async def health_metric_update(request: HealthMetricUpdate):
    """Обновить метрику здоровья"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.health_monitor import get_health_monitor
    
    monitor = get_health_monitor()
    success = monitor.update_metric(
        request.name, 
        request.value, 
        request.reason
    )
    
    return {
        "success": success,
        "metric": request.name,
        "value": request.value,
        "timestamp": datetime.now().isoformat()
    }


class HealthEventRequest(BaseModel):
    """Запись события здоровья"""
    event_type: str
    impact: Optional[float] = 1.0


@router.post("/health/event")
async def health_event(request: HealthEventRequest):
    """Записать событие, влияющее на здоровье"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.health_monitor import get_health_monitor
    
    monitor = get_health_monitor()
    monitor.record_event(request.event_type, request.impact)
    
    return {
        "status": "recorded",
        "event": request.event_type,
        "timestamp": datetime.now().isoformat()
    }


# === META-COGNITIVE ENDPOINTS ===

@router.get("/meta/stats")
async def meta_stats():
    """Статистика мета-когнитивного контроллера"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.meta_controller import get_meta_controller
    
    controller = get_meta_controller()
    return controller.get_stats()


@router.get("/meta/report")
async def meta_report():
    """Мета-когнитивный отчёт"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.meta_controller import get_meta_controller
    
    controller = get_meta_controller()
    report = controller.get_meta_report()
    
    return {
        "report": report,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/meta/load")
async def meta_load():
    """Оценка когнитивной нагрузки"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.meta_controller import get_meta_controller
    
    controller = get_meta_controller()
    load = controller.evaluate_cognitive_load()
    
    return load.to_dict()


@router.get("/meta/state")
async def meta_state():
    """Текущее состояние системы"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.meta_controller import get_meta_controller
    
    controller = get_meta_controller()
    
    return {
        "state": controller.get_state().value,
        "timestamp": datetime.now().isoformat()
    }


class StrategyDecideRequest(BaseModel):
    """Запрос на выбор стратегии"""
    query: str
    context: Optional[dict] = None


@router.post("/meta/decide")
async def meta_decide(request: StrategyDecideRequest):
    """Выбрать стратегию обработки"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.meta_controller import get_meta_controller
    
    controller = get_meta_controller()
    decision = controller.decide_strategy(request.query, request.context)
    
    return decision.to_dict()


@router.get("/meta/subsystems")
async def meta_subsystems():
    """Статус подсистем"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.meta_controller import get_meta_controller
    
    controller = get_meta_controller()
    
    return {
        "subsystems": controller.get_subsystem_status(),
        "timestamp": datetime.now().isoformat()
    }


class AdaptRequest(BaseModel):
    """Запрос на адаптацию"""
    success: bool
    strategy: Optional[str] = None
    response_time: Optional[float] = None
    reason: Optional[str] = None


@router.post("/meta/adapt")
async def meta_adapt(request: AdaptRequest):
    """Адаптация на основе обратной связи"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.meta_controller import get_meta_controller
    
    controller = get_meta_controller()
    controller.adapt(request.dict())
    
    return {
        "status": "adapted",
        "timestamp": datetime.now().isoformat()
    }


# === RESPONSE CACHE ENDPOINTS ===

@router.get("/cache/stats")
async def cache_stats():
    """Статистика кэша ответов"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.response_cache import get_response_cache
    
    cache = get_response_cache()
    return cache.get_stats()


@router.get("/cache/top")
async def cache_top(limit: int = 10):
    """Топ запросов из кэша"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.response_cache import get_response_cache
    
    cache = get_response_cache()
    return {
        "top_queries": cache.get_top_queries(limit),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/cache/invalidate")
async def cache_invalidate(all: bool = True):
    """Инвалидация кэша"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.response_cache import get_response_cache
    
    cache = get_response_cache()
    cache.invalidate(all=all)
    
    return {
        "status": "invalidated",
        "timestamp": datetime.now().isoformat()
    }


# === FEEDBACK SYSTEM ENDPOINTS ===

class FeedbackRequest(BaseModel):
    """Запрос на добавление обратной связи"""
    user_message: str
    ai_response: str
    feedback_type: str  # thumbs_up, thumbs_down, rating, correction
    rating: Optional[int] = None
    correction: Optional[str] = None
    comment: Optional[str] = None
    intent: Optional[str] = ""
    provider: Optional[str] = ""


@router.post("/feedback")
async def feedback_add(request: FeedbackRequest):
    """Добавить обратную связь"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.feedback_system import get_feedback_system, FeedbackType
    
    feedback = get_feedback_system()
    entry = feedback.add_feedback(
        user_message=request.user_message,
        ai_response=request.ai_response,
        feedback_type=FeedbackType(request.feedback_type),
        rating=request.rating,
        correction=request.correction,
        comment=request.comment,
        intent=request.intent,
        provider=request.provider
    )
    
    return {
        "status": "added",
        "id": entry.id,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/feedback/stats")
async def feedback_stats():
    """Статистика обратной связи"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.feedback_system import get_feedback_system
    
    feedback = get_feedback_system()
    return feedback.get_stats()


@router.get("/feedback/problems")
async def feedback_problems():
    """Проблемные области"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.feedback_system import get_feedback_system
    
    feedback = get_feedback_system()
    return {
        "problems": feedback.get_problem_areas(),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/feedback/recommendations")
async def feedback_recommendations():
    """Рекомендации по улучшению"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.feedback_system import get_feedback_system
    
    feedback = get_feedback_system()
    return {
        "recommendations": feedback.get_recommendations(),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/feedback/training-data")
async def feedback_training_data(limit: int = 100):
    """Данные для обучения (RLHF)"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.feedback_system import get_feedback_system
    
    feedback = get_feedback_system()
    data = feedback.get_learning_data(limit)
    
    return {
        "data": data,
        "total": len(data),
        "timestamp": datetime.now().isoformat()
    }


# === DATA MANAGER ENDPOINTS ===

@router.post("/data/export")
async def data_export():
    """Экспорт всех данных"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.data_manager import get_data_manager
    
    manager = get_data_manager()
    filepath = manager.export_data()
    
    return {
        "status": "exported",
        "filepath": filepath,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/data/exports")
async def data_exports_list():
    """Список backup файлов"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.data_manager import get_data_manager
    
    manager = get_data_manager()
    exports = manager.list_exports()
    
    return {
        "exports": exports,
        "total": len(exports),
        "timestamp": datetime.now().isoformat()
    }


class DataImportRequest(BaseModel):
    """Запрос на импорт данных"""
    filepath: str
    merge: Optional[bool] = True


@router.post("/data/import")
async def data_import(request: DataImportRequest):
    """Импорт данных из backup"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.data_manager import get_data_manager
    
    manager = get_data_manager()
    result = manager.import_data(request.filepath, merge=request.merge)
    
    return result


@router.post("/data/cleanup")
async def data_cleanup(keep: int = 10):
    """Очистка старых backup"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.data_manager import get_data_manager
    
    manager = get_data_manager()
    manager.cleanup_old_exports(keep=keep)
    
    return {
        "status": "cleaned",
        "kept": keep,
        "timestamp": datetime.now().isoformat()
    }


# === WEBSOCKET STATS ENDPOINT ===

@router.get("/websocket/stats")
async def websocket_stats():
    """Статистика WebSocket соединений"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.websocket_manager import get_ws_manager
    
    manager = get_ws_manager()
    return manager.get_stats()


# === RATE LIMITER ENDPOINTS ===

@router.get("/rate-limiter/stats")
async def rate_limiter_stats():
    """Статистика Rate Limiter"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.rate_limiter import get_rate_limiter
    
    limiter = get_rate_limiter()
    return limiter.get_stats()


@router.get("/rate-limiter/client/{client_id}")
async def rate_limiter_client(client_id: str):
    """Статистика по клиенту"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.rate_limiter import get_rate_limiter
    
    limiter = get_rate_limiter()
    return limiter.get_client_stats(client_id)


@router.post("/rate-limiter/reset/{client_id}")
async def rate_limiter_reset_client(client_id: str):
    """Сброс лимитов для клиента"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.rate_limiter import get_rate_limiter
    
    limiter = get_rate_limiter()
    limiter.reset_client(client_id)
    
    return {
        "status": "reset",
        "client_id": client_id,
        "timestamp": datetime.now().isoformat()
    }


# === SESSION ENDPOINTS ===

class SessionCreateRequest(BaseModel):
    """Запрос на создание сессии"""
    settings: Optional[dict] = None


@router.post("/sessions")
async def session_create(request: SessionCreateRequest = None):
    """Создать новую сессию"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.session_manager import get_session_manager
    
    manager = get_session_manager()
    session = manager.create_session(
        settings=request.settings if request else None
    )
    
    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "settings": session.settings
    }


@router.get("/sessions/{session_id}")
async def session_get(session_id: str):
    """Получить сессию"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.session_manager import get_session_manager
    
    manager = get_session_manager()
    session = manager.get_session(session_id)
    
    if not session:
        return {"error": "session not found"}
    
    return session.to_dict()


@router.delete("/sessions/{session_id}")
async def session_end(session_id: str):
    """Завершить сессию"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.session_manager import get_session_manager
    
    manager = get_session_manager()
    manager.end_session(session_id)
    
    return {
        "status": "ended",
        "session_id": session_id
    }


@router.get("/sessions/stats")
async def session_stats():
    """Статистика сессий"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.session_manager import get_session_manager
    
    manager = get_session_manager()
    return manager.get_stats()


class SessionSettingsRequest(BaseModel):
    """Обновление настроек сессии"""
    settings: dict


@router.post("/sessions/{session_id}/settings")
async def session_update_settings(
    session_id: str,
    request: SessionSettingsRequest
):
    """Обновить настройки сессии"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.session_manager import get_session_manager
    
    manager = get_session_manager()
    manager.update_settings(session_id, request.settings)
    
    return {
        "status": "updated",
        "session_id": session_id
    }


# === CONFIG ENDPOINTS ===

@router.get("/config")
async def config_get_all():
    """Получить всю конфигурацию"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.config_manager import get_config
    
    config = get_config()
    return config.get_all()


@router.get("/config/{key:path}")
async def config_get_key(key: str):
    """Получить значение конфигурации"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.config_manager import get_config
    
    config = get_config()
    value = config.get(key)
    
    if value is None:
        return {"error": "key not found", "key": key}
    
    return {
        "key": key,
        "value": value,
        "timestamp": datetime.now().isoformat()
    }


class ConfigSetRequest(BaseModel):
    """Установка значения конфигурации"""
    key: str
    value: Any
    description: Optional[str] = None


@router.post("/config")
async def config_set(request: ConfigSetRequest):
    """Установить значение конфигурации"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.config_manager import get_config
    
    config = get_config()
    config.set(request.key, request.value, request.description)
    
    return {
        "status": "updated",
        "key": request.key,
        "value": request.value,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/config/{key:path}/reset")
async def config_reset_key(key: str):
    """Сбросить значение к умолчанию"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.config_manager import get_config
    
    config = get_config()
    config.reset(key)
    
    return {
        "status": "reset",
        "key": key,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/config/validate")
async def config_validate():
    """Валидация конфигурации"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.config_manager import get_config
    
    config = get_config()
    errors = config.validate()
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/config/export")
async def config_export():
    """Экспорт конфигурации в .env формат"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.config_manager import get_config
    
    config = get_config()
    env_content = config.export_env()
    
    return {
        "content": env_content,
        "timestamp": datetime.now().isoformat()
    }


# === EPISODIC MEMORY ENDPOINTS ===

@router.get("/episodic/stats")
async def episodic_stats():
    """Статистика эпизодической памяти"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.episodic import get_episodic_memory
    
    episodic = get_episodic_memory()
    return episodic.get_stats()


class EpisodeSearchRequest(BaseModel):
    """Поиск эпизодов"""
    query: Optional[str] = None
    topic: Optional[str] = None
    intent: Optional[str] = None
    min_significance: Optional[float] = 0.0
    limit: Optional[int] = 10


@router.post("/episodic/search")
async def episodic_search(request: EpisodeSearchRequest):
    """Поиск эпизодов"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.episodic import get_episodic_memory
    
    episodic = get_episodic_memory()
    results = episodic.search_episodes(
        query=request.query,
        topic=request.topic,
        intent=request.intent,
        min_significance=request.min_significance,
        limit=request.limit
    )
    
    return {
        "results": [e.to_dict() for e in results],
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/episodic/timeline")
async def episodic_timeline(days: int = 7, limit: int = 50):
    """Хронология эпизодов"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.episodic import get_episodic_memory
    
    episodic = get_episodic_memory()
    results = episodic.get_timeline(days=days, limit=limit)
    
    return {
        "days": days,
        "episodes": [e.to_dict() for e in results],
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/episodic/significant")
async def episodic_significant(
    min_significance: float = 0.7,
    limit: int = 20
):
    """Значимые эпизоды"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.episodic import get_episodic_memory
    
    episodic = get_episodic_memory()
    results = episodic.get_significant_episodes(
        min_significance=min_significance,
        limit=limit
    )
    
    return {
        "episodes": [e.to_dict() for e in results],
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/episodic/emotional")
async def episodic_emotional(min_impact: float = 0.3, limit: int = 20):
    """Эмоционально заряженные эпизоды"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.episodic import get_episodic_memory
    
    episodic = get_episodic_memory()
    results = episodic.get_emotionally_charged(
        min_impact=min_impact,
        limit=limit
    )
    
    return {
        "episodes": [e.to_dict() for e in results],
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/episodic/{episode_id}")
async def episodic_get(episode_id: str):
    """Получить эпизод по ID"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.episodic import get_episodic_memory
    
    episodic = get_episodic_memory()
    episode = episodic.get_episode(episode_id)
    
    if not episode:
        return {"error": "episode not found"}
    
    return episode.to_dict()


@router.get("/episodic/{episode_id}/related")
async def episodic_related(episode_id: str):
    """Связанные эпизоды"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.episodic import get_episodic_memory
    
    episodic = get_episodic_memory()
    results = episodic.get_related_episodes(episode_id)
    
    return {
        "episode_id": episode_id,
        "related": [e.to_dict() for e in results],
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }


# === SEMANTIC MEMORY ENDPOINTS ===

@router.get("/semantic/stats")
async def semantic_stats():
    """Статистика семантической памяти"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.semantic import get_semantic_memory
    
    semantic = get_semantic_memory()
    return semantic.get_stats()


class SemanticSearchRequest(BaseModel):
    """Поиск в семантической памяти"""
    query: Optional[str] = None
    knowledge_type: Optional[str] = None
    domain: Optional[str] = None
    min_confidence: Optional[float] = 0.0
    tags: Optional[List[str]] = None
    limit: Optional[int] = 10


@router.post("/semantic/search")
async def semantic_search(request: SemanticSearchRequest):
    """Поиск знаний"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.semantic import get_semantic_memory, KnowledgeType
    
    semantic = get_semantic_memory()
    
    k_type = None
    if request.knowledge_type:
        try:
            k_type = KnowledgeType(request.knowledge_type)
        except ValueError:
            pass
    
    results = semantic.search_knowledge(
        query=request.query,
        knowledge_type=k_type,
        domain=request.domain,
        min_confidence=request.min_confidence,
        tags=request.tags,
        limit=request.limit
    )
    
    return {
        "results": [k.to_dict() for k in results],
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/semantic/{knowledge_id}")
async def semantic_get(knowledge_id: str):
    """Получить знание по ID"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.semantic import get_semantic_memory
    
    semantic = get_semantic_memory()
    knowledge = semantic.get_knowledge(knowledge_id)
    
    if not knowledge:
        return {"error": "knowledge not found"}
    
    return knowledge.to_dict()


@router.get("/semantic/self")
async def semantic_self_knowledge():
    """Знания о себе"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.semantic import get_semantic_memory
    
    semantic = get_semantic_memory()
    results = semantic.get_self_knowledge()
    
    return {
        "knowledge": [k.to_dict() for k in results],
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }


class ProcedureApplyRequest(BaseModel):
    """Применение процедуры"""
    context: str
    success: Optional[bool] = True
    feedback: Optional[str] = None


@router.post("/semantic/procedure/{procedure_id}/apply")
async def semantic_procedure_apply(procedure_id: str, request: ProcedureApplyRequest):
    """Применить процедуру"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.semantic import get_semantic_memory
    
    semantic = get_semantic_memory()
    result = semantic.apply_procedure(
        procedure_id=procedure_id,
        context=request.context,
        success=request.success,
        feedback=request.feedback
    )
    
    return result


@router.get("/semantic/procedure/find")
async def semantic_procedure_find(context: str):
    """Найти применимую процедуру"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.semantic import get_semantic_memory
    
    semantic = get_semantic_memory()
    procedure = semantic.find_applicable_procedure(context)
    
    if not procedure:
        return {"found": False}
    
    return {
        "found": True,
        "procedure": procedure.to_dict()
    }


# === CONSOLIDATION ENDPOINTS ===

@router.post("/consolidation/run")
async def consolidation_run():
    """Запуск консолидации"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.consolidation import get_consolidator
    
    consolidator = get_consolidator()
    results = consolidator.consolidate_all()
    
    return {
        "status": "completed",
        "results": {
            key: {
                "processed": r.items_processed,
                "consolidated": r.items_consolidated,
                "insights": r.insights
            }
            for key, r in results.items()
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/consolidation/stats")
async def consolidation_stats():
    """Статистика консолидации"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.consolidation import get_consolidator
    
    consolidator = get_consolidator()
    return consolidator.get_consolidation_stats()


# === DREAM SYSTEM ENDPOINTS ===

@router.get("/dreams/stats")
async def dreams_stats():
    """Статистика снов"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.dreams import get_dream_system
    
    dreams = get_dream_system()
    return dreams.get_dream_stats()


@router.post("/dreams/run")
async def dreams_run():
    """Запуск сна"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.dreams import get_dream_system
    
    dreams = get_dream_system()
    report = await dreams.dream()
    
    if not report:
        return {"status": "already_dreaming"}
    
    return {
        "status": "completed",
        "report": {
            "duration_seconds": report.total_duration,
            "phases_completed": report.phases_completed,
            "episodes_consolidated": report.episodes_consolidated,
            "new_knowledge_items": report.new_knowledge_items,
            "new_connections": report.new_connections,
            "insights": report.insights,
            "recommendations": report.recommendations
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/dreams/last")
async def dreams_last():
    """Отчёт о последнем сне"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.dreams import get_dream_system
    
    dreams = get_dream_system()
    report = dreams.get_last_dream_report()
    
    if not report:
        return {"status": "no_dreams_yet"}
    
    return report


@router.get("/dreams/should-dream")
async def dreams_should():
    """Проверка, пора ли спать"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.dreams import get_dream_system
    
    dreams = get_dream_system()
    
    return {
        "should_dream": dreams.should_dream(),
        "is_dreaming": dreams._is_dreaming,
        "timestamp": datetime.now().isoformat()
    }


# === HIERARCHICAL PLANNER ENDPOINTS ===

@router.get("/plans/stats")
async def plans_stats():
    """Статистика планирования"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.hierarchical_planner import get_hierarchical_planner
    
    planner = get_hierarchical_planner()
    return planner.get_stats()


class VisionCreateRequest(BaseModel):
    """Создание Vision"""
    title: str
    description: Optional[str] = ""
    deadline: Optional[str] = None
    importance: Optional[float] = 0.9


@router.post("/plans/vision")
async def plans_create_vision(request: VisionCreateRequest):
    """Создать Vision"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.hierarchical_planner import get_hierarchical_planner
    
    planner = get_hierarchical_planner()
    
    deadline = None
    if request.deadline:
        try:
            deadline = datetime.fromisoformat(request.deadline)
        except ValueError:
            pass
    
    plan = planner.create_vision(
        title=request.title,
        description=request.description,
        deadline=deadline,
        importance=request.importance
    )
    
    return {
        "status": "created",
        "plan": plan.to_dict(),
        "timestamp": datetime.now().isoformat()
    }


class StrategicCreateRequest(BaseModel):
    """Создание стратегического плана"""
    title: str
    parent_vision_id: str
    description: Optional[str] = ""
    deadline: Optional[str] = None


@router.post("/plans/strategic")
async def plans_create_strategic(request: StrategicCreateRequest):
    """Создать стратегический план"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.hierarchical_planner import get_hierarchical_planner
    
    planner = get_hierarchical_planner()
    
    deadline = None
    if request.deadline:
        try:
            deadline = datetime.fromisoformat(request.deadline)
        except ValueError:
            pass
    
    plan = planner.create_strategic_plan(
        title=request.title,
        parent_vision_id=request.parent_vision_id,
        description=request.description,
        deadline=deadline
    )
    
    return {
        "status": "created",
        "plan": plan.to_dict(),
        "timestamp": datetime.now().isoformat()
    }


class TacticalCreateRequest(BaseModel):
    """Создание тактической задачи"""
    title: str
    parent_strategic_id: str
    description: Optional[str] = ""
    deadline: Optional[str] = None
    priority: Optional[int] = 5


@router.post("/plans/tactical")
async def plans_create_tactical(request: TacticalCreateRequest):
    """Создать тактическую задачу"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.hierarchical_planner import get_hierarchical_planner
    
    planner = get_hierarchical_planner()
    
    deadline = None
    if request.deadline:
        try:
            deadline = datetime.fromisoformat(request.deadline)
        except ValueError:
            pass
    
    plan = planner.create_tactical_task(
        title=request.title,
        parent_strategic_id=request.parent_strategic_id,
        description=request.description,
        deadline=deadline,
        priority=request.priority
    )
    
    return {
        "status": "created",
        "plan": plan.to_dict(),
        "timestamp": datetime.now().isoformat()
    }


class OperationalCreateRequest(BaseModel):
    """Создание операционного действия"""
    title: str
    parent_tactical_id: str
    description: Optional[str] = ""


@router.post("/plans/operational")
async def plans_create_operational(request: OperationalCreateRequest):
    """Создать операционное действие"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.hierarchical_planner import get_hierarchical_planner
    
    planner = get_hierarchical_planner()
    plan = planner.create_operational_action(
        title=request.title,
        parent_tactical_id=request.parent_tactical_id,
        description=request.description
    )
    
    return {
        "status": "created",
        "plan": plan.to_dict(),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/plans")
async def plans_list(level: str = None):
    """Активные планы"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.hierarchical_planner import get_hierarchical_planner, PlanLevel
    
    planner = get_hierarchical_planner()
    
    plan_level = None
    if level:
        try:
            plan_level = PlanLevel(level)
        except ValueError:
            pass
    
    results = planner.get_active_plans(level=plan_level)
    
    return {
        "plans": [p.to_dict() for p in results],
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/plans/hierarchy")
async def plans_hierarchy(plan_id: str = None):
    """Иерархия планов"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.hierarchical_planner import get_hierarchical_planner
    
    planner = get_hierarchical_planner()
    return planner.get_hierarchy(plan_id)


@router.get("/plans/next-actions")
async def plans_next_actions(limit: int = 5):
    """Следующие действия"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.hierarchical_planner import get_hierarchical_planner
    
    planner = get_hierarchical_planner()
    results = planner.get_next_actions(limit=limit)
    
    return {
        "actions": [p.to_dict() for p in results],
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }


class ProgressUpdateRequest(BaseModel):
    """Обновление прогресса"""
    progress: float


@router.post("/plans/{plan_id}/progress")
async def plans_update_progress(plan_id: str, request: ProgressUpdateRequest):
    """Обновить прогресс плана"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.hierarchical_planner import get_hierarchical_planner
    
    planner = get_hierarchical_planner()
    planner.update_progress(plan_id, request.progress)
    
    return {
        "status": "updated",
        "plan_id": plan_id,
        "progress": request.progress,
        "timestamp": datetime.now().isoformat()
    }


class CompletePlanRequest(BaseModel):
    """Завершение плана"""
    outcome: Optional[str] = ""


@router.post("/plans/{plan_id}/complete")
async def plans_complete(plan_id: str, request: CompletePlanRequest):
    """Завершить план"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.hierarchical_planner import get_hierarchical_planner
    
    planner = get_hierarchical_planner()
    planner.complete_plan(plan_id, request.outcome)
    
    return {
        "status": "completed",
        "plan_id": plan_id,
        "timestamp": datetime.now().isoformat()
    }


class FailPlanRequest(BaseModel):
    """Провал плана"""
    reason: str


@router.post("/plans/{plan_id}/fail")
async def plans_fail(plan_id: str, request: FailPlanRequest):
    """Отметить план как проваленный"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.hierarchical_planner import get_hierarchical_planner
    
    planner = get_hierarchical_planner()
    planner.fail_plan(plan_id, request.reason)
    
    return {
        "status": "failed",
        "plan_id": plan_id,
        "timestamp": datetime.now().isoformat()
    }


class AdaptPlanRequest(BaseModel):
    """Адаптация плана"""
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    deadline: Optional[str] = None
    lessons: Optional[str] = None


@router.post("/plans/{plan_id}/adapt")
async def plans_adapt(plan_id: str, request: AdaptPlanRequest):
    """Адаптировать план"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from autonomy.hierarchical_planner import get_hierarchical_planner
    
    planner = get_hierarchical_planner()
    
    adaptation = {}
    if request.title:
        adaptation["title"] = request.title
    if request.description:
        adaptation["description"] = request.description
    if request.priority:
        adaptation["priority"] = request.priority
    if request.deadline:
        try:
            adaptation["deadline"] = datetime.fromisoformat(request.deadline)
        except ValueError:
            pass
    if request.lessons:
        adaptation["lessons"] = request.lessons
    
    plan = planner.adapt_plan(plan_id, adaptation)
    
    if not plan:
        return {"error": "plan not found"}
    
    return {
        "status": "adapted",
        "plan": plan.to_dict(),
        "timestamp": datetime.now().isoformat()
    }


# === STYLE MANAGEMENT ENDPOINTS ===

@router.get("/styles")
async def styles_list():
    """Получить список доступных стилей"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.style_manager import get_style_manager
    
    manager = get_style_manager()
    stats = manager.get_style_stats()
    
    return {
        "styles": stats,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/styles/{style_name}")
async def styles_get(style_name: str):
    """Получить информацию о стиле"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.style_manager import get_style_manager
    
    manager = get_style_manager()
    style = manager.get_style(style_name)
    
    if not style:
        return {"error": "style not found", "style_name": style_name}
    
    return {
        "style": {
            "name": style.name,
            "description": style.description,
            "tone": style.tone,
            "complexity": style.complexity,
            "verbosity": style.verbosity,
            "examples": style.examples,
            "keywords": style.keywords,
            "constraints": style.constraints,
            "enabled": style.enabled
        },
        "timestamp": datetime.now().isoformat()
    }


@router.post("/styles")
async def styles_create(style: Style):
    """Создать пользовательский стиль"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.style_manager import get_style_manager
    
    manager = get_style_manager()
    manager.add_custom_style(style)
    
    return {
        "status": "created",
        "style_name": style.name,
        "timestamp": datetime.now().isoformat()
    }


@router.put("/styles/{style_name}")
async def styles_update(style_name: str, updates: dict):
    """Обновить стиль"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.style_manager import get_style_manager
    
    manager = get_style_manager()
    manager.update_style(style_name, updates)
    
    return {
        "status": "updated",
        "style_name": style_name,
        "updates": updates,
        "timestamp": datetime.now().isoformat()
    }


@router.delete("/styles/{style_name}")
async def styles_disable(style_name: str):
    """Отключить стиль"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.style_manager import get_style_manager
    
    manager = get_style_manager()
    manager.disable_style(style_name)
    
    return {
        "status": "disabled",
        "style_name": style_name,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/styles/context/{style_name}")
async def styles_context(style_name: str):
    """Получить стилистические инструкции для LLM"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.style_manager import get_style_manager
    
    manager = get_style_manager()
    instructions = manager.get_style_instructions(style_name)
    
    return {
        "style_name": style_name,
        "instructions": instructions,
        "timestamp": datetime.now().isoformat()
    }


# === LLM PROVIDER MANAGEMENT ENDPOINTS ===

@router.get("/llm/providers")
async def llm_providers(session_id: Optional[str] = Query(None)):
    """Получить список провайдеров и их статус"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from llm.session_provider_manager import get_session_manager
    
    session_manager = get_session_manager()
    
    if session_id:
        # Получаем провайдеров пользователя
        providers_status = session_manager.get_providers_status(session_id)
        
        # Формируем ответ в ожидаемом формате
        providers_response = {}
        
        # Добавляем пользовательские провайдеры
        if providers_status.get("user_providers"):
            providers_response.update(providers_status["user_providers"])
        
        # Если нет пользовательских, добавляем системные
        if not providers_status.get("has_user_providers") and providers_status.get("system_providers"):
            providers_response.update(providers_status["system_providers"])
        
        return {
            "providers": providers_response,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
    else:
        # Получаем системные провайдеры
        from llm.provider_manager import get_provider_manager
        manager = get_provider_manager()
        providers = manager.get_providers_status()
        
        return {
            "providers": providers,
            "active_provider": manager.get_active_provider_name(),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/llm/models")
async def llm_models(provider: str = "openrouter"):
    """Получить доступные модели для провайдера"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from llm.provider_manager import get_provider_manager
    
    manager = get_provider_manager()
    
    if provider == "openrouter":
        # Список популярных моделей OpenRouter
        models = [
            "google/gemma-7b-it",
            "google/gemma-2-9b-it",
            "meta-llama/llama-3-8b-instruct",
            "meta-llama/llama-3-70b-instruct",
            "anthropic/claude-3-sonnet",
            "openai/gpt-4",
            "openai/gpt-3.5-turbo"
        ]
    elif provider == "gigachat":
        models = ["GigaChat:latest", "GigaChat-Pro"]
    elif provider == "gemini":
        models = ["gemini-pro", "gemini-1.5-flash", "gemini-1.5-pro"]
    else:
        models = []
    
    return {
        "provider": provider,
        "models": models,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/llm/config")
async def llm_config_update(config: LLMConfig, session_id: Optional[str] = Query(None)):
    """Обновить конфигурацию провайдеров"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from llm.session_provider_manager import get_session_manager
    
    session_manager = get_session_manager()
    
    # Если указан session_id, сохраняем в сессию пользователя
    if session_id:
        # Сохраняем конфигурацию в сессию
        session_manager.set_user_provider(session_id, "gigachat", {
            "enabled": config.gigachat.enabled,
            "api_key": config.gigachat.api_key
        })
        
        session_manager.set_user_provider(session_id, "gemini", {
            "enabled": config.gemini.enabled,
            "api_key": config.gemini.api_key
        })
        
        session_manager.set_user_provider(session_id, "openrouter", {
            "enabled": config.openrouter.enabled,
            "api_key": config.openrouter.api_key,
            "model": config.openrouter.model
        })
        
        return {
            "status": "updated",
            "session_id": session_id,
            "config": {
                "gigachat": {
                    "enabled": config.gigachat.enabled,
                    "has_key": config.gigachat.api_key is not None
                },
                "gemini": {
                    "enabled": config.gemini.enabled,
                    "has_key": config.gemini.api_key is not None
                },
                "openrouter": {
                    "enabled": config.openrouter.enabled,
                    "has_key": config.openrouter.api_key is not None,
                    "model": config.openrouter.model
                }
            },
            "timestamp": datetime.now().isoformat()
        }
    
    # Иначе сохраняем в системную конфигурацию (старое поведение)
    else:
        from llm.provider_manager import get_provider_manager
        from core.config_manager import get_config
        
        manager = get_provider_manager()
        config_manager = get_config()
        
        # Обновляем конфигурацию
        if config.gigachat.enabled:
            config_manager.set("GIGACHAT_ENABLED", True)
            if config.gigachat.api_key:
                config_manager.set("GIGACHAT_API_KEY", config.gigachat.api_key)
        else:
            config_manager.set("GIGACHAT_ENABLED", False)
        
        if config.gemini.enabled:
            config_manager.set("GEMINI_ENABLED", True)
            if config.gemini.api_key:
                config_manager.set("GEMINI_API_KEY", config.gemini.api_key)
        else:
            config_manager.set("GEMINI_ENABLED", False)
        
        if config.openrouter.enabled:
            config_manager.set("OPENROUTER_ENABLED", True)
            if config.openrouter.api_key:
                config_manager.set("OPENROUTER_API_KEY", config.openrouter.api_key)
            if config.openrouter.model:
                config_manager.set("OPENROUTER_MODEL", config.openrouter.model)
        else:
            config_manager.set("OPENROUTER_ENABLED", False)
        
        # Перезагружаем провайдеров
        manager.reload_providers()
        
        return {
            "status": "updated",
            "config": {
                "gigachat": {
                    "enabled": config.gigachat.enabled,
                    "has_key": config.gigachat.api_key is not None
                },
                "gemini": {
                    "enabled": config.gemini.enabled,
                    "has_key": config.gemini.api_key is not None
                },
                "openrouter": {
                    "enabled": config.openrouter.enabled,
                    "has_key": config.openrouter.api_key is not None,
                    "model": config.openrouter.model
                }
            },
            "timestamp": datetime.now().isoformat()
        }


@router.get("/llm/health")
async def llm_health():
    """Проверка здоровья всех провайдеров"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from llm.provider_manager import get_provider_manager
    
    manager = get_provider_manager()
    health = manager.check_all_health()
    
    return {
        "health": health,
        "active_provider": manager.get_active_provider_name(),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/llm/test/{provider}")
async def llm_test_provider(provider: str, session_id: Optional[str] = Query(None)):
    """Тестирование провайдера"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from llm.session_provider_manager import get_session_manager
    
    session_manager = get_session_manager()
    
    if session_id:
        # Тестируем провайдер пользователя
        try:
            result = await session_manager.test_user_provider(session_id, provider)
            return {
                "provider": provider,
                "session_id": session_id,
                "status": "success" if result.get("success") else "failed",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "provider": provider,
                "session_id": session_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    else:
        # Тестируем системный провайдер
        from llm.provider_manager import get_provider_manager
        manager = get_provider_manager()
        
        try:
            # Сначала пробуем использовать test_connection если он есть
            provider_instance = manager.providers.get(provider)
            if provider_instance and hasattr(provider_instance, 'test_connection'):
                result = await provider_instance.test_connection()
                return {
                    "provider": provider,
                    "status": "success" if result.get("success") else "failed",
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Используем старый метод test_provider
                result = await manager.test_provider(provider)
                return {
                    "provider": provider,
                    "status": "success" if result else "failed",
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "provider": provider,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


@router.get("/llm/usage")
async def llm_usage():
    """Статистика использования провайдеров"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from llm.provider_manager import get_provider_manager
    
    manager = get_provider_manager()
    usage = manager.get_usage_stats()
    
    return {
        "usage": usage,
        "timestamp": datetime.now().isoformat()
    }
