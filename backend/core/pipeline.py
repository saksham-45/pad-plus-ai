"""
🔄 PipelineExecutor v3.1 — Нервная система NeuroMind AI

Единый пайплайн для каждого запроса:
Safety → Intent → Retrieve → Generate → Verify → Remember → Emit

Новые возможности v3.1:
- Эпизодическая память (контекст ситуации)
- Семантическая память (процедуры и знания)
- Автоматическая консолидация
- Проверка сновидений при простое

Это делает проект настоящим организмом.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import logging
import time

logger = logging.getLogger("neuromind.pipeline")


@dataclass
class PipelineResult:
    """Результат выполнения пайплайна"""
    success: bool
    response: str = ""
    intent: str = ""
    confidence: float = 0.0
    provider: str = ""
    safety_passed: bool = True
    safety_warning: Optional[str] = None
    truth_confidence: float = 0.5
    claims_verified: int = 0
    emotion_style: Dict = field(default_factory=dict)
    rag_used: bool = False
    facts_used: int = 0
    execution_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Новые поля v3.0
    strategy: str = "simple"
    cognitive_load: float = 0.0
    health_score: float = 0.0
    # Новые поля v3.1
    episode_id: Optional[str] = None
    procedure_used: Optional[str] = None
    consolidation_triggered: bool = False
    # Сырой ответ LLM
    raw_llm_response: Optional[Dict] = None
    llm_metadata: Optional[Dict] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "response": self.response,
            "intent": self.intent,
            "confidence": self.confidence,
            "provider": self.provider,
            "safety": {
                "passed": self.safety_passed,
                "warning": self.safety_warning
            },
            "truth": {
                "confidence": self.truth_confidence,
                "claims_verified": self.claims_verified
            },
            "emotion_style": self.emotion_style,
            "rag_used": self.rag_used,
            "facts_used": self.facts_used,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "errors": self.errors,
            "episode_id": self.episode_id,
            "procedure_used": self.procedure_used
        }


class PipelineExecutor:
    """
    🔄 PipelineExecutor v3.1 — единая нервная система

    Порядок:
    1. Safety — проверка безопасности
    2. Intent — классификация намерения
    3. Retrieve — получение контекста (RAG, факты, знания)
    3.1 Episodic — похожие ситуации из прошлого
    3.2 Semantic — процедурные знания
    4. Generate — генерация ответа
    5. Verify — верификация через TruthLoop
    6. Remember — сохранение в память
    6.1 Episodic — сохранение эпизода
    6.2 Consolidation — проверка консолидации
    7. Emit — события
    7.1 Dreams — запись активности
    """

    def __init__(self):
        self._call_count = 0
        self._last_call_time = 0
        self._anti_loop_history: List[str] = []
        self._max_history = 10
        # v3.1: счётчик для консолидации
        self._dialogs_since_consolidation = 0
        self._consolidation_interval = 10
    
    def _check_anti_loop(self, user_message: str) -> Optional[str]:
        """
        Anti-Loop Guard — защита от зацикливания
        
        Проверяет:
        - Повторяющиеся запросы
        - Подобные ответы
        - Циклические паттерны
        """
        normalized = user_message.lower().strip()[:50]
        
        # Проверяем на повтор
        repeat_count = self._anti_loop_history.count(normalized)
        if repeat_count >= 3:
            return "Обнаружен цикл: похожий запрос повторяется. " \
                   "Попробуйте переформулировать."
        
        # Добавляем в историю
        self._anti_loop_history.append(normalized)
        if len(self._anti_loop_history) > self._max_history:
            self._anti_loop_history.pop(0)
        
        return None
    
    async def execute(
        self,
        user_message: str,
        context: Dict = None,
        session_id: str = None
    ) -> PipelineResult:
        """
        Выполняет полный пайплайн обработки
        """
        start_time = time.time()
        result = PipelineResult(success=False)
        
        # === 0. META-COGNITIVE CONTROLLER ===
        strategy = None
        try:
            from core.meta_controller import get_meta_controller, CognitiveState
            meta = get_meta_controller()
            
            # Устанавливаем состояние
            meta.set_state(CognitiveState.PROCESSING)
            
            # Оцениваем нагрузку
            load = meta.evaluate_cognitive_load()
            result.cognitive_load = load.current
            
            # Принимаем решение о стратегии
            strategy = meta.decide_strategy(user_message, context)
            result.strategy = strategy.strategy.value
            result.metadata["strategy_reason"] = strategy.reason
            
            logger.info(f"🧠 Meta: strategy={strategy.strategy.value}, "
                       f"load={load.current:.2f}")
        except Exception as e:
            logger.warning(f"Meta controller error: {e}")
        
        # === 1. ANTI-LOOP GUARD ===
        loop_warning = self._check_anti_loop(user_message)
        if loop_warning:
            result.errors.append(loop_warning)
            result.response = loop_warning
            result.success = True  # Мягкая обработка
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result
        
        # === 2. SAFETY LAYER ===
        try:
            from core.safety_layer import get_safety_layer
            safety = get_safety_layer()
            safety_check = safety.check_request(user_message)
            
            if safety_check.action.value == "block":
                result.safety_passed = False
                result.safety_warning = safety_check.warning_message
                result.response = safety_check.warning_message or \
                    "Запрос заблокирован по соображениям безопасности."
                result.errors.append("SAFETY_BLOCK")
                result.execution_time_ms = (time.time() - start_time) * 1000
                return result
            
            if safety_check.action.value == "warn":
                result.safety_warning = safety_check.warning_message
            
            # Санитизация если нужно
            if safety_check.action.value == "sanitize":
                user_message = safety.sanitize_input(user_message)
                
        except Exception as e:
            logger.warning(f"Safety layer error: {e}")
            result.errors.append(f"Safety: {str(e)}")
        
        # === 3. INTENT ROUTER ===
        intent = "chat_general"
        try:
            from core.intent_router import get_router
            router = get_router()
            routing = router.route(user_message)
            intent = routing.intent.value
            result.intent = intent
            result.metadata["pipeline"] = [
                s.name for s in routing.pipeline[:3]
            ]
        except Exception as e:
            logger.warning(f"Intent router error: {e}")
            result.errors.append(f"Intent: {str(e)}")
        
        # === 4. RETRIEVE CONTEXT ===
        rag_context = ""
        facts_context = []
        
        # RAG
        try:
            from memory.rag import get_rag
            rag = get_rag()
            rag_context = rag.get_context(user_message)
            result.rag_used = bool(rag_context)
        except Exception as e:
            logger.warning(f"RAG error: {e}")
            result.errors.append(f"RAG: {str(e)}")
        
        # Facts
        try:
            from memory.fact_memory import get_fact_memory
            facts = get_fact_memory()
            facts_context = facts.search(user_message, limit=3)
            result.facts_used = len(facts_context)
        except Exception as e:
            logger.warning(f"Facts error: {e}")
        
        # Knowledge Graph
        try:
            from knowledge.graph import get_knowledge_graph
            get_knowledge_graph()
            # Получаем связанные концепции
        except Exception as e:
            logger.warning(f"Knowledge graph error: {e}")

        # === 4.1 EPISODIC MEMORY (похожие ситуации) ===
        episodic_context = ""
        try:
            from memory.episodic import get_episodic_memory
            episodic = get_episodic_memory()
            similar = episodic.search_episodes(user_message, limit=2)

            if similar:
                episodic_context = "\n\n📜 Похожие ситуации из прошлого:\n"
                for ep in similar[:2]:
                    episodic_context += f"- {ep.topic}: {ep.user_message[:50]}... "
                    episodic_context += f"→ {ep.ai_response[:50]}...\n"
        except Exception as e:
            logger.warning(f"Episodic memory error: {e}")

        # === 4.2 SEMANTIC MEMORY (процедуры) ===
        procedure_context = ""
        applicable_procedure = None
        try:
            from memory.semantic import get_semantic_memory
            semantic = get_semantic_memory()
            procedure = semantic.find_applicable_procedure(user_message)

            if procedure:
                applicable_procedure = procedure
                result.procedure_used = procedure.name
                procedure_context = f"\n\n🔧 Процедура '{procedure.name}':\n"
                for i, step in enumerate(procedure.procedure_steps[:3], 1):
                    procedure_context += f"  {i}. {step}\n"
        except Exception as e:
            logger.warning(f"Semantic memory error: {e}")

        # === 5. EMOTION STATE ===
        emotion_state = {}
        emotion_style = {}
        try:
            from emotion.pad_model import get_pad_model
            pad = get_pad_model()
            state = pad.get_state()
            emotion_state = state.to_dict()
            emotion_style = state.get_style()
            result.emotion_style = emotion_style
        except Exception as e:
            logger.warning(f"Emotion error: {e}")
        
        # === 6. PERSONA CONTEXT ===
        persona_context = ""
        try:
            from memory.persona import get_persona
            persona = get_persona()
            persona_context = persona.get_persona_context()
            # Записываем взаимодействие
            persona.record_interaction(
                user_id="default",
                topic=intent,
                emotion=emotion_style.get('tone', 'neutral')
            )
        except Exception as e:
            logger.warning(f"Persona error: {e}")
        
        # === 7. GENERATE RESPONSE ===
        try:
            from llm.session_provider_manager import get_session_manager
            from core.anti_directive import ANTI_DIRECTIVE
            
            # === 7.1. ROOTS MEMORY (фундаментальные принципы) ===
            roots_context = ""
            try:
                from memory.roots import get_roots_memory
                roots = get_roots_memory()
                roots_context = roots.export_for_context(max_items=10)
            except Exception as e:
                logger.warning(f"Roots memory error: {e}")
            
            # Формируем контекст с Roots
            full_context = f"""Ты — NeuroMind AI, цифровой организм.

