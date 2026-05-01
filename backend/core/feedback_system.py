"""
⭐ FeedbackSystem — Система обратной связи (RLHF)

- Оценка ответов пользователями
- Накопление данных для обучения
- Аналитика качества
- Персонализация на основе предпочтений
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
import json
import os
import logging

logger = logging.getLogger("PAD+.feedback")


class FeedbackType(Enum):
    """Типы обратной связи"""
    THUMBS_UP = "thumbs_up"         # Палец вверх
    THUMBS_DOWN = "thumbs_down"     # Палец вниз
    RATING = "rating"               # Оценка 1-5
    CORRECTION = "correction"       # Исправление
    DETAILED = "detailed"           # Подробный отзыв


@dataclass
class FeedbackEntry:
    """Запись обратной связи"""
    id: str
    user_message: str
    ai_response: str
    feedback_type: FeedbackType
    rating: Optional[int] = None       # 1-5 для RATING
    correction: Optional[str] = None   # Для CORRECTION
    comment: Optional[str] = None      # Комментарий
    intent: str = ""
    provider: str = ""
    confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_message": self.user_message[:100],
            "ai_response": self.ai_response[:200],
            "feedback_type": self.feedback_type.value,
            "rating": self.rating,
            "correction": self.correction,
            "comment": self.comment,
            "intent": self.intent,
            "provider": self.provider,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


class FeedbackSystem:
    """
    ⭐ Система обратной связи
    
    Features:
    - Сбор оценок от пользователей
    - Анализ качества ответов
    - Выявление паттернов
    - Подготовка данных для RLHF
    """
    
    def __init__(self, data_path: str = None):
        if data_path is None:
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "feedback.json"
            )
        self.data_path = data_path
        self._feedback: List[FeedbackEntry] = []
        self._stats = {
            "total_feedback": 0,
            "positive_count": 0,
            "negative_count": 0,
            "average_rating": 0.0,
            "corrections_count": 0
        }
        self._load()
    
    def _load(self):
        """Загружает данные из файла"""
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    for item in data.get('feedback', []):
                        entry = FeedbackEntry(
                            id=item['id'],
                            user_message=item['user_message'],
                            ai_response=item['ai_response'],
                            feedback_type=FeedbackType(item['feedback_type']),
                            rating=item.get('rating'),
                            correction=item.get('correction'),
                            comment=item.get('comment'),
                            intent=item.get('intent', ''),
                            provider=item.get('provider', ''),
                            confidence=item.get('confidence', 0.0),
                            created_at=datetime.fromisoformat(item['created_at']),
                            metadata=item.get('metadata', {})
                        )
                        self._feedback.append(entry)
                    
                    self._stats = data.get('stats', self._stats)
                    
            except Exception as e:
                logger.warning(f"Ошибка загрузки feedback: {e}")
    
    def _save(self):
        """Сохраняет данные в файл"""
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        
        data = {
            "updated": datetime.now().isoformat(),
            "feedback": [f.to_dict() for f in self._feedback[-1000:]],  # Последние 1000
            "stats": self._stats
        }
        
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_feedback(
        self,
        user_message: str,
        ai_response: str,
        feedback_type: FeedbackType,
        rating: int = None,
        correction: str = None,
        comment: str = None,
        intent: str = "",
        provider: str = "",
        confidence: float = 0.0,
        metadata: Dict = None
    ) -> FeedbackEntry:
        """Добавляет обратную связь"""
        import uuid
        
        entry = FeedbackEntry(
            id=f"fb_{uuid.uuid4().hex[:8]}",
            user_message=user_message,
            ai_response=ai_response,
            feedback_type=feedback_type,
            rating=rating,
            correction=correction,
            comment=comment,
            intent=intent,
            provider=provider,
            confidence=confidence,
            metadata=metadata or {}
        )
        
        self._feedback.append(entry)
        self._update_stats(entry)
        self._save()
        
        logger.info(f"⭐ Feedback added: {feedback_type.value}")
        return entry
    
    def _update_stats(self, entry: FeedbackEntry):
        """Обновляет статистику"""
        self._stats["total_feedback"] += 1
        
        if entry.feedback_type == FeedbackType.THUMBS_UP:
            self._stats["positive_count"] += 1
        elif entry.feedback_type == FeedbackType.THUMBS_DOWN:
            self._stats["negative_count"] += 1
        elif entry.feedback_type == FeedbackType.RATING:
            ratings = [f.rating for f in self._feedback 
                      if f.feedback_type == FeedbackType.RATING]
            self._stats["average_rating"] = sum(ratings) / len(ratings)
        elif entry.feedback_type == FeedbackType.CORRECTION:
            self._stats["corrections_count"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику"""
        total = self._stats["total_feedback"]
        positive = self._stats["positive_count"]
        negative = self._stats["negative_count"]
        
        satisfaction = positive / (positive + negative) if (positive + negative) > 0 else 0.5
        
        return {
            "total_feedback": total,
            "positive_count": positive,
            "negative_count": negative,
            "satisfaction_rate": round(satisfaction, 3),
            "average_rating": round(self._stats["average_rating"], 2),
            "corrections_count": self._stats["corrections_count"],
            "recent_feedback": len([f for f in self._feedback 
                                   if (datetime.now() - f.created_at).days < 7])
        }
    
    def get_learning_data(self, limit: int = 100) -> List[Dict]:
        """
        Возвращает данные для обучения (RLHF)
        
        Формат: prompt, response, score
        """
        data = []
        
        for entry in self._feedback[-limit:]:
            # Вычисляем score на основе типа feedback
            score = 0.5  # Базовый
            
            if entry.feedback_type == FeedbackType.THUMBS_UP:
                score = 1.0
            elif entry.feedback_type == FeedbackType.THUMBS_DOWN:
                score = 0.0
            elif entry.feedback_type == FeedbackType.RATING:
                score = entry.rating / 5.0 if entry.rating else 0.5
            
            data.append({
                "prompt": entry.user_message,
                "response": entry.ai_response,
                "score": score,
                "correction": entry.correction,
                "intent": entry.intent
            })
        
        return data
    
    def get_problem_areas(self) -> List[Dict]:
        """Выявляет проблемные области"""
        problems = {}
        
        for entry in self._feedback:
            if entry.feedback_type in [FeedbackType.THUMBS_DOWN, FeedbackType.CORRECTION]:
                intent = entry.intent or "unknown"
                
                if intent not in problems:
                    problems[intent] = {
                        "count": 0,
                        "examples": [],
                        "corrections": []
                    }
                
                problems[intent]["count"] += 1
                
                if len(problems[intent]["examples"]) < 3:
                    problems[intent]["examples"].append({
                        "user_message": entry.user_message[:100],
                        "ai_response": entry.ai_response[:200]
                    })
                
                if entry.correction and len(problems[intent]["corrections"]) < 3:
                    problems[intent]["corrections"].append(entry.correction)
        
        # Сортируем по количеству проблем
        sorted_problems = sorted(
            problems.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        return [
            {
                "intent": intent,
                **data
            }
            for intent, data in sorted_problems[:10]
        ]
    
    def get_recommendations(self) -> List[str]:
        """Генерирует рекомендации по улучшению"""
        recommendations = []
        
        stats = self.get_stats()
        
        if stats["satisfaction_rate"] < 0.7:
            recommendations.append(
                f"⚠️ Низкий уровень удовлетворённости ({stats['satisfaction_rate']:.0%}). "
                "Рекомендуется проанализировать проблемные области."
            )
        
        if stats["corrections_count"] > 10:
            recommendations.append(
                f"📝 Много исправлений ({stats['corrections_count']}). "
                "Рассмотрите добавление в базу знаний."
            )
        
        problems = self.get_problem_areas()
        if problems:
            top_problem = problems[0]
            recommendations.append(
                f"🎯 Проблемная область: '{top_problem['intent']}' "
                f"({top_problem['count']} негативных отзывов)."
            )
        
        if not recommendations:
            recommendations.append("✅ Качество ответов хорошее. Продолжайте в том же духе!")
        
        return recommendations
    
    def export_for_training(self, filepath: str = None) -> str:
        """Экспортирует данные для обучения модели"""
        if filepath is None:
            filepath = os.path.join(
                os.path.dirname(self.data_path),
                "training_data.json"
            )
        
        data = self.get_learning_data(limit=1000)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📤 Exported {len(data)} samples to {filepath}")
        return filepath


# Глобальный экземпляр
_feedback_system: Optional[FeedbackSystem] = None


def get_feedback_system() -> FeedbackSystem:
    """Возвращает глобальную систему обратной связи"""
    global _feedback_system
    if _feedback_system is None:
        _feedback_system = FeedbackSystem()
    return _feedback_system