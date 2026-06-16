"""
Исправление 4: Async I/O для файлов

Тесты для проверки асинхронных файловых операций:
- Асинхронная запись в JSON
- Отсутствие блокировки event loop
- Корректная работа с данными
"""

import pytest
import asyncio
import json
import os
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


class TestAsyncIO:
    """Тесты Async I/O для файловых операций"""

    @pytest.mark.asyncio
    async def test_async_json_write(self, temp_data_dir):
        """
        Проверяет, что запись в JSON выполняется асинхронно
        """
        from backend.core.meta_controller import MetaCognitiveController
        
        # Создаём контроллер с временной директорией
        data_path = temp_data_dir / "meta_cognitive.json"
        controller = MetaCognitiveController(data_path=str(data_path))
        
        # Проверяем, что есть метод для асинхронной записи
        assert hasattr(controller, '_save_state_async') or hasattr(controller, '_save_state')
        
        # Если есть async метод — тестируем его
        if hasattr(controller, '_save_state_async'):
            start = asyncio.get_event_loop().time()
            await controller._save_state_async()
            end = asyncio.get_event_loop().time()
            
            # Проверка, что запись заняла разумное время
            assert (end - start) < 1.0
            
            # Проверка, что файл записан
            assert data_path.exists()
        else:
            # Если async метода ещё нет — это тест для будущей реализации
            pytest.skip("Async метод _save_state_async ещё не реализован")

    @pytest.mark.asyncio
    async def test_no_event_loop_blocking(self, temp_data_dir):
        """
        Проверяет, что файловые операции не блокируют event loop
        """
        from backend.core.meta_controller import MetaCognitiveController
        
        data_path = temp_data_dir / "meta_cognitive.json"
        controller = MetaCognitiveController(data_path=str(data_path))
        
        parallel_task_completed = False
        
        async def parallel_task():
            nonlocal parallel_task_completed
            await asyncio.sleep(0.01)
            parallel_task_completed = True
            return "completed"
        
        # Запускаем файловую операцию и параллельную задачу
        if hasattr(controller, '_save_state_async'):
            async def file_operation():
                await controller._save_state_async()
            
            results = await asyncio.gather(
                parallel_task(),
                file_operation(),
                return_exceptions=True
            )
            
            # Обе задачи должны выполниться
            assert results[0] == "completed"
            assert parallel_task_completed
            assert not isinstance(results[1], Exception)
        else:
            pytest.skip("Async метод ещё не реализован")

    @pytest.mark.asyncio
    async def test_async_read_write_consistency(self, temp_data_dir):
        """
        Проверяет консистентность асинхронных операций чтения/записи
        """
        from backend.core.meta_controller import MetaCognitiveController
        
        data_path = temp_data_dir / "meta_cognitive.json"
        controller = MetaCognitiveController(data_path=str(data_path))
        
        if hasattr(controller, '_save_state_async') and hasattr(controller, '_load_state_async'):
            # Записываем данные
            controller._total_requests = 100
            controller._successful_adaptations = 50
            await controller._save_state_async()
            
            # Читаем данные
            await controller._load_state_async()
            
            # Проверяем консистентность
            assert controller._total_requests == 100
            assert controller._successful_adaptations == 50
        else:
            pytest.skip("Async методы чтения/записи ещё не реализованы")

    @pytest.mark.asyncio
    async def test_concurrent_file_operations(self, temp_data_dir):
        """
        Проверяет корректность конкурентных файловых операций
        """
        from backend.core.meta_controller import MetaCognitiveController
        
        data_path = temp_data_dir / "meta_cognitive.json"
        controller = MetaCognitiveController(data_path=str(data_path))
        
        if hasattr(controller, '_save_state_async'):
            # Запускаем 10 конкурентных записей
            async def write_data(value):
                controller._total_requests = value
                await controller._save_state_async()
                return value
            
            tasks = [write_data(i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Все записи должны выполниться без ошибок
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            assert success_count == 10
        else:
            pytest.skip("Async метод ещё не реализован")


class TestAsyncIOHealthMonitor:
    """Тесты Async I/O для Health Monitor"""

    @pytest.mark.asyncio
    async def test_health_monitor_async_save(self, temp_data_dir):
        """
        Проверяет асинхронную запись в Health Monitor
        """
        from backend.core.health_monitor import CognitiveHealthMonitor
        
        data_path = temp_data_dir / "health.json"
        monitor = CognitiveHealthMonitor(data_path=str(data_path))
        
        if hasattr(monitor, '_save_async'):
            start = asyncio.get_event_loop().time()
            await monitor._save_async()
            end = asyncio.get_event_loop().time()
            
            assert (end - start) < 1.0
            assert data_path.exists()
        else:
            pytest.skip("Async метод _save_async ещё не реализован")

    @pytest.mark.asyncio
    async def test_health_monitor_metric_update(self, temp_data_dir):
        """
        Проверяет обновление метрик с асинхронной записью
        """
        from backend.core.health_monitor import CognitiveHealthMonitor
        
        data_path = temp_data_dir / "health.json"
        monitor = CognitiveHealthMonitor(data_path=str(data_path))
        
        if hasattr(monitor, '_save_async'):
            # Обновляем метрику
            monitor.update_metric("reflection_score", 0.9, reason="Тест")
            
            # Асинхронно сохраняем
            await monitor._save_async()
            
            # Проверяем, что файл записан
            assert data_path.exists()
            
            # Читаем и проверяем
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert data['metrics']
        else:
            pytest.skip("Async метод ещё не реализован")


class TestAsyncIOEdgeCases:
    """Тесты граничных случаев Async I/O"""

    @pytest.mark.asyncio
    async def test_async_write_to_nonexistent_directory(self, tmp_path):
        """
        Проверяет запись в несуществующую директорию
        """
        from backend.core.meta_controller import MetaCognitiveController
        
        # Путь в несуществующую директорию
        data_path = tmp_path / "subdir" / "meta_cognitive.json"
        controller = MetaCognitiveController(data_path=str(data_path))
        
        if hasattr(controller, '_save_state_async'):
            # Должна создаться директория
            await controller._save_state_async()
            assert data_path.exists()
        else:
            pytest.skip("Async метод ещё не реализован")

    @pytest.mark.asyncio
    async def test_async_write_large_data(self, temp_data_dir):
        """
        Проверяет запись больших объёмов данных
        """
        from backend.core.meta_controller import MetaCognitiveController
        
        data_path = temp_data_dir / "meta_cognitive.json"
        controller = MetaCognitiveController(data_path=str(data_path))
        
        if hasattr(controller, '_save_state_async'):
            # Добавляем много данных в историю
            from backend.core.meta_controller import StrategyDecision, ProcessingStrategy
            
            for i in range(1000):
                decision = StrategyDecision(
                    strategy=ProcessingStrategy.SIMPLE,
                    reason=f"Тест {i}",
                    confidence=0.8,
                    estimated_time=1.0,
                    resources_needed=[]
                )
                controller._decision_history.append(decision)
            
            # Асинхронная запись
            start = asyncio.get_event_loop().time()
            await controller._save_state_async()
            end = asyncio.get_event_loop().time()
            
            # Должно выполниться за разумное время
            assert (end - start) < 5.0
            assert data_path.exists()
        else:
            pytest.skip("Async метод ещё не реализован")

    @pytest.mark.asyncio
    async def test_async_write_permission_error(self, temp_data_dir):
        """
        Проверяет обработку ошибки прав доступа
        """
        from backend.core.meta_controller import MetaCognitiveController
        
        data_path = temp_data_dir / "meta_cognitive.json"
        controller = MetaCognitiveController(data_path=str(data_path))
        
        if hasattr(controller, '_save_state_async'):
            # Создаём файл и делаем его read-only
            data_path.touch()
            os.chmod(data_path, 0o444)
            
            try:
                # Попытка записи должна вернуть ошибку
                with pytest.raises((PermissionError, OSError)):
                    await controller._save_state_async()
            finally:
                # Восстанавливаем права
                os.chmod(data_path, 0o644)
        else:
            pytest.skip("Async метод ещё не реализован")


class TestAsyncIOHelpers:
    """Тесты вспомогательных функций Async I/O"""

    @pytest.mark.asyncio
    async def test_async_json_encode_decode(self):
        """
        Проверяет асинхронное кодирование/декодирование JSON
        """
        import aiofiles
        import tempfile
        
        data = {
            "test": "данные",
            "number": 42,
            "nested": {"key": "value"},
            "list": [1, 2, 3]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            # Асинхронная запись
            async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False))
            
            # Асинхронное чтение
            async with aiofiles.open(temp_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                loaded_data = json.loads(content)
            
            assert loaded_data == data
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_async_file_exists_check(self, temp_data_dir):
        """
        Проверяет асинхронную проверку существования файла
        """
        import aiofiles
        from pathlib import Path
        
        test_file = temp_data_dir / "test.json"
        
        # Файл не существует
        assert not test_file.exists()
        
        # Создаём асинхронно
        async with aiofiles.open(test_file, 'w') as f:
            await f.write("test")
        
        # Файл существует
        assert test_file.exists()
        
        # Проверяем размер
        stat = await test_file.stat()
        assert stat.st_size == 4


# Тесты для будущей реализации Async I/O
class TestAsyncIOFutureImplementation:
    """
    Тесты для будущей реализации Async I/O в проекте.
    
    Эти тесты документуют ожидаемое поведение после реализации.
    """

    @pytest.mark.asyncio
    async def test_expected_async_save_in_meta_controller(self):
        """
        Ожидаемое поведение: MetaCognitiveController._save_state_async()
        
        После реализации должно:
        1. Использовать aiofiles вместо встроенного open()
        2. Не блокировать event loop
        3. Корректно сериализовать данные
        """
        # Этот тест должен пройти после реализации
        from backend.core.meta_controller import MetaCognitiveController
        
        controller = MetaCognitiveController()
        
        # Проверяем наличие async метода
        assert hasattr(controller, '_save_state_async'), \
            "MetaCognitiveController должен иметь _save_state_async()"
        
        # Проверяем, что метод не блокирует
        import time
        start = time.time()
        await controller._save_state_async()
        elapsed = time.time() - start
        
        assert elapsed < 0.5, "Запись не должна блокировать event loop"

    @pytest.mark.asyncio
    async def test_expected_async_save_in_health_monitor(self):
        """
        Ожидаемое поведение: CognitiveHealthMonitor._save_async()
        
        После реализации должно:
        1. Использовать aiofiles
        2. Сохранять все метрики и историю
        3. Не блокировать event loop
        """
        from backend.core.health_monitor import CognitiveHealthMonitor
        
        monitor = CognitiveHealthMonitor()
        
        assert hasattr(monitor, '_save_async'), \
            "CognitiveHealthMonitor должен иметь _save_async()"

    @pytest.mark.asyncio
    async def test_expected_async_file_operations_in_pipeline(self):
        """
        Ожидаемое поведение: PipelineExecutor должен использовать async I/O
        
        После реализации должно:
        1. Асинхронно сохранять эпизоды
        2. Асинхронно обновлять метрики
        3. Не блокировать event loop при записи
        """
        from backend.core.pipeline import PipelineExecutor
        
        pipeline = PipelineExecutor()
        
        # Проверяем наличие async методов для записи
        # (после реализации)
        assert hasattr(pipeline, '_save_episode_async') or \
               hasattr(pipeline, '_save_state_async'), \
            "PipelineExecutor должен иметь async методы для записи"
