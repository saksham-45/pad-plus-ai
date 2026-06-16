"""
🔄 Pipeline Handlers — Обработчики этапов Pipeline

Модульная архитектура для обработки запросов.
Каждый этап — отдельный обработчик.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("PAD+.pipeline_handlers")


@dataclass
class HandlerResult:
    """Результат обработки этапа"""
    success: bool
    data: Any = None
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "errors": self.errors,
            "metadata": self.metadata
        }


class PipelineHandler(ABC):
    """
    🔄 Базовый класс для обработчиков этапов Pipeline
    
    Каждый этап pipeline реализуется как отдельный обработчик.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def process(self, context: Dict[str, Any]) -> HandlerResult:
        """
        Обрабатывает этап pipeline
        
        Args:
            context: Контекст выполнения (содержит user_message, context, и т.д.)
        
        Returns:
            HandlerResult с результатом обработки
        """
        pass
    
    async def rollback(self, context: Dict[str, Any]):
        """
        Откатывает изменения (опционально)
        
        Args:
            context: Контекст выполнения
        """
        pass
    
    def get_handler_name(self) -> str:
        """Возвращает имя обработчика"""
        return self.__class__.__name__


class SafetyHandler(PipelineHandler):
    """
    🛡️ Обработчик проверки безопасности
    
    Проверяет запрос на наличие опасных инструкций.
    """
    
    async def process(self, context: Dict[str, Any]) -> HandlerResult:
        try:
            from core.safety_layer import get_safety_layer
            
            safety = get_safety_layer()
            result = safety.check_request(context["user_message"])
            
            if result.action.value == "block":
                return HandlerResult(
                    success=False,
                    errors=["SAFETY_BLOCK"],
                    metadata={
                        "warning": result.warning_message,
                        "safety_passed": False
                    }
                )
            
            return HandlerResult(
                success=True,
                data={"action": result.action.value},
                metadata={
                    "safety_passed": True,
                    "safety_warning": result.warning_message if result.action.value == "warn" else None
                }
            )
            
        except Exception as e:
            self.logger.error(f"SafetyHandler error: {type(e).__name__}: {e}")
            return HandlerResult(
                success=True,  # Не блокируем при ошибке
                metadata={"safety_error": str(e)}
            )


class IntentHandler(PipelineHandler):
    """
    🎯 Обработчик классификации намерений
    
    Определяет намерение пользователя и выбирает стратегию.
    """
    
    async def process(self, context: Dict[str, Any]) -> HandlerResult:
        try:
            from core.intent_router import get_router
            
            router = get_router()
            routing = router.route(context["user_message"])
            
            return HandlerResult(
                success=True,
                data={
                    "intent": routing.intent.value,
                    "confidence": routing.confidence,
                    "pipeline": [s.name for s in routing.pipeline[:3]]
                },
                metadata={
                    "intent": routing.intent.value,
                    "intent_confidence": routing.confidence
                }
            )
            
        except Exception as e:
            self.logger.error(f"IntentHandler error: {type(e).__name__}: {e}")
            return HandlerResult(
                success=True,  # Не блокируем при ошибке
                data={"intent": "chat_general", "confidence": 0.5},
                metadata={"intent_error": str(e)}
            )


class RAGHandler(PipelineHandler):
    """
    🧠 Обработчик RAG поиска
    
    Ищет контекст в памяти.
    """
    
    async def process(self, context: Dict[str, Any]) -> HandlerResult:
        try:
            from memory.rag import get_rag
            
            rag = get_rag()
            user_id = context.get("user_id")
            rag_context = rag.get_context(
                context["user_message"],
                user_id=user_id
            )
            
            return HandlerResult(
                success=True,
                data={"context": rag_context},
                metadata={
                    "rag_used": bool(rag_context),
                    "rag_context_length": len(rag_context) if rag_context else 0
                }
            )
            
        except Exception as e:
            self.logger.error(f"RAGHandler error: {type(e).__name__}: {e}")
            return HandlerResult(
                success=True,
                data={"context": ""},
                metadata={"rag_error": str(e), "rag_used": False}
            )


