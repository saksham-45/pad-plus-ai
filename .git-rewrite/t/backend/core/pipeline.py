"""
🔄 PipelineExecutor v3.2 — Нервная система PAD+ AI (с Fail Strategy)

Единый пайплайн для каждого запроса:
Safety → Intent → Retrieve → Generate → Verify → Remember → Emit

Новые возможности v3.2 (Hardening):
- Fail Strategy — явная обработка ошибок с деградацией
- PipelineState — отслеживание состояния пайплайна
- DegradationInfo — информация о деградировавших компонентах
- Метрики и мониторинг через MetricsCollector
- Circuit Breaker для БД

v3.1:
- Эпизодическая память (контекст ситуации)
- Семантическая память (процедуры и знания)
- Автоматическая консолидация
- Проверка сновидений при простое
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import logging
import time
import asyncio

logger = logging.getLogger("padplus.pipeline")


class PipelineState(str, Enum):
    """Состояния пайплайна"""
    HEALTHY = "healthy"       # Все компоненты работают
    DEGRADED = "degraded"     # Часть компонентов недоступна
    FAILED = "failed"         # Критическая ошибка


@dataclass
class DegradationInfo:
    """Информация о деградации компонента"""
    component: str
    error: str
    fallback_applied: bool = False
    severity: str = "medium"  # "low", "medium", "high"
    
    def to_dict(self) -> dict:
        return {
            "component": self.component,
            "error": self.error,
            "fallback_applied": self.fallback_applied,
            "severity": self.severity,
        }

# === ФАЗА 1: Импорт для работы с пользовательскими ключами ===
from runtime.litellm_service import LiteLLMService


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
    
    # === ИСТОЧНИКИ ИНФОРМАЦИИ (НОВОЕ!) ===
    sources: Dict[str, Any] = field(default_factory=dict)
    # Формат:
    # {
    #   "rag": {"count": 3, "confidence": 0.8},
    #   "graph": {"concepts": ["физика", "частицы"], "confidence": 0.7},
    #   "llm": {"model": "openai/gpt-4", "provider": "OpenAI"},
    #   "memory": {"episodes": 2, "facts": 5}
    # }

    def to_dict(self, explain: bool = False) -> dict:
        """
        Преобразует результат в словарь
        
        Args:
            explain: Если True, добавляет расширенные когнитивные мета-данные
        """
        # Базовый ответ
        result = {
            # === ОСНОВНОЙ ОТВЕТ ===
            "answer": self.response,
            "success": self.success,
            
            # === КОГНИТИВНЫЕ МЕТА-ДАННЫЕ ===
            "cognitive": {
                "strategy": self.strategy,
                "confidence": round(self.confidence, 3),
                "health_score": round(self.health_score, 3),
                "execution_time_ms": round(self.execution_time_ms, 2),
                "cognitive_load": round(self.cognitive_load, 3)
            },
            
            # === ПАМЯТЬ ===
            "memory": {
                "rag_used": self.rag_used,
                "facts_used": self.facts_used,
                "episode_id": self.episode_id,
                "procedure_used": self.procedure_used,
                "sources": self.sources
            },
            
            # === ЭМОЦИИ ===
            "emotion": {
                "style": self.emotion_style,
                "truth_confidence": round(self.truth_confidence, 3)
            },
            
            # === МЕТА-ИНФОРМАЦИЯ ===
            "meta": {
                "intent": self.intent,
                "provider": self.provider,
                "errors": self.errors,
                "metadata": self.metadata
            },
            
            # === БЕЗОПАСНОСТЬ ===
            "safety": {
                "passed": self.safety_passed,
                "warning": self.safety_warning
            }
        }
        
        # === TRUTH LOOP МЕТРИКИ ===
        result["truth"] = {
            "confidence": round(self.truth_confidence, 3),
            "claims_verified": self.claims_verified,
            "status": self._get_truth_status(),
            "sources_count": self._get_sources_count()
        }
        
        # === X-RAY СЕКЦИЯ (при explain=true) ===
        if explain:
            result["xray"] = self._generate_xray_insights()
        
        return result
    
    def _get_truth_status(self) -> str:
        """Определяет статус верификации"""
        if self.truth_confidence >= 0.8:
            return "verified"
        elif self.truth_confidence >= 0.5:
            return "partial"
        else:
            return "unverified"
    
    def _get_sources_count(self) -> int:
        """Подсчитывает общее количество источников"""
        count = 0
        if self.sources:
            count += self.sources.get("rag", {}).get("count", 0)
            count += self.sources.get("facts", {}).get("count", 0)
            count += self.sources.get("episodic", {}).get("count", 0)
        return count
    
    def _generate_xray_insights(self) -> dict:
        """Генерирует X-Ray инсайты для режима explain"""
        # Описания стратегий
        strategy_descriptions = {
            "simple": "Прямая генерация ответа",
            "retrieval": "Поиск и синтез информации",
            "reasoning": "Логический анализ",
            "creative": "Творческая генерация",
            "analytical": "Аналитическая обработка"
        }
        
        # Определяем стадии пайплайна
        pipeline_stages = ["safety", "intent"]
        if self.rag_used:
            pipeline_stages.append("retrieval")
        if self.facts_used > 0:
            pipeline_stages.append("facts")
        if self.episode_id:
            pipeline_stages.append("episodic")
        pipeline_stages.extend(["generate", "verify", "remember"])
        
        return {
            "strategy": self.strategy,
            "strategy_description": strategy_descriptions.get(self.strategy, "Обработка запроса"),
            "pipeline_stages": pipeline_stages,
            "memory_usage": {
                "rag": self.rag_used,
                "facts": self.facts_used > 0,
                "episodic": self.episode_id is not None,
                "procedure": self.procedure_used is not None
            },
            "verification": {
                "status": self._get_truth_status(),
                "confidence": round(self.truth_confidence, 3),
                "claims_verified": self.claims_verified
            },
            "performance": {
                "execution_time_ms": round(self.execution_time_ms, 2),
                "health_score": round(self.health_score, 3),
                "cognitive_load": round(self.cognitive_load, 3)
            }
        }


class PipelineExecutor:
    """
    🔄 PipelineExecutor v3.2 — единая нервная система с Fail Strategy

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

    Fail Strategy (v3.2):
    - Отслеживание состояния пайплайна (HEALTHY/DEGRADED/FAILED)
    - Явная обработка ошибок с деградацией
    - Fallback для критических компонентов
    - Информирование пользователя о деградации
    """

    # Критические компоненты — при их отказе пайплайн останавливается
    CRITICAL_COMPONENTS = {"safety", "litellm"}
    
    # Важные компоненты — при отказе переходим в degraded mode
    IMPORTANT_COMPONENTS = {"rag", "facts", "episodic", "semantic"}

    def __init__(self):
        self._call_count = 0
        self._last_call_time = 0
        self._anti_loop_history: List[str] = []
        self._max_history = 10
        # v3.1: счётчик для консолидации
        self._dialogs_since_consolidation = 0
        self._consolidation_interval = 10
        
        # === ИСПРАВЛЕНИЕ 1: asyncio.Lock для потокобезопасности ===
        self._consolidation_lock = asyncio.Lock()
        
        # === V3.2: Fail Strategy состояние ===
        self._state = PipelineState.HEALTHY
        self._degradations: List[DegradationInfo] = []
    
    def _mark_degraded(self, component: str, error: str, severity: str = "medium", fallback_applied: bool = False):
        """Отмечает компонент как деградировавший"""
        degradation = DegradationInfo(
            component=component,
            error=error,
            fallback_applied=fallback_applied,
            severity=severity
        )
        self._degradations.append(degradation)
        
        # Если критический компонент — повышаем уровень
        if component in self.CRITICAL_COMPONENTS and severity == "high":
            self._state = PipelineState.FAILED
        elif self._degradations:
            self._state = PipelineState.DEGRADED
        
        logger.warning(f"⚠️ Компонент '{component}' деградировал: {error} (severity={severity})")
    
    def _should_stop_on_degradation(self, component: str) -> bool:
        """Определяет, нужно ли останавливать пайплайн"""
        if component in self.CRITICAL_COMPONENTS:
            return len([d for d in self._degradations if d.component in self.CRITICAL_COMPONENTS]) >= 1
        return False
    
    def _create_error_result(self, message: str, start_time: float) -> PipelineResult:
        """Создает результат с ошибкой"""
        result = PipelineResult(
            success=False,
            response=message,
            execution_time_ms=(time.time() - start_time) * 1000,
        )
        result.metadata["pipeline_state"] = self._state.value
        result.metadata["degradations"] = [d.to_dict() for d in self._degradations]
        return result
    
    def _create_degraded_system_prompt(self, base_prompt: str) -> str:
        """Создает упрощенный промпт для degraded mode"""
        degraded_notice = "\n\n⚠️ ВНИМАНИЕ: Система работает в ограниченном режиме. "
        degraded_notice += "Некоторые компоненты временно недоступны. "
        degraded_notice += "Отвечай максимально осторожно и указывай на возможные неточности."
        return base_prompt + degraded_notice
    
    def _format_degradation_notice(self) -> str:
        """Форматирует уведомление о деградации для пользователя"""
        if not self._degradations:
            return ""
        
        notice = "\n\n---\n⚠️ **Примечание:** "
        high_severity = [d for d in self._degradations if d.severity == "high"]
        
        if high_severity:
            notice += "Система работает в ограниченном режиме. "
        
        degraded_components = ", ".join(d.component for d in self._degradations)
        notice += f"Временно недоступны: {degraded_components}."
        
        return notice
    
    def _reset_fail_state(self):
        """Сбрасывает состояние Fail Strategy после успешного выполнения"""
        self._state = PipelineState.HEALTHY
        self._degradations.clear()
    
    def _get_fallback_rag_context(self, query: str) -> str:
        """Fallback для RAG — простой поиск по ключевым словам"""
        # Простая эвристика вместо векторного поиска
        keywords = query.lower().split()[:5]
        return f"[RAG недоступен. Ключевые слова: {', '.join(keywords)}]"
    
    def _record_metrics(self, start_time: float, result: PipelineResult):
        """Записывает метрики выполнения"""
        from core.metrics_collector import get_metrics
        metrics = get_metrics()
        
        duration_ms = (time.time() - start_time) * 1000
        
        metrics.increment("pipeline_requests_total")
        metrics.record_duration("pipeline_duration_ms", duration_ms)
        
        if result.success:
            metrics.increment("pipeline_success_total")
        else:
            metrics.increment("pipeline_errors_total")
        
        if self._state == PipelineState.DEGRADED:
            metrics.increment("pipeline_degraded_total")
        
        metrics.set_gauge("pipeline_active_state", 
                        0 if self._state == PipelineState.HEALTHY else 
                        1 if self._state == PipelineState.DEGRADED else 2)
    
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
        session_id: str = None,
        api_key: Optional[str] = None,      # === ФАЗА 1: API ключ пользователя ===
        provider: Optional[str] = None      # === ФАЗА 1: Провайдер пользователя ===
    ) -> PipelineResult:
        """
        Выполняет полный пайплайн обработки
        
        Args:
            user_message: Сообщение пользователя
            context: Контекст (user_id, key_id, и т.д.)
            session_id: ID сессии
            api_key: API ключ пользователя (если есть)
            provider: Провайдер пользователя (google, groq, openai, etc.)
        
        Returns:
            PipelineResult с результатом обработки
        """
        start_time = time.time()
        result = PipelineResult(success=False)
        
        # === 0. СТРАТЕГИЯ ОБРАБОТКИ (встроенная логика) ===
        text_lower = user_message.lower().strip()
        
        # Определяем стратегию напрямую без промежуточного Brain
        if any(kw in text_lower for kw in ['почему ты', 'как ты', 'что ты думаешь о себе', 'саморефлексия']):
            result.strategy = "reflective"
        elif any(kw in text_lower for kw in ['запомни', 'выучи', 'новый факт', 'добавь в память', 'сохрани']):
            result.strategy = "learning"
        elif any(kw in text_lower for kw in ['придумай', 'сочини', 'придумай историю', 'креативно', 'оригинально', 'необычно']):
            result.strategy = "creative"
        elif sum(1 for kw in ['почему', 'как работает', 'объясни', 'проанализируй', 'сравни', 'разбери', 'детально', 'подробно', 'глубоко'] if kw in text_lower) >= 2 or (len(user_message) > 50 and 'почему' in text_lower):
            result.strategy = "reasoning"
        elif any(kw in text_lower for kw in ['привет', 'здравствуй', 'как дела', 'что делаешь', 'спасибо', 'пока', 'до свидания', 'ок', 'хорошо']):
            result.strategy = "simple"
        elif len(user_message) < 20:
            result.strategy = "simple"
        elif len(user_message) < 100:
            result.strategy = "retrieval"
        else:
            result.strategy = "reasoning"
        
        result.metadata["strategy_selected"] = result.strategy
        logger.info(f"✅ Стратегия выбрана: {result.strategy}")
        
        # === 1. ANTI-LOOP GUARD ===
        loop_warning = self._check_anti_loop(user_message)
        if loop_warning:
            result.errors.append(loop_warning)
            result.response = loop_warning
            result.success = True  # Мягкая обработка
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result
        
        # === 2. SAFETY LAYER ===
        from core.error_handler import get_error_handler, ErrorSeverity
        error_handler = get_error_handler()

        async def safety_step():
            nonlocal user_message
            
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
            return None

        safety_result = await error_handler.try_execute(
            component="safety_layer",
            func=safety_step,
            severity=ErrorSeverity.HIGH,
            notify_user=True,
            user_message="Система безопасности временно недоступна"
        )

        if safety_result is not None:
            return safety_result
        
        # === 3. INTENT ROUTER ===
        intent = "chat_general"

        async def intent_step():
            from core.intent_router import get_router
            router = get_router()
            routing = router.route(user_message)
            intent = routing.intent.value
            result.intent = intent
            result.metadata["pipeline"] = [
                s.name for s in routing.pipeline[:3]
            ]
            return intent

        intent_result = await error_handler.try_execute(
            component="intent_router",
            func=intent_step,
            fallback_value="chat_general",
            severity=ErrorSeverity.MEDIUM,
            notify_user=False
        )

        intent = intent_result if intent_result is not None else "chat_general"
        
        # === 4. RETRIEVE CONTEXT ===
        rag_context = ""
        facts_context = []
        
        # Инициализация источников
        result.sources = {
            "rag": {"count": 0, "confidence": 0.0},
            "facts": {"count": 0},
            "graph": {"concepts": [], "confidence": 0.0},
            "episodic": {"count": 0},
            "llm": {"model": "", "provider": ""}
        }

        # RAG
        async def rag_step():
            from memory.rag import get_rag
            rag = get_rag()
            user_id = context.get('user_id') if context else None
            context_data = rag.get_context(user_message, user_id=user_id)
            
            if context_data:
                result.sources["rag"]["count"] = 1
                result.sources["rag"]["confidence"] = 0.8
                result.rag_used = True
            
            return context_data

        rag_context = await error_handler.try_execute(
            component="rag",
            func=rag_step,
            fallback=self._get_fallback_rag_context,
            fallback_value="",
            severity=ErrorSeverity.MEDIUM,
            notify_user=False
        )

        # Facts
        async def facts_step():
            from memory.fact_memory_chroma import get_fact_memory_chroma
            facts = get_fact_memory_chroma()
            context_data = facts.search(user_message, min_confidence=0.3, limit=3)
            result.facts_used = len(context_data)
            
            if context_data:
                result.sources["facts"]["count"] = len(context_data)
            
            return context_data

        facts_context = await error_handler.try_execute(
            component="facts_memory",
            func=facts_step,
            fallback_value=[],
            severity=ErrorSeverity.LOW,
            notify_user=False
        )

        # === ЭТАП 6: Интеграция VectorMemoryChroma (долговременная память) ===
        async def vector_memory_step():
            from memory.vector_memory_chroma import get_vector_memory_chroma
            vector_mem = get_vector_memory_chroma()
            vector_context = vector_mem.search(user_message, min_confidence=0.3, limit=3)
            if vector_context:
                result.metadata["vector_memory_used"] = True
                result.metadata["vector_records"] = len(vector_context)
            return vector_context

        vector_context = await error_handler.try_execute(
            component="vector_memory",
            func=vector_memory_step,
            fallback_value=[],
            severity=ErrorSeverity.LOW,
            notify_user=False
        )

        # === ЭТАП 7: Интеграция SmartCacheChroma (кратковременная память) ===
        async def smartcache_step():
            from memory.smartcache_chroma import get_smartcache_chroma
            smartcache = get_smartcache_chroma()
            
            # Проверяем отрицательный кэш
            if smartcache.is_negative(user_message):
                result.metadata["smartcache_negative"] = True
            else:
                # Ищем в кэше
                cache_results = smartcache.search(user_message, limit=3)
                if cache_results:
                    result.metadata["smartcache_used"] = True
                    result.metadata["smartcache_records"] = len(cache_results)

        await error_handler.try_execute(
            component="smartcache",
            func=smartcache_step,
            severity=ErrorSeverity.LOW,
            notify_user=False
        )
        
        # Knowledge Graph
        async def knowledge_graph_step():
            from knowledge.graph import get_knowledge_graph
            graph = get_knowledge_graph()
            # Получаем связанные концепции
            concepts = graph.get_related_concepts(user_message)
            if concepts:
                result.sources["graph"]["concepts"] = concepts[:5]
                result.sources["graph"]["confidence"] = 0.7
            return concepts

        await error_handler.try_execute(
            component="knowledge_graph",
            func=knowledge_graph_step,
            severity=ErrorSeverity.LOW,
            notify_user=False
        )

        # === 4.1 EPISODIC MEMORY (похожие ситуации) ===
        async def episodic_step():
            from memory.episodic import get_episodic_memory
            episodic = get_episodic_memory()
            user_id = context.get('user_id') if context else None
            similar = episodic.search_episodes(user_message, limit=2, user_id=user_id)
            
            if similar:
                context_data = "\n\n📜 Похожие ситуации из прошлого:\n"
                for ep in similar[:2]:
                    context_data += f"- {ep.topic}: {ep.user_message[:50]}... "
                    context_data += f"→ {ep.ai_response[:50]}...\n"
                
                result.sources["episodic"]["count"] = len(similar)
                return context_data
            
            return ""

        episodic_context = await error_handler.try_execute(
            component="episodic_memory",
            func=episodic_step,
            fallback_value="",
            severity=ErrorSeverity.LOW,
            notify_user=False
        )

        # === 4.2 SEMANTIC MEMORY (процедуры) ===
        procedure_context = ""
        applicable_procedure = None

        async def semantic_step():
            from memory.semantic import get_semantic_memory
            semantic = get_semantic_memory()
            procedure = semantic.find_applicable_procedure(user_message)

            if procedure:
                applicable_procedure = procedure
                result.procedure_used = procedure.name
                procedure_context = f"\n\n🔧 Процедура '{procedure.name}':\n"
                for i, step in enumerate(procedure.procedure_steps[:3], 1):
                    procedure_context += f"  {i}. {step}\n"

            return procedure, procedure_context

        semantic_result = await error_handler.try_execute(
            component="semantic_memory",
            func=semantic_step,
            fallback_value=(None, ""),
            severity=ErrorSeverity.LOW,
            notify_user=False
        )

        if semantic_result:
            applicable_procedure, procedure_context = semantic_result

        # === 5. EMOTION STATE ===
        emotion_state = {}
        emotion_style = {}

        async def emotion_step():
            from emotion.pad_model import get_pad_model
            pad = get_pad_model()
            state = pad.get_state()
            emotion_state = state.to_dict()
            emotion_style = state.get_style()
            result.emotion_style = emotion_style
            return emotion_state, emotion_style

        emotion_result = await error_handler.try_execute(
            component="emotion_model",
            func=emotion_step,
            fallback_value=({}, {}),
            severity=ErrorSeverity.LOW,
            notify_user=False
        )

        if emotion_result:
            emotion_state, emotion_style = emotion_result
        
        # === 6. PERSONA CONTEXT ===
        persona_context = ""

        async def persona_step():
            # === ФАЗА 4: Персонализация — используем UserPersona ===
            from memory.user_persona import get_user_persona_manager
            
            user_id = context.get('user_id') if context else None
            
            if user_id:
                # Персональная личность для пользователя
                persona_manager = get_user_persona_manager()
                user_persona = persona_manager.get_persona(user_id)
                persona_context = user_persona.get_context_for_prompt() or ""
                
                # Записываем взаимодействие
                user_persona.record_interaction(topic=intent)
                persona_manager.save_persona(user_persona)
            else:
                # Общая личность (без персонализации)
                from memory.persona import get_persona
                persona = get_persona()
                persona_context = persona.get_persona_context()
            
            return persona_context

        persona_context = await error_handler.try_execute(
            component="persona_system",
            func=persona_step,
            fallback_value="",
            severity=ErrorSeverity.LOW,
            notify_user=False
        )
        
        # === 7. GENERATE RESPONSE ===
        try:
            from runtime.litellm_service import get_litellm_service
            from core.anti_directive import ANTI_DIRECTIVE
            import os

            # === 7.1. ROOTS MEMORY (фундаментальные принципы) ===
            roots_context = ""

            async def roots_step():
                from memory.roots import get_roots_memory
                roots = get_roots_memory()
                roots_context = roots.export_for_context(max_items=10)
                return roots_context

            roots_context = await error_handler.try_execute(
                component="roots_memory",
                func=roots_step,
                fallback_value="",
                severity=ErrorSeverity.LOW,
                notify_user=False
            )

            # Формируем контекст с Roots
            full_context = f"""{roots_context}

