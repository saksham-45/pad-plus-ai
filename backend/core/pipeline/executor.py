"""
PipelineExecutor v4.0 — оркестратор фаз обработки запроса.

Заменяет монолитный execute() из pipeline.py.
Каждая фаза — отдельный класс с единым интерфейсом PipelinePhase.
"""

from typing import List, Dict, Any, Optional
import logging
import time
import asyncio
import uuid

from .models import PipelineState, DegradationInfo, PhaseResult, PipelineResult
from .context import PipelineContext
from .phases import (
    AntiLoopPhase,
    SafetyPhase,
    IntentPhase,
    RagPhase,
    KnowledgeGraphPhase,
    EpisodicPhase,
    SemanticPhase,
    EmotionPhase,
    PersonaPhase,
    RootsPhase,
    IdentityPhase,
    GeneratePhase,
    TruthLoopPhase,
    SaveEpisodePhase,
    EmotionUpdatePhase,
    PersonaEvolutionPhase,
    EventsBroadcastPhase,
    HealthMonitorPhase,
    ReflectionPhase,
    DreamsPhase,
    MetricsPhase,
    ResponseGuardPhase,
)

logger = logging.getLogger("padplus.pipeline.executor")


class PipelineExecutor:
    CRITICAL_COMPONENTS = {"safety", "llm_service"}
    IMPORTANT_COMPONENTS = {"rag", "facts", "episodic", "semantic"}

    def __init__(self):
        self._call_count = 0
        self._last_call_time = 0
        self._anti_loop_history: List[str] = []
        self._max_history = 10
        self._dialogs_since_consolidation = 0
        self._consolidation_interval = 10
        self._consolidation_lock = asyncio.Lock()
        self._state = PipelineState.HEALTHY
        self._degradations: List[DegradationInfo] = []

        self._phases = self._build_phases()

    def _build_phases(self):
        return [
            ("safety", SafetyPhase()),
            ("intent", IntentPhase()),
            ("rag", RagPhase()),
            ("knowledge_graph", KnowledgeGraphPhase()),
            ("episodic", EpisodicPhase()),
            ("semantic", SemanticPhase()),
            ("emotion", EmotionPhase()),
            ("persona", PersonaPhase()),
            ("roots", RootsPhase()),
            ("identity", IdentityPhase()),
            ("generate", GeneratePhase()),
            ("truth_loop", TruthLoopPhase()),
            ("save_episode", SaveEpisodePhase()),
            ("emotion_update", EmotionUpdatePhase()),
            ("consolidation", None),  # встроено в execute
            ("procedure_success", None),  # встроено в execute
            ("persona_evolution", PersonaEvolutionPhase()),
            ("events_broadcast", EventsBroadcastPhase()),
            ("health", HealthMonitorPhase()),
            ("reflection", ReflectionPhase()),
            ("dreams", DreamsPhase()),
            ("metrics", MetricsPhase(self)),
            ("response_guard", ResponseGuardPhase()),
        ]

    def _mark_degraded(self, component: str, error: str, severity: str = "medium", fallback_applied: bool = False):
        degradation = DegradationInfo(
            component=component,
            error=error,
            fallback_applied=fallback_applied,
            severity=severity,
        )
        self._degradations.append(degradation)
        if component in self.CRITICAL_COMPONENTS and severity == "high":
            self._state = PipelineState.FAILED
        elif self._degradations:
            self._state = PipelineState.DEGRADED
        logger.warning(f"Компонент '{component}' деградировал: {error} (severity={severity})")

    def _should_stop_on_degradation(self, component: str) -> bool:
        if component in self.CRITICAL_COMPONENTS:
            return len([d for d in self._degradations if d.component in self.CRITICAL_COMPONENTS]) >= 1
        return False

    def _create_error_result(self, message: str, start_time: float) -> PipelineResult:
        result = PipelineResult(
            success=False,
            response=message,
            execution_time_ms=(time.time() - start_time) * 1000,
        )
        result.metadata["pipeline_state"] = self._state.value
        result.metadata["degradations"] = [d.to_dict() for d in self._degradations]
        return result

    def _format_degradation_notice(self) -> str:
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
        self._state = PipelineState.HEALTHY
        self._degradations.clear()

    def _get_fallback_rag_context(self, query: str) -> str:
        keywords = query.lower().split()[:5]
        return f"[RAG недоступен. Ключевые слова: {', '.join(keywords)}]"

    def _record_metrics(self, start_time: float, result: PipelineResult):
        try:
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
            metrics.set_gauge(
                "pipeline_active_state",
                0 if self._state == PipelineState.HEALTHY else 1 if self._state == PipelineState.DEGRADED else 2,
            )
        except Exception as e:
            logger.warning(f"{__name__} error: {e}")

    def _check_anti_loop(self, user_message: str) -> Optional[str]:
        normalized = user_message.lower().strip()[:50]
        repeat_count = self._anti_loop_history.count(normalized)
        if repeat_count >= 3:
            return "Обнаружен цикл: похожий запрос повторяется. Попробуйте переформулировать."
        self._anti_loop_history.append(normalized)
        if len(self._anti_loop_history) > self._max_history:
            self._anti_loop_history.pop(0)
        return None

    def _determine_strategy(self, user_message: str) -> str:
        text_lower = user_message.lower().strip()
        if any(kw in text_lower for kw in ["почему ты", "как ты", "что ты думаешь о себе", "саморефлексия"]):
            return "reflective"
        if any(kw in text_lower for kw in ["запомни", "выучи", "новый факт", "добавь в память", "сохрани"]):
            return "learning"
        if any(kw in text_lower for kw in ["придумай", "сочини", "креативно", "оригинально", "необычно"]):
            return "creative"
        if sum(1 for kw in ["почему", "как работает", "объясни", "проанализируй", "сравни", "разбери", "детально", "подробно", "глубоко"] if kw in text_lower) >= 2 or (len(user_message) > 50 and "почему" in text_lower):
            return "reasoning"
        if any(kw in text_lower for kw in ["привет", "здравствуй", "как дела", "что делаешь", "спасибо", "пока", "до свидания", "ок", "хорошо"]):
            return "simple"
        if len(user_message) < 20:
            return "simple"
        if len(user_message) < 100:
            return "retrieval"
        return "reasoning"

    async def execute(
        self,
        user_message: str,
        context: Dict = None,
        session_id: str = None,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> PipelineResult:
        start_time = time.time()
        result = PipelineResult(success=False)
        ctx = PipelineContext(
            user_message=user_message,
            context=context or {},
            session_id=session_id,
            api_key=api_key,
            provider=provider,
        )

        result.strategy = self._determine_strategy(user_message)
        result.metadata["strategy_selected"] = result.strategy

        result.sources = {
            "rag": {"count": 0, "confidence": 0.0},
            "facts": {"count": 0},
            "graph": {"concepts": [], "confidence": 0.0},
            "episodic": {"count": 0},
            "llm": {"model": "", "provider": ""},
        }

        ctx.context["strategy"] = result.strategy
        ctx.context["response"] = ""
        ctx.context["start_time"] = start_time
        ctx.context["pipeline_result"] = result
        ctx.context["call_count"] = self._call_count

        # === X-RAY: инициализация трассировки ===
        request_id = str(uuid.uuid4())
        ctx.context["xray_request_id"] = request_id

        # Маппинг фаз pipeline на TraceStage
        _stage_map = {
            "safety": "safety", "intent": "intent",
            "rag": "retrieve", "knowledge_graph": "retrieve",
            "episodic": "retrieve", "semantic": "retrieve",
            "emotion": "retrieve", "roots": "retrieve",
            "persona": "persona", "generate": "generate",
            "truth_loop": "verify",
            "save_episode": "remember", "emotion_update": "remember",
            "persona_evolution": "remember",
            "events_broadcast": "emit", "health": "emit",
            "reflection": "emit", "dreams": "emit",
            "metrics": "emit", "response_guard": "emit",
        }

        async def _record_xray_phase(pname: str, pdata: dict, dur_ms: float, pstatus: str = "success", perror: str = None):
            """Запись события фазы в X-Ray TraceCollector + Broadcaster"""
            try:
                from core.xray import get_trace_collector, get_xray_broadcaster, get_thought_visualizer
                from core.xray.trace_collector import TraceStage

                stage = TraceStage(_stage_map.get(pname, "retrieve"))
                tc = get_trace_collector()
                tb = get_xray_broadcaster()

                tc.record_event(request_id, stage, {**pdata, "phase": pname}, dur_ms, pstatus, perror)
                await tb.send_pipeline_status(request_id, pname, {
                    **pdata, "status": pstatus, "duration_ms": round(dur_ms, 2)
                })
            except Exception as e:
                logger.warning(f"{__name__} error: {e}")

        # X-Ray: старт сессии + стратегия
        try:
            from core.xray import (
                get_trace_collector, get_xray_broadcaster, get_thought_visualizer
            )
            tc = get_trace_collector()
            tb = get_xray_broadcaster()
            tv = get_thought_visualizer()

            tc.start_session(user_message, {"strategy": result.strategy}, request_id=request_id)

            thought = tv.strategy_decision(
                strategy=result.strategy,
                reason=f"Стратегия '{result.strategy}' выбрана на основе сообщения ({len(user_message)} symbols)",
                confidence=0.85
            )
            await tb.send_thought(thought.to_dict())
            await tb.send_decision({
                "type": "strategy",
                "strategy": result.strategy,
                "reason": f"Длина: {len(user_message)} символов, ключевые слова",
                "confidence": 0.85
            })
        except Exception as e:
            logger.warning(f"{__name__} error: {e}")

        # === 1. ANTI-LOOP GUARD ===
        phase_result = await AntiLoopPhase(self).execute(ctx)
        if phase_result.data and phase_result.data.get("blocked"):
            result.response = phase_result.data.get("warning", "")
            result.success = True
            result.execution_time_ms = (time.time() - start_time) * 1000
            # X-Ray: завершить сессию при блокировке
            try:
                from core.xray import get_trace_collector
                get_trace_collector().complete_session(request_id, {"reason": "anti_loop_block", "response": result.response[:200]})
            except Exception as e:
                logger.warning(f"{__name__} error: {e}")
            return result

        for phase_name, phase in self._phases:
            if phase is None:
                continue

            # Когнитивный снимок перед GeneratePhase (диагностика v4.0)
            if phase_name == "generate":
                logger.info("=== КОГНИТИВНЫЙ СНИМОК перед GeneratePhase ===")
                cognitive_keys = ["roots_context", "persona_context", "rag_context", "episodic_context", "procedure_context", "emotion_state", "emotion_style", "intent", "strategy"]
                for key in cognitive_keys:
                    val = ctx.context.get(key, "")
                    if isinstance(val, dict):
                        val_preview = {k: v for k, v in list(val.items())[:5]}
                    elif isinstance(val, str):
                        val_preview = val[:120] if val else "(пусто)"
                    else:
                        val_preview = val
                    logger.info(f"  {key}: {val_preview}")
                logger.info("=== КОНЕЦ СНИМКА ===")

            try:
                phase_result = await phase.execute(ctx)
            except Exception as e:
                self._mark_degraded(phase_name, str(e), severity="high")
                if self._should_stop_on_degradation(phase_name):
                    # X-Ray: завершить сессию при критической ошибке
                    try:
                        from core.xray import get_trace_collector
                        get_trace_collector().complete_session(request_id, {"error": str(e)[:200], "phase": phase_name})
                    except Exception as e:
                        logger.warning(f"{__name__} error: {e}")
                    return self._create_error_result(
                        f"Критическая ошибка: {e}", start_time
                    )
                continue

            # X-Ray: запись фазы (ВСЕГДА, даже для failed/degraded)
            phase_dur = (time.time() - ctx.context.get("start_time", start_time)) * 1000
            phase_status = "error" if not phase_result.success else "success"
            phase_error = phase_result.errors[0] if phase_result.errors else None
            await _record_xray_phase(phase_name, phase_result.data or {}, phase_dur, pstatus=phase_status, perror=phase_error)

            if not phase_result.success:
                if phase_result.degradation:
                    self._mark_degraded(
                        phase_result.degradation.component,
                        phase_result.degradation.error,
                        phase_result.degradation.severity,
                        phase_result.degradation.fallback_applied,
                    )
                    if self._should_stop_on_degradation(phase_result.degradation.component):
                        try:
                            from core.xray import get_trace_collector
                            get_trace_collector().complete_session(request_id, {
                                "reason": f"degradation_stop: {phase_result.degradation.component}",
                                "phase": phase_name,
                            })
                        except Exception as e:
                            logger.warning(f"{__name__} error: {e}")
                        break
                    continue
                # Фаза упала без деградации (generate, truth_loop, etc)
                # Запоминаем ошибку, но продолжаем — поздние фазы могут дать fallback
                if phase_result.errors:
                    result.errors.extend(phase_result.errors)
                continue

            if phase_result.data:
                ctx.context.update(phase_result.data)

            self._apply_phase_result(phase_name, phase_result, result)

            # Skip generate if flag set (identity phase, etc.)
            if phase_result.data and phase_result.data.get("skip_generate"):
                logger.info(f"{phase_name}: skip_generate=True, пропускаем оставшиеся фазы")
                break

            # X-Ray: мысли для ключевых фаз
            try:
                from core.xray import get_thought_visualizer, get_xray_broadcaster
                tv = get_thought_visualizer()
                tb = get_xray_broadcaster()
                pd = phase_result.data or {}

                if phase_name == "safety":
                    th = tv.safety_check(pd.get("blocked", False) is False, pd.get("warning"))
                    await tb.send_thought(th.to_dict())
                elif phase_name == "intent":
                    th = tv.intent_classification(pd.get("intent", "unknown"), pd.get("confidence", 0.5))
                    await tb.send_thought(th.to_dict())
                elif phase_name == "rag":
                    th = tv.memory_search("rag", pd.get("sources", {}).get("count", 0))
                    await tb.send_thought(th.to_dict())
                elif phase_name == "episodic":
                    th = tv.episode_recall(pd.get("episodes", []))
                    await tb.send_thought(th.to_dict())
                elif phase_name == "semantic":
                    pname = pd.get("procedure_name")
                    if pname:
                        th = tv.procedure_application(pname, pd.get("steps", []))
                        await tb.send_thought(th.to_dict())
                elif phase_name == "emotion":
                    th = tv.emotion_update(pd.get("emotion_style", {}))
                    await tb.send_thought(th.to_dict())
                    await tb.send_emotion_update(pd.get("emotion_style", {}))
                elif phase_name == "persona":
                    adj = pd.get("adjustments", {})
                    if adj:
                        th = tv.persona_adjustment(adj)
                        await tb.send_thought(th.to_dict())
                elif phase_name == "generate":
                    th = tv.model_selection(pd.get("model", ""), pd.get("provider", ""))
                    await tb.send_thought(th.to_dict())
                elif phase_name == "truth_loop":
                    verified = pd.get("claims_verified", 0)
                    total = pd.get("claims_total", verified or 1)
                    th = tv.claim_verification(verified, total, pd.get("truth_confidence", 0.5))
                    await tb.send_thought(th.to_dict())
                elif phase_name == "save_episode":
                    th = tv.memory_storage("episodic", True)
                    await tb.send_thought(th.to_dict())
                elif phase_name == "events_broadcast":
                    th = tv.event_emission("dialogue_finished")
                    await tb.send_thought(th.to_dict())
            except Exception as e:
                logger.warning(f"{__name__} error: {e}")

            # Safety block — early return
            if phase_name == "safety" and not result.safety_passed:
                result.execution_time_ms = (time.time() - start_time) * 1000
                # X-Ray: завершить сессию при блокировке safety
                try:
                    from core.xray import get_trace_collector
                    get_trace_collector().complete_session(request_id, {"reason": "safety_block", "warning": result.safety_warning})
                except Exception as e:
                    logger.warning(f"{__name__} error: {e}")
                return result

        # === Consolidation (встроенная логика с блокировкой) ===
        async with self._consolidation_lock:
            self._dialogs_since_consolidation += 1
            if self._dialogs_since_consolidation >= self._consolidation_interval:
                try:
                    from memory.consolidation import get_consolidator
                    consolidator = get_consolidator()
                    user_id = ctx.context.get("user_id")
                    consolidator.run_scheduled_consolidation(user_id=user_id)
                    result.consolidation_triggered = True
                    self._dialogs_since_consolidation = 0
                    logger.info("Consolidation triggered")
                except Exception as e:
                    logger.warning(f"Consolidation error: {e}")

        # === Procedure success ===
        applicable_procedure_id = ctx.context.get("procedure_id")
        truth_confidence = result.truth_confidence or ctx.context.get("truth_confidence", 0)
        if applicable_procedure_id and truth_confidence > 0.6:
            try:
                from memory.semantic import get_semantic_memory
                semantic = get_semantic_memory()
                semantic.record_procedure_success(applicable_procedure_id, success=True)
            except Exception as e:
                logger.warning(f"{__name__} error: {e}")

        # === Finalize ===
        if self._degradations:
            result.response += self._format_degradation_notice()
            result.metadata["pipeline_state"] = self._state.value
            result.metadata["degradations"] = [d.to_dict() for d in self._degradations]

        has_response = bool(result.response and result.response.strip() and result.response.strip() not in ("...",))
        if not has_response:
            result.success = False
            if result.errors:
                result.response = result.errors[0]
            elif not result.errors:
                result.errors.append("Pipeline completed but no response generated")
                result.response = "Ошибка: не удалось сгенерировать ответ"
        else:
            result.success = True
        result.execution_time_ms = (time.time() - start_time) * 1000
        self._call_count += 1

        self._reset_fail_state()

        # X-Ray: завершение сессии
        try:
            from core.xray import get_trace_collector
            tc = get_trace_collector()
            tc.complete_session(request_id, {
                "response_preview": (result.response or "")[:200],
                "success": result.success,
                "strategy": result.strategy,
                "intent": result.intent,
                "execution_time_ms": result.execution_time_ms,
            })
        except Exception as e:
            logger.warning(f"Experience capture failed: {e}")

        logger.info(
            f"Pipeline: {result.intent} | {result.strategy} | "
            f"{result.execution_time_ms:.0f}ms | conf={result.confidence:.2f} | "
            f"health={result.health_score:.2f} | state={self._state.value}"
        )

        return result

    def _apply_phase_result(self, phase_name: str, phase_result: PhaseResult, result: PipelineResult):
        data = phase_result.data or {}

        if phase_name == "safety":
            if data.get("blocked"):
                result.safety_passed = False
                result.safety_warning = data.get("warning")
                result.response = data.get("warning", "")
                result.success = True  # Блокировка — корректная обработка
            else:
                result.safety_passed = True
                if data.get("warning"):
                    result.safety_warning = data["warning"]

        elif phase_name == "intent":
            result.intent = data.get("intent", "chat_general")
            result.metadata["pipeline"] = data.get("pipeline_meta", [])

        elif phase_name == "rag":
            result.rag_used = data.get("rag_used", False)
            result.sources["rag"] = data.get("sources", {"count": 0, "confidence": 0.0})

        elif phase_name == "knowledge_graph":
            result.sources["graph"] = {"concepts": data.get("concepts", []), "confidence": data.get("confidence", 0.0)}

        elif phase_name == "episodic":
            result.sources["episodic"]["count"] = data.get("count", 0)

        elif phase_name == "semantic":
            result.procedure_used = data.get("procedure_name")

        elif phase_name == "identity":
            result.response = data.get("response", "")
            result.provider = data.get("provider", "system")
            result.confidence = data.get("confidence", 1.0)

        elif phase_name == "emotion":
            result.emotion_style = data.get("emotion_style", {})

        elif phase_name == "generate":
            result.response = data.get("response", result.response)
            result.provider = data.get("provider", result.provider)
            result.confidence = data.get("confidence", result.confidence)
            result.sources["llm"]["model"] = data.get("model", "")
            result.sources["llm"]["provider"] = data.get("provider", "")
            if data.get("raw_llm_response"):
                result.raw_llm_response = data["raw_llm_response"]
            if data.get("llm_metadata"):
                result.llm_metadata = data["llm_metadata"]

        elif phase_name == "truth_loop":
            result.truth_confidence = data.get("truth_confidence", result.truth_confidence)
            result.claims_verified = data.get("claims_verified", 0)
            sources_info = data.get("sources_info", [])
            if data.get("add_disclaimer"):
                result.response += "\n\n⚠️ Примечание: Эта информация требует дополнительной проверки."
            if sources_info:
                result.response += "\n\n---\n🔍 **Источники информации:**\n" + "\n".join(sources_info)
                result.response += f"\n\n📊 **Общая уверенность:** {result.truth_confidence:.0%}"

        elif phase_name == "save_episode":
            result.episode_id = data.get("episode_id")

        elif phase_name == "health":
            result.health_score = data.get("health_score", 0.0)

        elif phase_name == "response_guard":
            if data.get("response"):
                result.response = data["response"]
            if data.get("cognition"):
                result.metadata["cognition"] = data["cognition"]

        elif phase_name == "emotion_update":
            result.metadata["emotion_updated"] = True

        elif phase_name == "persona_evolution":
            result.metadata["persona_evolved"] = True

        elif phase_name == "events_broadcast":
            result.metadata["events_emitted"] = True

        elif phase_name == "dreams":
            result.metadata["dreams_recorded"] = True

        elif phase_name == "reflection":
            result.metadata["reflection_done"] = True

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_calls": self._call_count,
            "anti_loop_history_size": len(self._anti_loop_history),
            "dialogs_since_consolidation": self._dialogs_since_consolidation,
            "consolidation_interval": self._consolidation_interval,
            "version": "4.0",
            "state": self._state.value,
        }
