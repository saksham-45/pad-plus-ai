"""
🔄 Pipeline Helpers — Вспомогательные функции для PipelineExecutor

Вынесены из pipeline.py для улучшения читаемости и тестируемости.
"""

from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger("padplus.pipeline_helpers")


def extract_context_data(
    context: Optional[Dict[str, Any]]
) -> Tuple[Optional[str], Optional[str]]:
    """
    Извлекает user_id и session_id из контекста
    
    Args:
        context: Контекст запроса
        
    Returns:
        (user_id, session_id)
    """
    if not context:
        return None, None
    
    user_id = context.get('user_id')
    session_id = context.get('session_id')
    
    return user_id, session_id


def format_rag_context(
    rag_context: str,
    facts_context: list,
    episodic_context: str,
    procedure_context: str,
    persona_context: str,
    emotion_style: Dict,
    emotion_state: Dict,
    strategy: str,
    roots_context: str,
    persona_prompt: str
) -> str:
    """
    Формирует полный контекст для LLM
    
    Returns:
        Форматированный промпт
    """
    full_context = f"""Ты — PAD+ AI, цифровой организм.

{roots_context}

Твоя ДНК (ANTI_DIRECTIVE): {persona_prompt}

{persona_context}

Твоё текущее эмоциональное состояние:
- Тон: {emotion_style.get('tone', 'neutral')}
- Уверенность: {emotion_state.get('уверенность', 0.5):.2f}

Стратегия обработки: {strategy}

Всегда отвечай на русском. Будь кратким, но глубоким.
Сомневайся в утверждениях. Проверяй факты.
"""
    return full_context


def process_safety_check(
    user_message: str,
    safety_layer
) -> Tuple[bool, Optional[str], str]:
    """
    Проверяет безопасность запроса
    
    Returns:
        (is_safe, warning_message, sanitized_message)
    """
    try:
        safety_check = safety_layer.check_request(user_message)
        
        if safety_check.action.value == "block":
            return False, safety_check.warning_message, user_message
        
        if safety_check.action.value == "sanitize":
            user_message = safety_layer.sanitize_input(user_message)
        
        warning = safety_check.warning_message if safety_check.action.value == "warn" else None
        return True, warning, user_message
        
    except Exception as e:
        logger.warning(f"Safety check error: {e}")
        return True, None, user_message


def detect_intent(
    user_message: str,
    intent_router
) -> Tuple[str, Optional[list]]:
    """
    Определяет намерение пользователя
    
    Returns:
        (intent, pipeline_stages)
    """
    try:
        routing = intent_router.route(user_message)
        intent = routing.intent.value
        pipeline = [s.name for s in routing.pipeline[:3]]
        return intent, pipeline
    except Exception as e:
        logger.warning(f"Intent detection error: {e}")
        return "chat_general", None


def gather_memory_context(
    user_message: str,
    user_id: Optional[str],
    rag,
    facts_memory,
    episodic_memory,
    semantic_memory,
    vector_memory,
    smartcache
) -> Dict[str, Any]:
    """
    Собирает контекст из всех источников памяти
    
    Returns:
        Словарь с контекстом и источниками
    """
    result = {
        "rag_context": "",
        "facts_context": [],
        "episodic_context": "",
        "procedure_context": "",
        "vector_context": None,
        "smartcache_context": None,
        "sources": {
            "rag": {"count": 0, "confidence": 0.0},
            "facts": {"count": 0},
            "graph": {"concepts": [], "confidence": 0.0},
            "episodic": {"count": 0},
            "llm": {"model": "", "provider": ""}
        },
        "metadata": {}
    }
    
    # RAG
    try:
        rag_context = rag.get_context(user_message, user_id=user_id)
        if rag_context:
            result["rag_context"] = rag_context
            result["sources"]["rag"]["count"] = 1
            result["sources"]["rag"]["confidence"] = 0.8
    except Exception as e:
        logger.warning(f"RAG error: {e}")
    
    # Facts
    try:
        facts_context = facts_memory.search(user_message, min_confidence=0.3, limit=3)
        if facts_context:
            result["facts_context"] = facts_context
            result["sources"]["facts"]["count"] = len(facts_context)
    except Exception as e:
        logger.warning(f"Facts error: {e}")
    
    # Episodic
    try:
        similar = episodic_memory.search_episodes(user_message, limit=2, user_id=user_id)
        if similar:
            episodic_text = "\n\n📜 Похожие ситуации из прошлого:\n"
            for ep in similar[:2]:
                episodic_text += f"- {ep.topic}: {ep.user_message[:50]}... "
                episodic_text += f"→ {ep.ai_response[:50]}...\n"
            result["episodic_context"] = episodic_text
            result["sources"]["episodic"]["count"] = len(similar)
    except Exception as e:
        logger.warning(f"Episodic error: {e}")
    
    # Semantic (procedures)
    try:
        procedure = semantic_memory.find_applicable_procedure(user_message)
        if procedure:
            procedure_text = f"\n\n🔧 Процедура '{procedure.name}':\n"
            for i, step in enumerate(procedure.procedure_steps[:3], 1):
                procedure_text += f"  {i}. {step}\n"
            result["procedure_context"] = procedure_text
            result["metadata"]["procedure_used"] = procedure.name
    except Exception as e:
        logger.warning(f"Semantic error: {e}")
    
    # Vector Memory
    try:
        vector_context = vector_memory.search(user_message, min_confidence=0.3, limit=3)
        if vector_context:
            result["vector_context"] = vector_context
            result["metadata"]["vector_memory_used"] = True
            result["metadata"]["vector_records"] = len(vector_context)
    except Exception as e:
        logger.warning(f"VectorMemory error: {e}")
    
    # SmartCache
    try:
        if smartcache.is_negative(user_message):
            result["metadata"]["smartcache_negative"] = True
        else:
            cache_results = smartcache.search(user_message, limit=3)
            if cache_results:
                result["smartcache_context"] = cache_results
                result["metadata"]["smartcache_used"] = True
                result["metadata"]["smartcache_records"] = len(cache_results)
    except Exception as e:
        logger.warning(f"SmartCache error: {e}")
    
    return result