{persona_context}

Твоё текущее эмоциональное состояние:
- Тон: {emotion_style.get('tone', 'neutral')}
- Уверенность: {emotion_state.get('уверенность', 0.5):.2f}

Стратегия обработки: {result.strategy}

Всегда отвечай на русском. Будь кратким, но глубоким.
Сомневайся в утверждениях. Проверяй факты.
Отвечай естественно, без самоидентификации.
"""

            # === 7.2 GENERATE RESPONSE через LiteLLM ===
            # === ФАЗА 1: ИСПОЛЬЗУЕМ API КЛЮЧ ПОЛЬЗОВАТЕЛЯ ===
            
            # Проверяем, передан ли ключ напрямую в Pipeline
            user_api_key = api_key  # Из параметра метода execute()
            user_provider = provider  # Из параметра метода execute()
            model = None

            logger.info(f"🔑 Pipeline: api_key_len={len(user_api_key) if user_api_key else 0}, provider={user_provider}, model={model}")

            # Если ключ не передан, пытаемся получить из сессии
            if not user_api_key and session_id:
                try:
                    from runtime.session_provider_manager import get_session_manager
                    session_manager = get_session_manager()
                    user_manager = session_manager.create_user_manager(session_id)

                    if user_manager.litellm_service:
                        # Используем ключ пользователя из сессии
                        user_api_key = user_manager.litellm_service.default_api_key
                        model = user_manager.litellm_service.default_model
                        # provider определяем из ключа (будет добавлен позже)
                except Exception as e:
                    logger.warning(f"Ошибка получения ключа сессии: {e}")

            if not user_api_key:
                # Fallback: нет ключа пользователя
                result.response = "У меня нет подключенного API ключа. Пожалуйста, добавьте ключ в настройках."
                result.provider = "no_api_key"
                result.confidence = 0.0
            else:
                # === ФАЗА 1: Создаём LiteLLMService с ключом пользователя ===
                litellm = LiteLLMService(api_key=user_api_key)
                
                gen_result = await litellm.generate(
                    prompt=user_message,
                    system_prompt=full_context,
                    api_key=user_api_key,
                    model=model,
                    provider=user_provider  # Передаём провайдера явно
                )

                result.response = gen_result.text
                result.provider = gen_result.provider
                result.confidence = gen_result.confidence
                
                # Записываем источник LLM
                result.sources["llm"]["model"] = gen_result.model
                result.sources["llm"]["provider"] = gen_result.provider

            # === ЭТАП 5: VERIFY (верификация через TruthLoop) ===
            async def truth_loop_step():
                from core.truth_loop import get_truth_loop
                truth = get_truth_loop()
                
                # Извлекаем утверждения из ответа
                claims = truth.extract_claims(result.response)
                
                if claims:
                    # Проверяем утверждения
                    verified = truth.verify_claims(claims)
                    result.truth_confidence = verified.get('overall_confidence', 0.5)
                    result.claims_verified = len(verified.get('verified_claims', []))
                    
                    # Если низкая уверенность — добавляем дисклеймер
                    if result.truth_confidence < 0.5:
                        result.response = f"{result.response}\n\n⚠️ Примечание: Эта информация требует дополнительной проверки."
                    
                    # Добавляем информацию об источниках
                    sources_info = []
                    if result.sources["rag"]["count"] > 0:
                        sources_info.append(f"📚 RAG: {result.sources['rag']['count']} источников (уверенность: {result.sources['rag']['confidence']:.0%})")
                    if result.sources["facts"]["count"] > 0:
                        sources_info.append(f"📝 Факты: {result.sources['facts']['count']} найдено")
                    if result.sources["episodic"]["count"] > 0:
                        sources_info.append(f"📜 Эпизоды: {result.sources['episodic']['count']} найдено")
                    if result.sources["llm"]["model"]:
                        sources_info.append(f"🤖 LLM: {result.sources['llm']['provider']} ({result.sources['llm']['model']})")
                    
                    if sources_info:
                        result.response += "\n\n---\n🔍 **Источники информации:**\n" + "\n".join(sources_info)
                        result.response += f"\n\n📊 **Общая уверенность:** {result.truth_confidence:.0%}"

                return result.truth_confidence

            result.truth_confidence = await error_handler.try_execute(
                component="truth_loop",
                func=truth_loop_step,
                fallback_value=0.5,
                severity=ErrorSeverity.LOW,
                notify_user=False
            )

            # Определяем значимость эпизода
            significance = 0.5
            if result.rag_used:
                significance += 0.1
            if result.procedure_used:
                significance += 0.15
            if result.truth_confidence > 0.7:
                significance += 0.1

            # === ФАЗА 3: Персонализация — передаём user_id ===
            user_id = context.get('user_id') if context else None

            # Преобразуем emotion_style в формат для эпизодической памяти
            # emotion_style имеет структуру {"tone": "...", "verbosity": "...", "color": "..."}
            # а episodic ожидает {"уверенность": float, "удовольствие": float, ...}
            emotion_before_dict = {
                "уверенность": float(emotion_state.get("уверенность", 0.5)),
                "удовольствие": float(emotion_state.get("удовольствие", 0.0)),
                "возбуждение": float(emotion_state.get("возбуждение", 0.0)),
            }

            # Подготавливаем безопасные значения для всех параметров
            safe_intent = intent if intent else "unknown"
            safe_topic = safe_intent
            safe_concepts = [safe_intent]
            safe_user_id = user_id  # Может быть None для общих записей

            # Сохранение эпизода
            async def save_episode_step():
                from memory.episodic import get_episodic_memory
                episodic = get_episodic_memory()
                episode = episodic.add_episode(
                    user_message=str(user_message) if user_message else "",
                    ai_response=str(result.response) if result.response else "",
                    topic=safe_topic,
                    intent=safe_intent,
                    significance=min(significance, 1.0),
                    emotion_before=emotion_before_dict,
                    emotion_after={},
                    concepts=safe_concepts,
                    user_id=safe_user_id
                )
                return episode.id

            episode_id = await error_handler.try_execute(
                component="episodic_save",
                func=save_episode_step,
                fallback_value=None,
                severity=ErrorSeverity.LOW,
                notify_user=False
            )

            if episode_id:
                result.episode_id = episode_id
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.warning(f"Episodic save error: {type(e).__name__}: {e}")
            logger.warning(f"Episodic save traceback: {tb}")

        # === 8.2 CONSOLIDATION (периодическая) ===
        # === ИСПРАВЛЕНИЕ 1: Блокировка для потокобезопасности ===
        async with self._consolidation_lock:
            self._dialogs_since_consolidation += 1
            if self._dialogs_since_consolidation >= self._consolidation_interval:

                async def consolidation_step():
                    from memory.consolidation import get_consolidator
                    consolidator = get_consolidator()
                    # === ФАЗА 5: Персонализация — передаём user_id ===
                    user_id = context.get('user_id') if context else None
                    # Запускаем консолидацию асинхронно
                    consolidator.run_scheduled_consolidation(user_id=user_id)
                    result.consolidation_triggered = True
                    self._dialogs_since_consolidation = 0
                    logger.info("🔄 Consolidation triggered")

                await error_handler.try_execute(
                    component="consolidator",
                    func=consolidation_step,
                    severity=ErrorSeverity.LOW,
                    notify_user=False
                )

        # === 8.3 PROCEDURE SUCCESS (если использовалась процедура) ===
        if applicable_procedure and result.truth_confidence > 0.6:
            async def procedure_success_step():
                from memory.semantic import get_semantic_memory
                semantic = get_semantic_memory()
                semantic.record_procedure_success(
                    applicable_procedure.id,
                    success=True
                )

            await error_handler.try_execute(
                component="semantic_memory_success",
                func=procedure_success_step,
                severity=ErrorSeverity.LOW,
                notify_user=False
            )

        # === ЭТАП 8: Сохранение в VectorMemory (долговременная память) ===
        async def vector_save_step():
            from memory.vector_memory_chroma import get_vector_memory_chroma
            vector_mem = get_vector_memory_chroma()
            # Сохраняем диалог в долговременную память
            vector_mem.store(
                text=f"User: {user_message}\nAI: {result.response}",
                source="dialog",
                confidence=result.confidence,
                depth=1
            )

        await error_handler.try_execute(
            component="vector_memory_save",
            func=vector_save_step,
            severity=ErrorSeverity.LOW,
            notify_user=False
        )

        # === ЭТАП 9: Сохранение в SmartCache (кратковременная память) ===
        async def smartcache_save_step():
            from memory.smartcache_chroma import get_smartcache_chroma
            smartcache = get_smartcache_chroma()
            # Сохраняем вопрос и ответ в кэш
            smartcache.store(
                text=f"Q: {user_message}\nA: {result.response}",
                source="dialog",
                confidence=result.confidence,
                ttl=3600  # 1 час
            )

        await error_handler.try_execute(
            component="smartcache_save",
            func=smartcache_save_step,
            severity=ErrorSeverity.LOW,
            notify_user=False
        )

        # === 10. UPDATE EMOTION ===
        async def emotion_update_step():
            from emotion.pad_model import get_pad_model
            pad = get_pad_model()
            # Обновляем эмоцию на основе диалога
            if "ошибка" in result.response.lower() or "проблема" in result.response.lower():
                pad.apply_event("fallback", 0.2)
            else:
                pad.apply_event("new_knowledge", 0.2)

        await error_handler.try_execute(
            component="emotion_update",
            func=emotion_update_step,
            severity=ErrorSeverity.LOW,
            notify_user=False
        )
        
        # === 10. PERSONA EVOLUTION ===
        async def persona_evolution_step():
            # === ФАЗА 4: Персонализация — эволюция UserPersona ===
            from memory.user_persona import get_user_persona_manager
            
            user_id = context.get('user_id') if context else None
            
            if user_id:
                # Эволюция персональной личности
                persona_manager = get_user_persona_manager()
                user_persona = persona_manager.get_persona(user_id)
                
                # Анализируем диалог для эволюции
                msg_lower = user_message.lower()
                
                # Если вопрос о фактах — растёт technical_level
                if any(w in msg_lower for w in ["правда", "факт", "точно", "верно"]):
                    user_persona.adjust_style("technical_level", 0.01, "фактологический вопрос")
                
                # Если философский вопрос — растёт humor_level
                if any(w in msg_lower for w in ["почему", "смысл", "суть", "думаю"]):
                    user_persona.adjust_style("formality", -0.01, "философский вопрос")
                
                # Если пользователь благодарит — растём empathy
                if any(w in msg_lower for w in ["спасибо", "благодар", "помог", "отлично"]):
                    user_persona.adjust_style("verbosity", 0.01, "положительная обратная связь")
                
                # Сохраняем эволюцию
                persona_manager.save_persona(user_persona)
                
                result.metadata["user_persona_evolved"] = True
            else:
                # Эволюция общей личности
                from memory.persona import get_persona
                persona = get_persona()
                evolution = persona.evolve_from_dialog(
                    user_message=user_message,
                    ai_response=result.response
                )
                result.metadata["persona_evolution"] = evolution["changes"]

        await error_handler.try_execute(
            component="persona_evolution",
            func=persona_evolution_step,
            severity=ErrorSeverity.LOW,
            notify_user=False
        )
        
        # === 11. EMIT EVENTS + WEBSOCKET BROADCAST ===
        async def events_broadcast_step():
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

            # === BROADCAST MIND-STATE UPDATE через WebSocket ===
            bus.emit(
                EventType.MIND_STATE_UPDATE,
                data={"trigger": "dialogue_finished"},
                source="pipeline"
            )

        await error_handler.try_execute(
            component="event_bus_broadcast",
            func=events_broadcast_step,
            severity=ErrorSeverity.LOW,
            notify_user=False
        )
        
        # === 12. HEALTH MONITOR ===
        async def health_monitor_step():
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

        await error_handler.try_execute(
            component="health_monitor",
            func=health_monitor_step,
            severity=ErrorSeverity.LOW,
            notify_user=False
        )
        
        # === 13. X-RAY REFLECTION & META-COGNITIVE FINALIZATION ===
        async def reflection_finalization_step():
            # X-Ray Reflection Loop (анализ результата)
            from core.xray.reflection import get_reflection_loop
            from core.xray.system_state import get_system_state_manager
            
            reflection = get_reflection_loop()
            state_manager = get_system_state_manager()
            
            # Обновляем состояние системы
            state_manager.update(result.to_dict())
            
            # Старая мета-когнитивная финализация (оставляем для совместимости)
            from core.meta_controller import get_meta_controller, CognitiveState
            meta = get_meta_controller()
            meta.adapt({
                "success": result.success,
                "strategy": result.strategy,
                "response_time": result.execution_time_ms / 1000
            })
            meta.set_state(CognitiveState.IDLE)

        await error_handler.try_execute(
            component="xray_reflection",
            func=reflection_finalization_step,
            severity=ErrorSeverity.LOW,
            notify_user=False
        )

        # === 14. DREAMS (запись активности) ===
        async def dreams_record_step():
            from core.dreams import get_dream_system
            dreams = get_dream_system()
            dreams.record_activity()

        await error_handler.try_execute(
            component="dreams_system",
            func=dreams_record_step,
            severity=ErrorSeverity.LOW,
            notify_user=False
        )

        # === V3.2: Добавляем информацию о деградации в ответ ===
        if self._degradations:
            result.response += self._format_degradation_notice()
            result.metadata["pipeline_state"] = self._state.value
            result.metadata["degradations"] = [d.to_dict() for d in self._degradations]
        
        # === FINALIZE ===
        result.success = True
        result.execution_time_ms = (time.time() - start_time) * 1000
        self._call_count += 1

        # === V3.2: Записываем метрики ===
        async def metrics_record_step():
            self._record_metrics(start_time, result)

        await error_handler.try_execute(
            component="metrics_collector",
            func=metrics_record_step,
            severity=ErrorSeverity.LOW,
            notify_user=False
        )

        # === RESPONSE GUARD (многоступенчатый контроль качества) ===
        async def response_guard_step():
            from core.guard.response_guard import get_response_guard
            from core.guard.self_healing import get_self_healing_guard
            from core.guard.tone_engine import get_tone_engine, apply_emotional_tone
            from core.guard.cognitive_layer import get_cognitive_layer, build_cognition
            
            # 1. ResponseGuard — базовая очистка (6 ступеней)
            guard = get_response_guard()
            meta_for_guard = {
                "is_first_message": self._call_count <= 1,
                "asked_identity": any(w in user_message.lower() for w in ["кто ты", "что ты", "как тебя зовут", "ты кто"]),
                "confidence": result.confidence,
            }
            result.response = guard.process(result.response, meta_for_guard)
            
            # 2. Self-Healing Guard — детекция и адаптация
            self_healing = get_self_healing_guard()
            self_healing.process_and_learn(result.response, meta_for_guard)
            
            # 3. Tone Engine — применение эмоционального тона
            tone_engine = get_tone_engine()
            # Определяем эмоцию из контекста диалога
            emotion = tone_engine.get_emotion_from_context(user_message, result.response)
            result.response = tone_engine.apply(result.response, emotion, meta_for_guard)
            
            # 4. Cognitive Layer — добавляем мета-данные
            cognitive_layer = get_cognitive_layer()
            if cognitive_layer.enabled:
                # Сохраняем cognition данные в metadata
                cognition = build_cognition(result.to_dict(explain=False))
                result.metadata["cognition"] = cognition

        await error_handler.try_execute(
            component="response_guard",
            func=response_guard_step,
            severity=ErrorSeverity.MEDIUM,
            notify_user=False
        )

        # === V3.2: Сбрасываем состояние Fail Strategy ===
        self._reset_fail_state()

        logger.info(
            f"✅ Pipeline: {intent} | {result.strategy} | "
            f"{result.execution_time_ms:.0f}ms | conf={result.confidence:.2f} | "
            f"health={result.health_score:.2f} | state={self._state.value}"
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