from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult


class GeneratePhase(PipelinePhase):
    name = "generate"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from runtime.llm_service import get_llm_service, LLMService
            from core.anti_directive import ANTI_DIRECTIVE
            import os

            roots_context = ctx.context.get("roots_context", "")
            persona_context = ctx.context.get("persona_context", "")
            rag_context = ctx.context.get("rag_context", "")
            episodic_context = ctx.context.get("episodic_context", "")
            procedure_context = ctx.context.get("procedure_context", "")
            emotion_style = ctx.context.get("emotion_style", {})
            emotion_state = ctx.context.get("emotion_state", {})
            emotion_plain = emotion_state if isinstance(emotion_state, dict) else {}
            strategy = ctx.context.get("strategy", "simple")

            emotion_tone = emotion_style.get("tone", "neutral") if isinstance(emotion_style, dict) else "neutral"

            full_context = f"""{roots_context}

{persona_context}

{rag_context}
{episodic_context}
{procedure_context}

Твоё текущее эмоциональное состояние:
- Тон: {emotion_tone}
- Уверенность: {emotion_plain.get("уверенность", 0.5):.2f}

Стратегия обработки: {strategy}

Всегда отвечай на русском. Будь кратким, но глубоким.
Сомневайся в утверждениях. Проверяй факты.
"""

            user_api_key = ctx.api_key
            user_provider = ctx.provider

            if not user_api_key and ctx.session_id:
                try:
                    from runtime.session_provider_manager import get_session_manager
                    session_manager = get_session_manager()
                    user_manager = session_manager.create_user_manager(ctx.session_id)
                    if user_manager.llm_service:
                        user_api_key = user_manager.llm_service.default_api_key
                except Exception as e:
                    logger.warning(f"{__name__} error: {e}")

            if not user_api_key:
                return PhaseResult(
                    success=True,
                    data={
                        "response": "У меня нет подключенного API ключа. Пожалуйста, добавьте ключ в настройках.",
                        "provider": "no_api_key",
                        "confidence": 0.0,
                        "model": "",
                    },
                )

            llm = LLMService(api_key=user_api_key)
            gen_result = await llm.generate(
                prompt=ctx.user_message,
                system_prompt=full_context,
                api_key=user_api_key,
                model=None,
                provider=user_provider,
                max_tokens=14000,
            )

            return PhaseResult(
                success=True,
                data={
                    "response": gen_result.text,
                    "provider": gen_result.provider,
                    "confidence": gen_result.confidence,
                    "model": gen_result.model,
                    "raw_llm_response": gen_result.metadata.get("raw_response") if gen_result.metadata else None,
                    "llm_metadata": gen_result.metadata,
                },
            )
        except Exception as e:
            return PhaseResult(
                success=False,
                errors=[f"Generate failed: {e}"],
                data={
                    "response": "",
                    "provider": "",
                    "confidence": 0.0,
                    "model": "",
                },
            )
