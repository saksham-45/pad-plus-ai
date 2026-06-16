"""
Тестирование Memory Consolidation — NeuroMind AI
"""

import sys
import os
import asyncio
from typing import Dict, Any
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMemoryConsolidation:
    """Тестирование Memory Consolidation системы"""
    
    async def test_consolidation_process(self):
        """Тест процесса консолидации памяти"""
        from memory.consolidation import get_consolidation
        
        consolidation = get_consolidation()
        
        # Тест консолидации
        result = await consolidation.run_consolidation()
        
        assert result["status"] == "completed"
        assert "consolidated_items" in result
        print("  ✅ Memory Consolidation: процесс консолидации работает")
    
    async def test_episodic_to_semantic_transfer(self):
        """Тест переноса из эпизодической в семантическую память"""
        from memory.consolidation import get_consolidation
        
        consolidation = get_consolidation()
        
        # Тест переноса памяти
        result = await consolidation.transfer_episodic_to_semantic()
        
        assert result["transferred_items"] > 0
        print("  ✅ Memory Consolidation: перенос из эпизодической в семантическую работает")
    
    async def test_fact_extraction(self):
        """Тест извлечения фактов"""
        from memory.consolidation import get_consolidation
        
        consolidation = get_consolidation()
        
        # Тест извлечения фактов
        facts = await consolidation.extract_facts_from_dialogs()
        
        assert len(facts) > 0
        print("  ✅ Memory Consolidation: извлечение фактов работает")
    
    async def test_knowledge_graph_update(self):
        """Тест обновления графа знаний"""
        from memory.consolidation import get_consolidation
        
        consolidation = get_consolidation()
        
        # Тест обновления графа знаний
        result = await consolidation.update_knowledge_graph()
        
        assert result["updated_nodes"] > 0
        assert result["updated_edges"] > 0
        print("  ✅ Memory Consolidation: обновление графа знаний работает")
    
    async def test_memory_hygiene_integration(self):
        """Тест интеграции с гигиеной памяти"""
        from memory.consolidation import get_consolidation
        
        consolidation = get_consolidation()
        
        # Тест интеграции с гигиеной
        result = await consolidation.run_with_hygiene_check()
        
        assert result["status"] == "completed"
        assert "cleaned_items" in result
        print("  ✅ Memory Consolidation: интеграция с гигиеной работает")
    
    async def test_consolidation_timing(self):
        """Тест временных параметров консолидации"""
        from memory.consolidation import get_consolidation
        
        consolidation = get_consolidation()
        
        # Тест временных параметров
        timing = consolidation.get_consolidation_timing()
        
        assert timing["interval"] > 0
        assert timing["duration"] > 0
        print("  ✅ Memory Consolidation: временные параметры работают")


def run_memory_consolidation_tests():
    """Запуск всех тестов Memory Consolidation"""
    print("\n" + "="*60)
    print("💾 ТЕСТИРОВАНИЕ MEMORY CONSOLIDATION")
    print("="*60)
    
    tests = TestMemoryConsolidation()
    results = []
    
    # Запускаем все тесты
    asyncio.run(tests.test_consolidation_process())
    asyncio.run(tests.test_episodic_to_semantic_transfer())
    asyncio.run(tests.test_fact_extraction())
    asyncio.run(tests.test_knowledge_graph_update())
    asyncio.run(tests.test_memory_hygiene_integration())
    asyncio.run(tests.test_consolidation_timing())
    
    print("="*60)
    print("✅ Memory Consolidation: ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("="*60)


if __name__ == "__main__":
    run_memory_consolidation_tests()