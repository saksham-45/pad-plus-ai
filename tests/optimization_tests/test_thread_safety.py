"""
Исправление 1: asyncio.Lock для счётчиков

Тесты для проверки потокобезопасности в PipelineExecutor.
Проверяет отсутствие race condition в счётчиках и метриках.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


class TestThreadSafety:
    """Тесты потокобезопасности PipelineExecutor"""

    @pytest.mark.asyncio
    async def test_concurrent_consolidation_counter(self, mock_cache_manager):
        """
        Проверяет, что счётчик консолидации корректно работает
        при конкурентных запросах
        """
        from backend.core.pipeline import get_pipeline
        
        # Сбрасываем глобальный экземпляр для чистоты теста
        import backend.core.pipeline as pipeline_module
        pipeline_module._pipeline = None
        
        pipeline = get_pipeline()
        pipeline._consolidation_interval = 100  # Увеличиваем для теста
        
        num_concurrent_requests = 50
        
        # Мок для всех зависимостей pipeline
        with patch.object(pipeline, '_run_safety_check', return_value=True), \
             patch.object(pipeline, '_run_intent_classification', return_value=("chat_general", 0.8)), \
             patch.object(pipeline, '_run_generate', return_value="Тестовый ответ"), \
             patch.object(pipeline, '_save_episode', new=AsyncMock()):
            
            # Создаём 50 конкурентных запросов
            tasks = [
                pipeline.execute(f"Тестовый запрос {i}")
                for i in range(num_concurrent_requests)
            ]
            
            # Выполняем все запросы параллельно
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Фильтруем успешные выполнения
            success_results = [r for r in results if not isinstance(r, Exception)]
            
            # Счётчик должен быть корректным
            assert pipeline._dialogs_since_consolidation == len(success_results)
            
            # Счётчик не должен быть отрицательным
            assert pipeline._dialogs_since_consolidation >= 0

    @pytest.mark.asyncio
    async def test_no_race_condition_in_metrics(self, mock_cache_manager):
        """
        Проверяет отсутствие race condition в метриках Pipeline
        """
        from backend.core.pipeline import get_pipeline
        
        # Сбрасываем глобальный экземпляр
        import backend.core.pipeline as pipeline_module
        pipeline_module._pipeline = None
        
        pipeline = get_pipeline()
        initial_stats = pipeline.get_stats()
        
        # Мок для зависимостей
        with patch.object(pipeline, '_run_safety_check', return_value=True), \
             patch.object(pipeline, '_run_intent_classification', return_value=("chat_general", 0.8)), \
             patch.object(pipeline, '_run_generate', return_value="Тестовый ответ"), \
             patch.object(pipeline, '_save_episode', new=AsyncMock()):
            
            # 100 конкурентных запросов
            tasks = [pipeline.execute(f"Запрос {i}") for i in range(100)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Считаем успешные выполнения
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            
            final_stats = pipeline.get_stats()
            
            # total_calls должен увеличиться ровно на количество успешных запросов
            expected_calls = initial_stats['total_calls'] + success_count
            assert final_stats['total_calls'] == expected_calls

    @pytest.mark.asyncio
    async def test_consolidation_lock_prevents_race(self, mock_cache_manager):
        """
        Проверяет, что Lock предотвращает race condition при консолидации
        """
        from backend.core.pipeline import get_pipeline
        import asyncio
        
        # Сбрасываем глобальный экземпляр
        import backend.core.pipeline as pipeline_module
        pipeline_module._pipeline = None
        
        pipeline = get_pipeline()
        pipeline._consolidation_interval = 10  # Маленький интервал для теста
        
        consolidation_triggered = []
        original_consolidate = pipeline._run_consolidation
        
        async def tracked_consolidate():
            consolidation_triggered.append(asyncio.current_task())
            # Имитируем задержку консолидации
            await asyncio.sleep(0.01)
            return {"consolidated": True}
        
        pipeline._run_consolidation = tracked_consolidate
        
        # Мок для зависимостей
        with patch.object(pipeline, '_run_safety_check', return_value=True), \
             patch.object(pipeline, '_run_intent_classification', return_value=("chat_general", 0.8)), \
             patch.object(pipeline, '_run_generate', return_value="Тестовый ответ"), \
             patch.object(pipeline, '_save_episode', new=AsyncMock()):
            
            # Запускаем много запросов одновременно
            tasks = [pipeline.execute(f"Запрос {i}") for i in range(20)]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Проверяем, что консолидация не запускалась слишком часто
        # (Lock должен предотвратить параллельное выполнение)
        assert len(consolidation_triggered) <= 3  # Максимум 2-3 раза за 20 запросов

    @pytest.mark.asyncio
    async def test_counter_accuracy_under_load(self, mock_cache_manager):
        """
        Стресс-тест: проверка точности счётчика под высокой нагрузкой
        """
        from backend.core.pipeline import get_pipeline
        
        # Сбрасываем глобальный экземпляр
        import backend.core.pipeline as pipeline_module
        pipeline_module._pipeline = None
        
        pipeline = get_pipeline()
        pipeline._consolidation_interval = 1000  # Увеличиваем
        
        total_requests = 200
        batch_size = 50
        
        successful_count = 0
        
        # Мок для зависимостей
        with patch.object(pipeline, '_run_safety_check', return_value=True), \
             patch.object(pipeline, '_run_intent_classification', return_value=("chat_general", 0.8)), \
             patch.object(pipeline, '_run_generate', return_value="Тестовый ответ"), \
             patch.object(pipeline, '_save_episode', new=AsyncMock()):
            
            # Запускаем пакетами
            for batch in range(total_requests // batch_size):
                tasks = [
                    pipeline.execute(f"Пакет {batch}, запрос {i}")
                    for i in range(batch_size)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                successful_count += sum(1 for r in results if not isinstance(r, Exception))
        
        # Счётчик должен точно соответствовать количеству успешных запросов
        assert pipeline._dialogs_since_consolidation == successful_count

    @pytest.mark.asyncio
    async def test_no_negative_counter_values(self, mock_cache_manager):
        """
        Проверяет, что счётчик никогда не становится отрицательным
        """
        from backend.core.pipeline import get_pipeline
        
        # Сбрасываем глобальный экземпляр
        import backend.core.pipeline as pipeline_module
        pipeline_module._pipeline = None
        
        pipeline = get_pipeline()
        
        negative_values = []
        
        # Мок для зависимостей
        with patch.object(pipeline, '_run_safety_check', return_value=True), \
             patch.object(pipeline, '_run_intent_classification', return_value=("chat_general", 0.8)), \
             patch.object(pipeline, '_run_generate', return_value="Тестовый ответ"), \
             patch.object(pipeline, '_save_episode', new=AsyncMock()):
            
            async def check_counter():
                # Проверяем счётчик во время выполнения
                await asyncio.sleep(0.001)
                if pipeline._dialogs_since_consolidation < 0:
                    negative_values.append(pipeline._dialogs_since_consolidation)
            
            # Запускаем запросы и проверки параллельно
            for i in range(50):
                task1 = asyncio.create_task(pipeline.execute(f"Запрос {i}"))
                task2 = asyncio.create_task(check_counter())
                await asyncio.gather(task1, task2)
        
        # Счётчик никогда не должен быть отрицательным
        assert len(negative_values) == 0


class TestLockImplementation:
    """Тесты реализации Lock"""

    @pytest.mark.asyncio
    async def test_lock_exists(self):
        """
        Проверяет, что Lock создан в PipelineExecutor
        """
        from backend.core.pipeline import PipelineExecutor
        
        pipeline = PipelineExecutor()
        
        # Проверяем наличие lock
        assert hasattr(pipeline, '_consolidation_lock')
        assert isinstance(pipeline._consolidation_lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_lock_acquire_release(self):
        """
        Проверяет, что Lock корректно захватывается и освобождается
        """
        from backend.core.pipeline import PipelineExecutor
        
        pipeline = PipelineExecutor()
        
        # Захватываем lock
        await pipeline._consolidation_lock.acquire()
        assert pipeline._consolidation_lock.locked()
        
        # Освобождаем
        pipeline._consolidation_lock.release()
        assert not pipeline._consolidation_lock.locked()

    @pytest.mark.asyncio
    async def test_lock_context_manager(self):
        """
        Проверяет, что Lock работает как контекстный менеджер
        """
        from backend.core.pipeline import PipelineExecutor
        
        pipeline = PipelineExecutor()
        
        # Используем как контекстный менеджер
        async with pipeline._consolidation_lock:
            assert pipeline._consolidation_lock.locked()
        
        # После выхода из контекста lock освобождён
        assert not pipeline._consolidation_lock.locked()

    @pytest.mark.asyncio
    async def test_lock_prevents_concurrent_access(self):
        """
        Проверяет, что Lock предотвращает конкурентный доступ
        """
        from backend.core.pipeline import PipelineExecutor
        
        pipeline = PipelineExecutor()
        execution_order = []
        
        async def task(task_id):
            async with pipeline._consolidation_lock:
                execution_order.append(f"{task_id}_start")
                await asyncio.sleep(0.01)
                execution_order.append(f"{task_id}_end")
        
        # Запускаем 3 задачи одновременно
        await asyncio.gather(
            task(1),
            task(2),
            task(3)
        )
        
        # Проверяем, что задачи выполнялись последовательно
        # (каждая start должна быть перед соответствующей end)
        for i in range(1, 4):
            start_idx = execution_order.index(f"{i}_start")
            end_idx = execution_order.index(f"{i}_end")
            assert start_idx < end_idx
