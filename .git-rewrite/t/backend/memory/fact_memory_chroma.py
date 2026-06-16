"""
🧠 FactMemoryChroma — Атомарные факты на ChromaDB

Хранит факты с векторным поиском:
- Семантический поиск (по смыслу, не по ключевым словам)
- Фильтрация по confidence, source, status
- Автоматическое кластеризование похожих фактов
- NEVER mixes with persona

Наследуется от ChromaMemory для устранения дублирования.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid
import logging

from core.chroma_memory import ChromaMemory

# FactStatus enum локально
from enum import Enum

class FactStatus(str, Enum):
    HYPOTHESIS = "hypothesis"
    VERIFIED = "verified"
    REFUTED = "refuted"
    OBSOLETE = "obsolete"

logger = logging.getLogger("PAD+.facts_chroma")


@dataclass
class FactChroma:
    """
    Атомарный факт для ChromaDB

    Тройка (subject, predicate, object) с метаданными.
    """
    id: str
    subject: str
    predicate: str
    object: str
    confidence: float = 0.5
    status: FactStatus = FactStatus.HYPOTHESIS
    source: str = "unknown"
    source_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Преобразует в словарь для ChromaDB"""
        return {
            "id": self.id,
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "confidence": round(self.confidence, 3),
            "status": self.status.value,
            "source": self.source,
            "source_id": self.source_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count
        }

    def to_sentence(self) -> str:
        """Возвращает как предложение"""
        return f"{self.subject} {self.predicate} {self.object}"

    @classmethod
    def from_chroma(cls, chroma_dict: dict) -> 'FactChroma':
        """Создаёт из словаря ChromaDB"""
        return cls(
            id=chroma_dict['id'],
            subject=chroma_dict['subject'],
            predicate=chroma_dict['predicate'],
            object=chroma_dict['object'],
            confidence=chroma_dict['confidence'],
            status=FactStatus(chroma_dict['status']),
            source=chroma_dict['source'],
            source_id=chroma_dict.get('source_id', ''),
            created_at=datetime.fromisoformat(chroma_dict['created_at']),
            updated_at=datetime.fromisoformat(chroma_dict['updated_at']),
            accessed_at=datetime.fromisoformat(chroma_dict['accessed_at']),
            access_count=chroma_dict.get('access_count', 0),
            metadata=chroma_dict.get('metadata', {})
        )


