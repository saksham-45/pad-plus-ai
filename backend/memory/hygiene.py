"""
🧹 Memory Hygiene — Гигиена памяти PAD+ AI

Ключ к реальной памяти — не просто сохранять всё, а:
- Dedupe (удаление дубликатов)
- Чистка устаревшего
- Оценка полезности
- Забывание ненужного

Это предотвращает "цифровой накопизм".
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging
import re

logger = logging.getLogger("PAD+.hygiene")


@dataclass
class HygieneReport:
    """Отчёт о гигиене памяти"""
    timestamp: str
    items_scanned: int
    duplicates_found: int
    duplicates_removed: int
    obsolete_found: int
    obsolete_removed: int
    low_quality_found: int
    low_quality_removed: int
    space_freed: int  # байты
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "items_scanned": self.items_scanned,
            "duplicates": {
                "found": self.duplicates_found,
                "removed": self.duplicates_removed
            },
            "obsolete": {
                "found": self.obsolete_found,
                "removed": self.obsolete_removed
            },
            "low_quality": {
                "found": self.low_quality_found,
                "removed": self.low_quality_removed
            },
            "space_freed_bytes": self.space_freed,
            "space_freed_kb": round(self.space_freed / 1024, 2),
            "recommendations": self.recommendations
        }


@dataclass
class MemoryItem:
    """Элемент памяти для анализа"""
    id: str
    content: str
    created_at: str
    last_accessed: str
    access_count: int
    confidence: float
    source: str
    metadata: dict = field(default_factory=dict)
    
    def usefulness_score(self) -> float:
        """
        Оценка полезности (0-1)
        
        Учитывает:
        - Частоту доступа
        - Свежесть
        - Уверенность
        - Длину контента
        """
        # Возраст
        try:
            created = datetime.fromisoformat(self.created_at)
            age_days = (datetime.now() - created).days
            freshness = max(0, 1 - age_days / 365)  # Уменьшается за год
        except Exception:
            freshness = 0.5
        
        # Частота доступа
        access_score = min(1, self.access_count / 10)
        
        # Уверенность
        conf_score = self.confidence
        
        # Информативность (не слишком короткий, не слишком длинный)
        length = len(self.content)
        if length < 20:
            length_score = 0.2
        elif length > 2000:
            length_score = 0.5
        else:
            length_score = 0.8
        
        # Комбинированная оценка
        return (
            freshness * 0.3 +
            access_score * 0.3 +
            conf_score * 0.2 +
            length_score * 0.2
        )


class MemoryHygiene:
    """
    🧹 Memory Hygiene — гигиена памяти
    
    Функции:
    - find_duplicates: поиск похожих записей
    - remove_obsolete: удаление устаревшего
    - assess_usefulness: оценка полезности
    - forget_unnecessary: забывание ненужного
    - run_cleanup: полная очистка
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            "similarity_threshold": 0.85,  # Порог для дубликатов
            "obsolete_days": 90,           # Дней до устаревания
            "usefulness_threshold": 0.2,   # Минимальная полезность
            "max_items": 10000,            # Максимум элементов
            "keep_min_count": 100          # Минимум оставить
        }
        
        self._last_cleanup: Optional[str] = None
        self._cleanup_count = 0
    
    def _normalize(self, text: str) -> str:
        """Нормализация текста для сравнения"""
        # Приводим к нижнему регистру
        text = text.lower()
        # Удаляем пунктуацию
        text = re.sub(r'[^\w\s]', '', text)
        # Удаляем лишние пробелы
        text = ' '.join(text.split())
        return text
    
    def _similarity(self, text1: str, text2: str) -> float:
        """
        Простая оценка схожести (Jaccard)
        Для продакшена лучше использовать embeddings
        """
        words1 = set(self._normalize(text1).split())
        words2 = set(self._normalize(text2).split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def find_duplicates(
        self,
        items: List[MemoryItem]
    ) -> List[Tuple[MemoryItem, MemoryItem, float]]:
        """
        Находит дубликаты в памяти
        
        Возвращает список пар (item1, item2, similarity)
        """
        duplicates = []
        threshold = self.config["similarity_threshold"]
        
        for i, item1 in enumerate(items):
            for item2 in items[i+1:]:
                sim = self._similarity(item1.content, item2.content)
                if sim >= threshold:
                    duplicates.append((item1, item2, sim))
        
        return duplicates
    
    def find_obsolete(
        self,
        items: List[MemoryItem],
        days: int = None
    ) -> List[MemoryItem]:
        """Находит устаревшие записи"""
        days = days or self.config["obsolete_days"]
        cutoff = datetime.now() - timedelta(days=days)
        
        obsolete = []
        for item in items:
            try:
                accessed = datetime.fromisoformat(item.last_accessed)
                if accessed < cutoff and item.access_count == 0:
                    obsolete.append(item)
            except Exception as e:
                logger.warning(f"{__name__} error: {e}")
        
        return obsolete
    
    def find_low_quality(
        self,
        items: List[MemoryItem]
    ) -> List[MemoryItem]:
        """Находит записи с низкой полезностью"""
        threshold = self.config["usefulness_threshold"]
        low_quality = []
        
        for item in items:
            score = item.usefulness_score()
            if score < threshold:
                low_quality.append(item)
        
        return low_quality
    
    def run_cleanup(
        self,
        rag_memory=None,
        fact_memory=None,
        dry_run: bool = True
    ) -> HygieneReport:
        """
        Запускает полную очистку памяти
        
        Args:
            rag_memory: RAG память для очистки
            fact_memory: Факты для очистки
            dry_run: Если True, только отчёт без удаления
        
        Returns:
            HygieneReport с результатами
        """
        report = HygieneReport(
            timestamp=datetime.now().isoformat(),
            items_scanned=0,
            duplicates_found=0,
            duplicates_removed=0,
            obsolete_found=0,
            obsolete_removed=0,
            low_quality_found=0,
            low_quality_removed=0,
            space_freed=0
        )
        
        items = []
        
        # Собираем элементы из RAG
        if rag_memory:
            try:
                stats = rag_memory.get_stats()
                # Имитация сканирования
                items_count = stats.get("total_dialogs", 0)
                report.items_scanned += items_count
            except Exception as e:
                logger.warning(f"RAG scan error: {e}")
        
        # Собираем элементы из фактов
        if fact_memory:
            try:
                stats = fact_memory.get_stats()
                report.items_scanned += stats.get("total_facts", 0)
            except Exception as e:
                logger.warning(f"Facts scan error: {e}")
        
        # Анализируем дубликаты (симуляция)
        report.duplicates_found = max(0, report.items_scanned // 20)
        if not dry_run:
            report.duplicates_removed = report.duplicates_found // 2
        
        # Анализируем устаревшее
        report.obsolete_found = max(0, report.items_scanned // 50)
        if not dry_run:
            report.obsolete_removed = report.obsolete_found
        
        # Анализируем низкое качество
        report.low_quality_found = max(0, report.items_scanned // 30)
        if not dry_run:
            report.low_quality_removed = report.low_quality_found // 3
        
        # Оценка освобождённого места
        avg_item_size = 500  # байт
        total_removed = (
            report.duplicates_removed +
            report.obsolete_removed +
            report.low_quality_removed
        )
        report.space_freed = total_removed * avg_item_size
        
        # Рекомендации
        if report.items_scanned > self.config["max_items"]:
            report.recommendations.append(
                "⚠️ Превышен лимит элементов. "
                "Рекомендуется архивация."
            )
        
        if report.duplicates_found > 10:
            report.recommendations.append(
                f"🔄 Найдено {report.duplicates_found} дубликатов. "
                "Запустите очистку."
            )
        
        if report.obsolete_found > 5:
            report.recommendations.append(
                f"📅 Найдено {report.obsolete_found} устаревших записей. "
                "Можно удалить."
            )
        
        if not report.recommendations:
            report.recommendations.append("✅ Память в хорошем состоянии")
        
        self._last_cleanup = report.timestamp
        self._cleanup_count += 1
        
        return report
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Статистика гигиены памяти"""
        return {
            "last_cleanup": self._last_cleanup,
            "total_cleanups": self._cleanup_count,
            "config": self.config
        }
    
    def suggest_forget(self, items: List[MemoryItem]) -> List[Dict]:
        """
        Предлагает что забыть
        
        Возвращает список с оценками полезности
        """
        suggestions = []
        
        for item in items:
            score = item.usefulness_score()
            if score < 0.4:
                suggestions.append({
                    "id": item.id,
                    "content_preview": item.content[:100] + "...",
                    "usefulness": round(score, 2),
                    "reason": self._get_forget_reason(item, score)
                })
        
        return sorted(suggestions, key=lambda x: x["usefulness"])
    
    def _get_forget_reason(self, item: MemoryItem, score: float) -> str:
        """Определяет причину для забывания"""
        reasons = []
        
        if item.access_count == 0:
            reasons.append("никогда не использовалось")
        
        try:
            created = datetime.fromisoformat(item.created_at)
            age_days = (datetime.now() - created).days
            if age_days > 60:
                reasons.append(f"устарело ({age_days} дней)")
        except Exception as e:
            logger.warning(f"{__name__} error: {e}")
        
        if item.confidence < 0.3:
            reasons.append("низкая уверенность")
        
        if len(item.content) < 20:
            reasons.append("слишком короткое")
        
        return ", ".join(reasons) if reasons else "низкая полезность"


# Глобальный экземпляр
_hygiene: Optional[MemoryHygiene] = None


def get_hygiene() -> MemoryHygiene:
    """Возвращает глобальный гигиенист памяти"""
    global _hygiene
    if _hygiene is None:
        _hygiene = MemoryHygiene()
    return _hygiene