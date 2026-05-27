"""
Главный тест для запуска всех компонентов
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.integration
class TestAllComponents:
    """Интеграционный тест всех компонентов"""

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

    @pytest.mark.pipeline
    def test_pipeline_executor(self):
        """Тест PipelineExecutor"""
        try:
            from core.pipeline import PipelineExecutor
            
            pipeline = PipelineExecutor()
            assert pipeline is not None
            
        except ImportError as e:
            pytest.skip(f"Модуль пайплайна не найден: {e}")

    @pytest.mark.rag
    def test_rag_memory(self):
        """Тест RAG Memory"""
        try:
            from memory.rag import RAGMemory
            
            rag = RAGMemory()
            assert rag is not None
            
        except ImportError as e:
            pytest.skip(f"Модуль RAG не найден: {e}")

    @pytest.mark.semantic
    def test_semantic_memory(self):
        """Тест семантической памяти"""
        try:
            from memory.semantic import get_semantic_memory
            
            semantic = get_semantic_memory()
            assert semantic is not None
            
        except ImportError as e:
            pytest.skip(f"Модуль семантической памяти не найден: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])