class FactMemoryChroma(ChromaMemory[FactChroma]):
    """
    🧠 FactMemoryChroma — хранилище атомарных фактов на ChromaDB

    Ключевые особенности:
    - Векторный поиск (семантический, по смыслу)
    - Фильтрация по confidence, source, status
    - Автоматическое кластеризование
    - Факты НЕ смешиваются с личностью
    
    Наследуется от ChromaMemory для устранения дублирования.
    """
    
    COLLECTION_NAME = "facts"
    DEFAULT_TTL = 2592000  # 30 дней
    MIN_CONFIDENCE = 0.3
    
    def __init__(self, collection_name: Optional[str] = None, db_path: str = "data/chroma"):
        """
        Инициализирует FactMemoryChroma
        
        Args:
            collection_name: Имя коллекции
            db_path: Путь к хранилищу ChromaDB
        """
        super().__init__(collection_name, db_path)
    
    def _create_metadata(self, record: FactChroma) -> Dict[str, Any]:
        """Создаёт метаданные для факта"""
        return {
            "id": record.id,
            "subject": record.subject,
            "predicate": record.predicate,
            "object": record.object,
            "confidence": record.confidence,
            "status": record.status.value,
            "source": record.source,
            "source_id": record.source_id,
            "type": "fact"
        }
    
    def _record_from_metadata(self, metadata: Dict[str, Any]) -> FactChroma:
        """Восстанавливает факт из метаданных"""
        return FactChroma.from_chroma(metadata)
    
    def _get_record_text(self, record: FactChroma) -> str:
        """Возвращает текстовое представление факта"""
        return record.to_sentence()

    # === Специфичные методы для фактов ===
    
    def add(
        self,
        subject: str,
        predicate: str,
        object: str,
        confidence: float = 0.5,
        source: str = "unknown",
        source_id: str = "",
        status: FactStatus = FactStatus.HYPOTHESIS,
        metadata: Dict = None
    ) -> str:
        """
        Добавляет факт в память
        
        Args:
            subject: Субъект (кто/что)
            predicate: Предикат (действие/свойство)
            object: Объект (на что направлено)
            confidence: Уверенность (0.0-1.0)
            source: Источник факта
            source_id: ID источника
            status: Статус факта
            metadata: Дополнительные метаданные
        
        Returns:
            ID добавленного факта
        """
        try:
            # Проверяем на дубликат (семантически похожий)
            similar = self._find_similar(subject, predicate, object)
            if similar:
                # Обновляем существующий
                self._update_confidence(similar['id'], confidence)
                logger.debug(f"Обновлён факт: {subject} {predicate} {object}")
                return similar['id']
            
            # Создаём новый факт
            fact_id = f"fact_{uuid.uuid4().hex[:8]}"
            fact = FactChroma(
                id=fact_id,
                subject=subject.lower().strip(),
                predicate=predicate.lower().strip(),
                object=object.lower().strip(),
                confidence=confidence,
                status=status,
                source=source,
                source_id=source_id,
                metadata=metadata or {}
            )
            
            # Сохраняем через базовый класс
            return super().store(fact)
            
        except Exception as e:
            logger.error(f"Ошибка добавления факта: {e}")
            raise

    def _find_similar(
        self,
        subject: str,
        predicate: str,
        object: str
    ) -> Optional[Dict]:
        """Находит семантически похожие факты"""
        try:
            query_text = f"{subject} {predicate} {object}".lower().strip()
            
            results = self.collection.query(
                query_texts=[query_text],
                n_results=1,
                include=["metadatas", "distances"]
            )
            
            if not results['ids'] or not results['ids'][0]:
                return None
            
            # Проверяем расстояние (похожесть)
            distance = results['distances'][0][0]
            if distance < 0.1:  # Очень похоже
                return results['metadatas'][0][0]
            
            return None
        except Exception as e:
            logger.warning(f"Ошибка поиска похожих фактов: {e}")
            return None

    def _update_confidence(self, fact_id: str, delta: float):
        """Обновляет confidence факта"""
        try:
            # Получаем текущий факт
            results = self.collection.get(ids=[fact_id], include=["metadatas"])
            
            if not results['metadatas'] or not results['metadatas'][0]:
                return
            
            metadata = results['metadatas'][0]
            metadata['confidence'] = min(float(metadata.get('confidence', 0.5)) + delta * 0.3, 0.95)
            metadata['updated_at'] = datetime.now().isoformat()
            metadata['access_count'] = int(metadata.get('access_count', 0)) + 1
            
            # Обновляем в ChromaDB
            self.collection.update(
                ids=[fact_id],
                metadatas=[metadata]
            )
        except Exception as e:
            logger.warning(f"Ошибка обновления confidence: {e}")

    def search(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.3,
        source: str = None
    ) -> List[FactChroma]:
        """
        Семантический поиск фактов
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            min_confidence: Минимальная уверенность
            source: Фильтр по источнику
        
        Returns:
            Список найденных фактов
        """
        try:
            # Фильтр
            where_filter: Dict[str, Any] = {}
            if min_confidence > 0:
                where_filter["confidence"] = {"$gte": min_confidence}
            if source:
                where_filter["source"] = source
            
            # Поиск
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"]
            )
            
            # Форматируем результаты
            facts = []
            if results and results.get('ids') and results['ids'][0]:
                for i, fact_id in enumerate(results['ids'][0]):
                    if results['metadatas'] and i < len(results['metadatas'][0]):
                        metadata = results['metadatas'][0][i]
                        fact = FactChroma.from_chroma(metadata)
                        facts.append(fact)
            
            logger.debug(f"🔍 Найдено фактов: {len(facts)} по запросу '{query}'")
            return facts
            
        except Exception as e:
            logger.warning(f"Ошибка поиска фактов: {e}")
            return []

    def find_by_subject(
        self,
        subject: str,
        min_confidence: float = 0.3,
        limit: int = 20
    ) -> List[FactChroma]:
        """Находит все факты о субъекте"""
        return self.search(subject, min_confidence, limit)

    def find_by_predicate(
        self,
        predicate: str,
        min_confidence: float = 0.3,
        limit: int = 20
    ) -> List[FactChroma]:
        """Находит все факты с данным предикатом"""
        # Поиск по всем фактам с фильтрацией по предикату
        all_facts = self.search(predicate, min_confidence, limit=100)
        return [f for f in all_facts if f.predicate == predicate][:limit]

    def get_related(
        self,
        subject: str,
        depth: int = 2,
        min_confidence: float = 0.3
    ) -> List[FactChroma]:
        """Получает связанные факты (графовый обход)"""
        visited = set()
        result = []
        
        def traverse(s: str, d: int):
            if d <= 0 or s in visited:
                return
            visited.add(s)
            
            facts = self.find_by_subject(s, min_confidence)
            for fact in facts:
                if fact.id not in [f.id for f in result]:
                    result.append(fact)
                    # Рекурсивно обходим через object
                    traverse(fact.object, d - 1)
        
        traverse(subject.lower(), depth)
        return result

    def update_confidence(
        self,
        fact_id: str,
        delta: float
    ) -> Optional[FactChroma]:
        """Обновляет confidence факта"""
        self._update_confidence(fact_id, delta)
        
        # Получаем обновлённый факт
        try:
            results = self.collection.get(ids=[fact_id], include=["metadatas"])
            if results and results.get('metadatas') and results['metadatas'][0]:
                return FactChroma.from_chroma(results['metadatas'][0])
        except Exception as e:
            logger.warning(f"Ошибка получения обновлённого факта: {e}")
        return None

    def delete(self, record_id: str) -> bool:
        """Удаляет факт по ID"""
        try:
            result = super().delete(record_id)
            logger.info(f"🗑️ Факт удалён: {record_id}")
            return result
        except Exception as e:
            logger.error(f"Ошибка удаления факта: {e}")
            return False

    def get(self, record_id: str) -> Optional[FactChroma]:
        """Получает факт по ID"""
        try:
            result = super().get(record_id)
            return result
        except Exception as e:
            logger.warning(f"Ошибка получения факта: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Статистика памяти фактов"""
        try:
            total = self.collection.count()
            
            # Получаем все факты для статистики
            all_facts = []
            if total > 0:
                results = self.collection.get(include=["metadatas"])
                if results and results.get('metadatas'):
                    for m in results['metadatas']:
                        try:
                            fact = FactChroma.from_chroma(m)
                            all_facts.append(fact)
                        except Exception:
                            pass
            
            # Статистика по статусам
            status_dist = {}
            for fact in all_facts:
                status = fact.status.value
                status_dist[status] = status_dist.get(status, 0) + 1
            
            # Средняя confidence
            avg_conf = sum(f.confidence for f in all_facts) / len(all_facts) if all_facts else 0
            
            # Высокая/низкая confidence
            high_conf = sum(1 for f in all_facts if f.confidence >= 0.7)
            low_conf = sum(1 for f in all_facts if f.confidence < 0.3)
            
            # Топ предикатов
            predicates = {}
            for fact in all_facts:
                pred = fact.predicate
                predicates[pred] = predicates.get(pred, 0) + 1
            top_predicates = dict(sorted(predicates.items(), key=lambda x: x[1], reverse=True)[:5])
            
            return {
                "total_facts": total,
                "status_distribution": status_dist,
                "average_confidence": round(avg_conf, 3),
                "high_confidence_count": high_conf,
                "low_confidence_count": low_conf,
                "top_predicates": top_predicates,
                "collection": self.collection_name
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                "total_facts": 0,
                "status_distribution": {},
                "average_confidence": 0,
                "high_confidence_count": 0,
                "low_confidence_count": 0,
                "top_predicates": {},
                "collection": self.collection_name,
                "error": str(e)
            }

    def clear(self):
        """Очищает память фактов"""
        try:
            super().clear()
            logger.info("🗑️ FactMemoryChroma очищена")
        except Exception as e:
            logger.error(f"Ошибка очистки памяти фактов: {e}")


# Глобальный экземпляр
_fact_memory_chroma: Optional[FactMemoryChroma] = None


def get_fact_memory_chroma() -> FactMemoryChroma:
    """Возвращает глобальную память фактов на ChromaDB"""
    global _fact_memory_chroma
    if _fact_memory_chroma is None:
        _fact_memory_chroma = FactMemoryChroma()
    return _fact_memory_chroma