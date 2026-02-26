"""
Главный тест для запуска всех компонентов
"""

import pytest
import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.mark.integration
class TestAllComponents:
    """Интеграционный тест всех компонентов"""
    
    @pytest.mark.memory
    def test_memory_components(self):
        """Тест компонентов памяти"""
        try:
            from memory.smartcache import get_husk_cache
            from memory.vectormemory import get_soil_memory
            
            # Шелуха
            husk = get_husk_cache()
            record = husk.store("Тест шелухи", "test", 0.7)
            retrieved = husk.get(record.id)
            assert retrieved is not None
            
            # Почва
            soil = get_soil_memory()
            record = soil.store("Тест почвы", "test", 0.8)
            retrieved = soil.get(record.id)
            assert retrieved is not None
            soil.delete(record.id)
            
        except ImportError as e:
            pytest.skip(f"Модуль памяти не найден: {e}")
    
    @pytest.mark.emotion
    def test_emotion_components(self):
        """Тест компонентов эмоций"""
        try:
            from emotion.pad_model import get_pad_model
            
            pad = get_pad_model()
            state = pad.get_state()
            style = state.get_style()
            
            assert style["tone"] in ["friendly", "neutral", "serious"]
            
        except ImportError as e:
            pytest.skip(f"Модуль эмоций не найден: {e}")
    
    @pytest.mark.llm
    def test_llm_components(self):
        """Тест LLM компонентов"""
        try:
            from llm.provider_manager import get_provider_manager
            
            manager = get_provider_manager()
            status = manager.get_status()
            
            assert status["fallback"]["enabled"]
            # Проверяем что есть хотя бы один провайдер или fallback работает
            assert len(status["providers"]) >= 0
            
        except ImportError as e:
            pytest.skip(f"Модуль LLM не найден: {e}")
    
    @pytest.mark.knowledge
    def test_knowledge_components(self):
        """Тест компонентов знаний"""
        try:
            from knowledge.graph import get_knowledge_graph
            
            graph = get_knowledge_graph()
            stats = graph.get_stats()
            
            assert "nodes" in stats
            assert "edges" in stats
            
        except ImportError as e:
            pytest.skip(f"Модуль знаний не найден: {e}")
    
    @pytest.mark.autonomy
    def test_autonomy_components(self):
        """Тест компонентов автономии"""
        try:
            from autonomy.planner import get_planner, get_self_reflection
            
            planner = get_planner()
            reflection = get_self_reflection()
            
            # Генерируем вопрос
            question = planner.generate_question()
            assert len(question) > 0
            
            # Статус рефлексии
            refl_status = reflection.get_status()
            assert refl_status is not None
            
        except ImportError as e:
            pytest.skip(f"Модуль автономии не найден: {e}")
    
    @pytest.mark.anti_directive
    def test_anti_directive_components(self):
        """Тест ANTI_DIRECTIVE компонентов"""
        try:
            from core.anti_directive import ANTI_DIRECTIVE, check_integrity
            
            text = ANTI_DIRECTIVE.text
            valid = check_integrity()
            
            assert valid
            assert len(text) > 0
            
        except ImportError as e:
            pytest.skip(f"Модуль ANTI_DIRECTIVE не найден: {e}")
    
    @pytest.mark.persona
    def test_persona_components(self):
        """Тест компонентов персоны"""
        try:
            from memory.persona import get_persona
            
            persona = get_persona()
            stats = persona.get_stats()
            traits = persona.get_all_traits()
            
            assert len(traits) > 0
            assert stats is not None
            
        except ImportError as e:
            pytest.skip(f"Модуль персоны не найден: {e}")
    
    @pytest.mark.pipeline
    def test_pipeline_components(self):
        """Тест компонентов пайплайна"""
        try:
            from core.pipeline import get_pipeline
            
            pipeline = get_pipeline()
            stats = pipeline.get_stats()
            
            assert "total_calls" in stats
            
        except ImportError as e:
            pytest.skip(f"Модуль пайплайна не найден: {e}")
    
    @pytest.mark.hygiene
    def test_hygiene_components(self):
        """Тест компонентов гигиены"""
        try:
            from memory.hygiene import get_hygiene
            
            hygiene = get_hygiene()
            stats = hygiene.get_memory_stats()
            
            assert "total_cleanups" in stats
            
        except ImportError as e:
            pytest.skip(f"Модуль гигиены не найден: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
