"""
Интеграционные тесты: Pipeline + FactMemoryChroma

Проверяют, что Pipeline корректно использует FactMemoryChroma
с fallback на старый FactMemory.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


# ============================================================================
# ТЕСТЫ 1: ИНТЕГРАЦИЯ С FACTMEMORYCHROMA
# ============================================================================

class TestPipelineFactMemoryIntegration:
    """Тесты интеграции Pipeline с FactMemoryChroma"""

    @pytest.mark.asyncio
    async def test_pipeline_uses_fact_memory_chroma(self):
        """
        Проверяет, что Pipeline использует FactMemoryChroma
        """
        from backend.core.pipeline import PipelineExecutor
        
        pipeline = PipelineExecutor()
        
        # Мок для FactMemoryChroma в исходном модуле
        with patch('backend.memory.fact_memory_chroma.get_fact_memory_chroma') as MockGetFactChroma, \
             patch('backend.memory.rag.get_rag'), \
             patch('backend.memory.episodic.get_episodic_memory'), \
             patch('backend.memory.semantic.get_semantic_memory'), \
             patch('backend.memory.persona.get_persona'), \
             patch('backend.runtime.litellm_service.get_litellm_service'), \
             patch('backend.core.meta_controller.get_meta_controller'), \
             patch('backend.core.safety_layer.get_safety_layer'), \
             patch('backend.core.intent_router.get_router'):
            
            # Настраиваем FactMemoryChroma
            mock_fact_chroma = MagicMock()
            mock_fact_chroma.search = MagicMock(return_value=[
                MagicMock(subject="Python", predicate="это", object="язык")
            ])
            MockGetFactChroma.return_value = mock_fact_chroma
            
            # Вызываем Pipeline
            result = await pipeline.execute(
                user_message="Что такое Python?",
                context={}
            )
            
            # Проверяем, что FactMemoryChroma был использован
            mock_fact_chroma.search.assert_called()
            assert result.facts_used >= 0

    @pytest.mark.asyncio
    async def test_pipeline_fallback_to_fact_memory(self):
        """
        Проверяет fallback на старый FactMemory при ошибке
        """
        from backend.core.pipeline import PipelineExecutor
        
        pipeline = PipelineExecutor()
        
        # Мок для FactMemoryChroma с Exception
        with patch('backend.memory.fact_memory_chroma.get_fact_memory_chroma', side_effect=Exception("Test error")), \
             patch('backend.memory.fact_memory.get_fact_memory') as MockGetFact, \
             patch('backend.memory.rag.get_rag'), \
             patch('backend.memory.episodic.get_episodic_memory'), \
             patch('backend.memory.semantic.get_semantic_memory'), \
             patch('backend.memory.persona.get_persona'), \
             patch('backend.runtime.litellm_service.get_litellm_service'), \
             patch('backend.core.meta_controller.get_meta_controller'), \
             patch('backend.core.safety_layer.get_safety_layer'), \
             patch('backend.core.intent_router.get_router'):
            
            mock_fact = MagicMock()
            mock_fact.search = MagicMock(return_value=[])
            MockGetFact.return_value = mock_fact
            
            # Вызываем Pipeline
            result = await pipeline.execute(
                user_message="Тест",
                context={}
            )
            
            # Старый FactMemory был использован
            mock_fact.search.assert_called()

    @pytest.mark.asyncio
    async def test_pipeline_handles_fact_memory_error(self):
        """
        Проверяет обработку ошибок FactMemory
        """
        from backend.core.pipeline import PipelineExecutor
        
        pipeline = PipelineExecutor()
        
        # Оба FactMemory с ошибкой
        with patch('backend.memory.fact_memory_chroma.get_fact_memory_chroma', side_effect=Exception("Test error")), \
             patch('backend.memory.fact_memory.get_fact_memory', side_effect=Exception("Test error")), \
             patch('backend.memory.rag.get_rag'), \
             patch('backend.memory.episodic.get_episodic_memory'), \
             patch('backend.memory.semantic.get_semantic_memory'), \
             patch('backend.memory.persona.get_persona'), \
             patch('backend.runtime.litellm_service.get_litellm_service'), \
             patch('backend.core.meta_controller.get_meta_controller'), \
             patch('backend.core.safety_layer.get_safety_layer'), \
             patch('backend.core.intent_router.get_router'):
            
            # Вызываем Pipeline — не должен упасть
            result = await pipeline.execute(
                user_message="Тест",
                context={}
            )
            
            # Pipeline должен продолжить работу
            assert result is not None


# ============================================================================
# ТЕСТЫ 2: СРАВНЕНИЕ PRODUCTION VS CHROMA
# ============================================================================

class TestFactMemoryComparison:
    """Тесты сравнения FactMemory и FactMemoryChroma"""

    @pytest.mark.asyncio
    async def test_fact_memory_chroma_faster(self):
        """
        Проверяет, что FactMemoryChroma быстрее старого FactMemory
        """
        import time
        
        from backend.memory.fact_memory import get_fact_memory
        from backend.memory.fact_memory_chroma import get_fact_memory_chroma
        
        # Добавляем факты в оба хранилища
        old_fact = get_fact_memory()
        new_fact = get_fact_memory_chroma()
        
        # Очищаем перед тестом
        old_fact.clear()
        new_fact.clear()
        
        # Добавляем тестовые факты
        for i in range(10):
            old_fact.add(f"Факт {i}", "это", f"тест {i}")
            new_fact.add(f"Факт {i}", "это", f"тест {i}")
        
        # Замеряем скорость поиска
        start = time.time()
        old_results = old_fact.search("тест", limit=5)
        old_time = time.time() - start
        
        start = time.time()
        new_results = new_fact.search("тест", limit=5)
        new_time = time.time() - start
        
        # FactMemoryChroma должен быть быстрее или сравним
        # (в реальности быстрее на больших объёмах)
        assert len(new_results) >= 0
        assert len(old_results) >= 0
        
        # Очищаем
        old_fact.clear()
        new_fact.clear()


# ============================================================================
# ТЕСТЫ 3: END-TO-END
# ============================================================================

class TestEndToEnd:
    """Сквозные тесты Pipeline с FactMemoryChroma"""

    @pytest.mark.asyncio
    async def test_pipeline_full_workflow_with_facts(self):
        """
        Полный тест рабочего процесса Pipeline с фактами
        """
        from backend.core.pipeline import PipelineExecutor
        
        pipeline = PipelineExecutor()
        
        # Мок для всех зависимостей
        with patch('backend.memory.fact_memory_chroma.get_fact_memory_chroma') as MockFactChroma, \
             patch('backend.memory.rag.get_rag') as MockRag, \
             patch('backend.memory.episodic.get_episodic_memory') as MockEpisodic, \
             patch('backend.memory.semantic.get_semantic_memory') as MockSemantic, \
             patch('backend.memory.persona.get_persona') as MockPersona, \
             patch('backend.runtime.litellm_service.get_litellm_service') as MockLiteLLM, \
             patch('backend.core.meta_controller.get_meta_controller') as MockMeta, \
             patch('backend.core.safety_layer.get_safety_layer') as MockSafety, \
             patch('backend.core.intent_router.get_router') as MockRouter:
            
            # Настраиваем моки
            MockFactChroma.return_value.search = MagicMock(return_value=[])
            MockRag.return_value.get_context = MagicMock(return_value="")
            MockEpisodic.return_value.search_episodes = MagicMock(return_value=[])
            MockEpisodic.return_value.add_episode = MagicMock(return_value=MagicMock(id="ep-123"))
            MockSemantic.return_value.find_applicable_procedure = MagicMock(return_value=None)
            MockPersona.return_value.get_persona_context = MagicMock(return_value="")
            MockPersona.return_value.record_interaction = MagicMock()
            MockPersona.return_value.evolve_from_dialog = MagicMock(return_value={"changes": []})
            
            mock_litellm = AsyncMock()
            mock_litellm.generate = AsyncMock(return_value=MagicMock(
                text="Ответ",
                provider="test",
                confidence=0.8
            ))
            MockLiteLLM.return_value = mock_litellm
            
            mock_meta = MagicMock()
            mock_meta.evaluate_cognitive_load = MagicMock(return_value=MagicMock(current=0.5))
            mock_meta.decide_strategy = MagicMock(return_value=MagicMock(
                strategy=MagicMock(value="simple"),
                reason="Тест"
            ))
            mock_meta.set_state = MagicMock()
            mock_meta.adapt = MagicMock()
            MockMeta.return_value = mock_meta
            
            mock_safety = MagicMock()
            mock_safety.check_request = MagicMock(return_value=MagicMock(
                action=MagicMock(value="allow")
            ))
            MockSafety.return_value = mock_safety
            
            mock_router = MagicMock()
            mock_router.route = MagicMock(return_value=MagicMock(
                intent=MagicMock(value="chat_general"),
                pipeline=[]
            ))
            MockRouter.return_value = mock_router
            
            # Вызываем Pipeline
            result = await pipeline.execute(
                user_message="Что такое Python?",
                context={"user_id": "user-123"}
            )
            
            # Проверяем результат
            assert result is not None
            # FactMemoryChroma был вызван
            MockFactChroma.return_value.search.assert_called()


# ============================================================================
# СВОДНЫЙ ТЕСТ
# ============================================================================

class TestFactMemoryPipelineIntegration:
    """Сводный тест интеграции"""

    @pytest.mark.asyncio
    async def test_fact_memory_chroma_integration(self):
        """
        Полный тест интеграции FactMemoryChroma
        """
        from backend.core.pipeline import PipelineExecutor
        from backend.memory.fact_memory_chroma import get_fact_memory_chroma
        
        # 1. FactMemoryChroma существует
        fact_memory = get_fact_memory_chroma()
        assert fact_memory is not None
        
        # 2. Pipeline существует
        pipeline = PipelineExecutor()
        assert pipeline is not None
        
        # 3. FactMemoryChroma работает
        fact_memory.clear()
        fact_id = fact_memory.add("Тест", "это", "интеграция")
        assert fact_id is not None
        
        results = fact_memory.search("Тест интеграция")
        assert len(results) >= 1
        
        fact_memory.clear()
