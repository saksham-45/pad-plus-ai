"""
📦 Memory Base Interface — Единый интерфейс для всех систем памяти

Цель: Устранить дублирование и обеспечить согласованность
Все системы памяти должны реализовывать этот интерфейс.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger("padplus.memory.base")


@dataclass
class MemoryRecord:
    """Базовая запись памяти"""
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class MemoryInterface(ABC):
    """Базовый интерфейс для всех систем памяти"""
    
    @abstractmethod
    async def store(self, data: Dict[str, Any], **kwargs) -> str:
        """
        Сохранить данные в память
        
        Args:
            data: Данные для сохранения
            **kwargs: Дополнительные параметры (user_id, session_id, etc.)
        
        Returns:
            str: ID сохраненной записи
        """
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """
        Поиск по памяти
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            **kwargs: Дополнительные параметры (user_id, min_confidence, etc.)
        
        Returns:
            List[Dict]: Список найденных записей
        """
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """
        Удалить запись по ID
        
        Args:
            id: ID записи для удаления
        
        Returns:
            bool: True если успешно
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику памяти
        
        Returns:
            Dict: Статистика (количество записей, размер, etc.)
        """
        pass
    
    async def clear(self, **kwargs) -> bool:
        """
        Очистить всю память (опционально)
        
        Returns:
            bool: True если успешно
        """
        raise NotImplementedError("clear not implemented")
    
    async def update(self, id: str, data: Dict[str, Any]) -> bool:
        """
        Обновить запись (опционально)
        
        Args:
            id: ID записи
            data: Новые данные
        
        Returns:
            bool: True если успешно
        """
        raise NotImplementedError("update not implemented")
    
    async def get(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Получить запись по ID (опционально)
        
        Args:
            id: ID записи
        
        Returns:
            Optional[Dict]: Запись или None
        """
        raise NotImplementedError("get not implemented")