{roots_context}

Твоя ДНК (ANTI_DIRECTIVE): {ANTI_DIRECTIVE.text}

{persona_context}

Твоё текущее эмоциональное состояние:
- Тон: {emotion_style.get('tone', 'neutral')}
- Уверенность: {emotion_state.get('уверенность', 0.5):.2f}

Стратегия обработки: {result.strategy}

Всегда отвечай на русском. Будь кратким, но глубоким.
Сомневайся в утверждениях. Проверяй факты.
"""

            # Определяем значимость эпизода
            significance = 0.5
            if result.rag_used:
                significance += 0.1
            if result.procedure_used:
                significance += 0.15
            if result.truth_confidence > 0.7:
                significance += 0.1

            episode = episodic.add_episode(
                user_message=user_message,
                ai_response=result.response,
                topic=intent,
                intent=intent,
                significance=min(significance, 1.0),
                emotion=emotion_style.get('tone', 'neutral'),
                concepts=[intent]
            )
            result.episode_id = episode.id
        except Exception as e:
            logger.warning(f"Episodic save error: {e}")

        # === 8.2 CONSOLIDATION (периодическая) ===
        self._dialogs_since_consolidation += 1
        if self._dialogs_since_consolidation >= self._consolidation_interval:
            try:
                from memory.consolidation import get_consolidator
                consolidator = get_consolidator()
                # Запускаем консолидацию асинхронно
                consolidator.run_consolidation()
                result.consolidation_triggered = True
                self._dialogs_since_consolidation = 0
                logger.info("🔄 Consolidation triggered")
            except Exception as e:
                logger.warning(f"Consolidation error: {e}")

        # === 8.3 PROCEDURE SUCCESS (если использовалась процедура) ===
        if applicable_procedure and result.truth_confidence > 0.6:
            try:
                from memory.semantic import get_semantic_memory
                semantic = get_semantic_memory()
                semantic.record_procedure_success(
                    applicable_procedure.id,
                    success=True
                )
            except Exception as e:
                logger.warning(f"Procedure success error: {e}")

        # === 9. UPDATE EMOTION ===
        try:
            from emotion.pad_model import get_pad_model
            pad = get_pad_model()
            # Обновляем эмоцию на основе диалога
            if "ошибка" in result.response.lower() or "проблема" in result.response.lower():
                pad.apply_event("fallback", 0.2)
            else:
                pad.apply_event("new_knowledge", 0.2)
        except Exception as e:
            logger.warning(f"Emotion update error: {e}")
        
        # === 10. PERSONA EVOLUTION ===
        try:
            from memory.persona import get_persona
            persona = get_persona()
            # Эволюция личности на основе диалога
            evolution = persona.evolve_from_dialog(
                user_message=user_message,
                ai_response=result.response
            )
            result.metadata["persona_evolution"] = evolution["changes"]
        except Exception as e:
            logger.warning(f"Persona evolution error: {e}")
        
        # === 11. EMIT EVENTS ===
        try:
            from core.event_bus import get_event_bus, EventType
            bus = get_event_bus()
            bus.emit(
                EventType.DIALOGUE_FINISHED,
                data={
                    "intent": intent,
                    "confidence": result.confidence,
                    "rag_used": result.rag_used
                },
                source="pipeline"
            )
        except Exception as e:
            logger.warning(f"Event emit error: {e}")
        
        # === 12. HEALTH MONITOR ===
        try:
            from core.health_monitor import get_health_monitor
            health = get_health_monitor()
            
            # Записываем событие успешного диалога
            if result.success:
                health.record_event("good_dialog", 1.0)
                if result.rag_used:
                    health.record_event("learned_fact", 0.5)
            
            # Получаем текущий score
            health_assessment = health.assess_health()
            result.health_score = health_assessment["overall_score"]
        except Exception as e:
            logger.warning(f"Health monitor error: {e}")
        
        # === 13. META-COGNITIVE FINALIZATION ===
        try:
            from core.meta_controller import get_meta_controller, CognitiveState
            meta = get_meta_controller()

            # Адаптация на основе результата
            meta.adapt({
                "success": result.success,
                "strategy": result.strategy,
                "response_time": result.execution_time_ms / 1000
            })

            # Возвращаем состояние в idle
            meta.set_state(CognitiveState.IDLE)
        except Exception as e:
            logger.warning(f"Meta finalization error: {e}")

        # === 14. DREAMS (запись активности) ===
        try:
            from core.dreams import get_dream_system
            dreams = get_dream_system()
            dreams.record_activity()
        except Exception as e:
            logger.warning(f"Dreams record error: {e}")

        # === FINALIZE ===
        result.success = True
        result.execution_time_ms = (time.time() - start_time) * 1000
        self._call_count += 1
        
        logger.info(
            f"✅ Pipeline: {intent} | {result.strategy} | "
            f"{result.execution_time_ms:.0f}ms | conf={result.confidence:.2f} | "
            f"health={result.health_score:.2f}"
        )
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика пайплайна"""
        return {
            "total_calls": self._call_count,
            "anti_loop_history_size": len(self._anti_loop_history),
            "dialogs_since_consolidation": self._dialogs_since_consolidation,
            "consolidation_interval": self._consolidation_interval,
            "version": "3.1"
        }


# Глобальный экземпляр
_pipeline: Optional[PipelineExecutor] = None


def get_pipeline() -> PipelineExecutor:
    """Возвращает глобальный пайплайн"""
    global _pipeline
    if _pipeline is None:
        _pipeline = PipelineExecutor()
    return _pipeline