class FactsHandler(PipelineHandler):
    """
    📝 Обработчик поиска фактов
    
    Ищет факты в FactMemory.
    """
    
    async def process(self, context: Dict[str, Any]) -> HandlerResult:
        try:
            from memory.fact_memory_chroma import get_fact_memory_chroma
            
            facts = get_fact_memory_chroma()
            facts_context = facts.search(context["user_message"], min_confidence=0.3, limit=3)
            
            return HandlerResult(
                success=True,
                data={"facts": [f.to_dict() for f in facts_context]},
                metadata={
                    "facts_used": len(facts_context),
                    "fact_memory_used": True
                }
            )
            
        except Exception as e:
            self.logger.error(f"FactsHandler error: {type(e).__name__}: {e}")
            return HandlerResult(
                success=True,
                data={"facts": []},
                metadata={"facts_error": str(e), "facts_used": 0}
            )


class EpisodicHandler(PipelineHandler):
    """
    📖 Обработчик эпизодической памяти
    
    Ищет похожие эпизоды из прошлого.
    """
    
    async def process(self, context: Dict[str, Any]) -> HandlerResult:
        try:
            from memory.episodic import get_episodic_memory
            
            episodic = get_episodic_memory()
            user_id = context.get("user_id")
            similar = episodic.search_episodes(
                context["user_message"],
                limit=2,
                user_id=user_id
            )
            
            episodic_context = ""
            if similar:
                episodic_context = "\n\n📜 Похожие ситуации из прошлого:\n"
                for ep in similar[:2]:
                    episodic_context += f"- {ep.topic}: {ep.user_message[:50]}... "
                    episodic_context += f"→ {ep.ai_response[:50]}...\n"
            
            return HandlerResult(
                success=True,
                data={"episodic_context": episodic_context},
                metadata={
                    "episodic_used": bool(similar),
                    "episodic_count": len(similar)
                }
            )
            
        except Exception as e:
            self.logger.error(f"EpisodicHandler error: {type(e).__name__}: {e}")
            return HandlerResult(
                success=True,
                data={"episodic_context": ""},
                metadata={"episodic_error": str(e), "episodic_used": False}
            )


class GenerateHandler(PipelineHandler):
    """
    🤖 Обработчик генерации ответа
    
    Генерирует ответ через LLM.
    """
    
    async def process(self, context: Dict[str, Any]) -> HandlerResult:
        try:
            from runtime.litellm_service import LiteLLMService
            
            # Формируем промпт
            system_prompt = context.get("system_prompt", "Вы полезный ассистент PAD+ AI.")
            
            # Собираем контекст
            full_context = system_prompt
            
            if context.get("rag_context"):
                full_context += f"\n\n{context['rag_context']}"
            
            if context.get("episodic_context"):
                full_context += f"\n\n{context['episodic_context']}"
            
            # Генерируем ответ
            api_key = context.get("api_key")
            provider = context.get("provider")
            model = context.get("model", "auto")
            
            if not api_key:
                return HandlerResult(
                    success=False,
                    errors=["NO_API_KEY"],
                    metadata={"error": "API key not provided"}
                )
            
            litellm = LiteLLMService(api_key=api_key)
            gen_result = await litellm.generate(
                prompt=context["user_message"],
                system_prompt=full_context,
                api_key=api_key,
                model=model,
                provider=provider
            )
            
            return HandlerResult(
                success=True,
                data={
                    "response": gen_result.text,
                    "provider": gen_result.provider,
                    "confidence": gen_result.confidence
                },
                metadata={
                    "provider": gen_result.provider,
                    "confidence": gen_result.confidence,
                    "model": model
                }
            )
            
        except Exception as e:
            self.logger.error(f"GenerateHandler error: {type(e).__name__}: {e}")
            return HandlerResult(
                success=False,
                errors=[f"GENERATION_ERROR: {type(e).__name__}"],
                metadata={"generation_error": str(e)}
            )
