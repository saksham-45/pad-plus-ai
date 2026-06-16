"""
🌙 Механизм сновидений — Dream System

Ночная обработка и консолидация памяти.
Имитирует процессы, происходящие в мозге во время сна.

Фазы:
1. REM-подобная фаза — обработка эмоциональных воспоминаний
2. Slow-wave фаза — консолидация в долговременную память
3. Интеграция — создание новых связей между концепциями
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging
import asyncio
import random

logger = logging.getLogger("PAD+.dreams")


@dataclass
class DreamContent:
    """Содержимое "сна" """
    phase: str                    # rem, slow_wave, integration
    topic: str                    # Тема обработки
    episodes_processed: int       # Обработано эпизодов
    insights: List[str]           # Инсайты
    emotions_processed: List[str] # Эмоции
    connections_made: int         # Создано связей
    duration_seconds: float       # Длительность
    timestamp: datetime


@dataclass
class DreamReport:
    """Отчёт о "сне" """
    total_duration: float
    phases_completed: int
    episodes_consolidated: int
    new_knowledge_items: int
    new_connections: int
    insights: List[str]
    recommendations: List[str]
    started_at: datetime
    finished_at: datetime


class DreamSystem:
    """
    🌙 Система сновидений
    
    Выполняется в "тихие" периоды или по расписанию.
    Обрабатывает память, создаёт связи, генерирует инсайты.
    """
    
    def __init__(self):
        from memory.consolidation import get_consolidator
        from memory.episodic import get_episodic_memory
        from memory.semantic import get_semantic_memory
        from memory.persona import get_persona
        from emotion.pad_model import get_pad_model
        from knowledge.graph import get_knowledge_graph
        
        self.consolidator = get_consolidator()
        self.episodic = get_episodic_memory()
        self.semantic = get_semantic_memory()
        self.persona = get_persona()
        self.emotions = get_pad_model()
        self.knowledge = get_knowledge_graph()
        
        # История снов
        self._dream_history: List[DreamReport] = []
        
        # Конфигурация
        self.config = {
            "min_idle_minutes": 30,      # Минимальное время простоя
            "dream_duration": 60,         # Длительность сна (секунды)
            "episodes_per_dream": 50,     # Эпизодов за сон
            "connection_threshold": 0.6,  # Порог для связей
            "emotion_decay_dream": 0.5    # Затухание эмоций во сне
        }
        
        # Флаг активности
        self._is_dreaming = False
        self._last_activity = datetime.now()
        
        logger.info("🌙 Система сновидений инициализирована")
    
    def record_activity(self):
        """Записывает активность (для определения простоя)"""
        self._last_activity = datetime.now()
    
    def should_dream(self) -> bool:
        """Проверяет, пора ли "спать" """
        if self._is_dreaming:
            return False
        
        idle_time = (datetime.now() - self._last_activity).total_seconds() / 60
        return idle_time >= self.config["min_idle_minutes"]
    
    async def dream(self) -> DreamReport:
        """
        Выполняет цикл "сна"
        
        Аналог фаз сна:
        1. REM — обработка эмоциональных воспоминаний
        2. Slow-wave — консолидация в долговременную память
        3. Integration — создание новых связей
        """
        if self._is_dreaming:
            logger.warning("Сон уже выполняется")
            return None
        
        self._is_dreaming = True
        started_at = datetime.now()
        
        logger.info("🌙 Начинается сон...")
        
        dream_contents: List[DreamContent] = []
        
        try:
            # Фаза 1: REM — эмоциональные воспоминания
            rem_content = await self._rem_phase()
            dream_contents.append(rem_content)
            await asyncio.sleep(1)  # Пауза между фазами
            
            # Фаза 2: Slow-wave — консолидация
            sw_content = await self._slow_wave_phase()
            dream_contents.append(sw_content)
            await asyncio.sleep(1)
            
            # Фаза 3: Интеграция
            int_content = await self._integration_phase()
            dream_contents.append(int_content)
            
        except Exception as e:
            logger.error(f"Ошибка во время сна: {e}")
        
        finished_at = datetime.now()
        
        # Формируем отчёт
        report = DreamReport(
            total_duration=(finished_at - started_at).total_seconds(),
            phases_completed=len(dream_contents),
            episodes_consolidated=sum(d.episodes_processed for d in dream_contents),
            new_knowledge_items=sum(len(d.insights) for d in dream_contents),
            new_connections=sum(d.connections_made for d in dream_contents),
            insights=[insight for d in dream_contents for insight in d.insights],
            recommendations=self._generate_recommendations(dream_contents),
            started_at=started_at,
            finished_at=finished_at
        )
        
        self._dream_history.append(report)
        self._is_dreaming = False
        
        logger.info(f"🌙 Сон завершён: {report.phases_completed} фаз, "
                   f"{report.episodes_consolidated} эпизодов")
        
        return report
    
    async def _rem_phase(self) -> DreamContent:
        """
        REM-подобная фаза
        
        Обрабатывает эмоционально заряженные воспоминания,
        снижает эмоциональное напряжение.
        """
        start_time = datetime.now()
        logger.info("  💭 REM-фаза: обработка эмоций...")
        
        # Получаем эмоционально заряженные эпизоды
        emotional_episodes = self.episodic.get_emotionally_charged(
            min_impact=0.2, limit=20
        )
        
        insights = []
        emotions_processed = []
        
        for episode in emotional_episodes:
            # Анализируем эмоциональный контекст
            if episode.emotion_impact > 0:
                # Позитивный опыт — укрепляем
                emotions_processed.append("positive")
                if episode.significance > 0.7:
                    insights.append(
                        f"Позитивный опыт в '{episode.topic}': "
                        f"{episode.user_message[:50]}..."
                    )
            else:
                # Негативный опыт — анализируем уроки
                emotions_processed.append("negative")
                if episode.significance > 0.5:
                    insights.append(
                        f"Урок из '{episode.topic}': нужно быть осторожнее"
                    )
        
        # Снижаем эмоциональное напряжение
        current_emotions = self.emotions.get_state()
        for key in current_emotions:
            # Затухание эмоций во сне
            decay = self.config["emotion_decay_dream"]
            if abs(current_emotions[key]) > 0.3:
                current_emotions[key] *= (1 - decay)
        
        self.emotions._save_state(current_emotions)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return DreamContent(
            phase="rem",
            topic="emotional_processing",
            episodes_processed=len(emotional_episodes),
            insights=insights[:5],
            emotions_processed=list(set(emotions_processed)),
            connections_made=0,
            duration_seconds=duration,
            timestamp=datetime.now()
        )
    
    async def _slow_wave_phase(self) -> DreamContent:
        """
        Slow-wave фаза
        
        Консолидация памяти — перенос важных знаний
        из кратковременной в долговременную память.
        """
        start_time = datetime.now()
        logger.info("  🌑 Slow-wave: консолидация памяти...")
        
        # Запускаем консолидацию
        consolidation_results = self.consolidator.consolidate_all()
        
        insights = []
        total_consolidated = 0
        connections = 0
        
        for key, result in consolidation_results.items():
            total_consolidated += result.items_consolidated
            insights.extend(result.insights[:2])
        
        # Очищаем дубликаты в памяти
        from memory.hygiene import get_hygiene
        try:
            hygiene = get_hygiene()
            cleanup = hygiene.analyze()
            if cleanup.get("duplicates", {}).get("found", 0) > 10:
                hygiene.cleanup()
                insights.append("Очистка памяти выполнена")
        except Exception:
            pass
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return DreamContent(
            phase="slow_wave",
            topic="memory_consolidation",
            episodes_processed=total_consolidated,
            insights=insights[:5],
            emotions_processed=[],
            connections_made=connections,
            duration_seconds=duration,
            timestamp=datetime.now()
        )
    
    async def _integration_phase(self) -> DreamContent:
        """
        Фаза интеграции
        
        Создаёт новые связи между концепциями,
        генерирует творческие инсайты.
        """
        start_time = datetime.now()
        logger.info("  🔗 Интеграция: создание связей...")
        
        insights = []
        connections_made = 0
        
        # Получаем все концепции
        concepts = self.semantic.search_knowledge(
            limit=50
        )
        
        # Находим похожие концепции для связывания
        for i, concept1 in enumerate(concepts):
            for concept2 in concepts[i+1:]:
                # Проверяем общие теги
                common_tags = set(concept1.tags) & set(concept2.tags)
                
                if common_tags and concept2.id not in concept1.related_concepts:
                    # Создаём связь в Knowledge Graph
                    try:
                        self.knowledge.add_relation(
                            concept1.id, concept2.id,
                            relation_type="related",
                            weight=len(common_tags) * 0.3
                        )
                        connections_made += 1
                    except Exception:
                        pass
                    
                    # Добавляем в related_concepts
                    concept1.related_concepts.append(concept2.id)
                    concept2.related_concepts.append(concept1.id)
                    self.semantic._save_knowledge(concept1)
                    self.semantic._save_knowledge(concept2)
        
        # Генерируем инсайты на основе связей
        if connections_made > 0:
            insights.append(f"Создано {connections_made} новых связей между концепциями")
        
        # Анализируем паттерны
        topics = {}
        for concept in concepts:
            domain = concept.domain
            topics[domain] = topics.get(domain, 0) + 1
        
        # Определяем доминантные темы
        dominant = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:3]
        if dominant:
            insights.append(
                f"Доминантные темы: {', '.join(t[0] for t in dominant)}"
            )
        
        # Обновляем персону на основе инсайтов
        if insights:
            try:
                self.persona.add_reflection(
                    insight="; ".join(insights[:2]),
                    action="Интеграция во время сна",
                    confidence=0.7
                )
            except Exception:
                pass
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return DreamContent(
            phase="integration",
            topic="knowledge_integration",
            episodes_processed=0,
            insights=insights[:5],
            emotions_processed=[],
            connections_made=connections_made,
            duration_seconds=duration,
            timestamp=datetime.now()
        )
    
    def _generate_recommendations(
        self, dream_contents: List[DreamContent]
    ) -> List[str]:
        """
        Генерирует рекомендации на основе сна
        """
        recommendations = []
        
        # Анализируем эмоциональный контент
        negative_count = sum(
            len([e for e in d.emotions_processed if e == "negative"])
            for d in dream_contents
        )
        
        if negative_count > 5:
            recommendations.append(
                "Много негативного опыта — рассмотреть изменения в подходах"
            )
        
        # Анализируем связи
        total_connections = sum(d.connections_made for d in dream_contents)
        if total_connections > 10:
            recommendations.append(
                "Хорошая связность знаний — можно углубить изучение"
            )
        
        # Анализируем инсайты
        total_insights = sum(len(d.insights) for d in dream_contents)
        if total_insights > 5:
            recommendations.append(
                "Много новых инсайтов — рекомендуется рефлексия"
            )
        
        return recommendations
    
    def get_dream_stats(self) -> Dict[str, Any]:
        """Статистика снов"""
        if not self._dream_history:
            return {
                "total_dreams": 0,
                "is_dreaming": self._is_dreaming
            }
        
        total_episodes = sum(d.episodes_consolidated for d in self._dream_history)
        total_connections = sum(d.new_connections for d in self._dream_history)
        avg_duration = sum(d.total_duration for d in self._dream_history) / len(self._dream_history)
        
        return {
            "total_dreams": len(self._dream_history),
            "is_dreaming": self._is_dreaming,
            "total_episodes_consolidated": total_episodes,
            "total_connections_made": total_connections,
            "average_duration_seconds": round(avg_duration, 2),
            "last_dream": self._dream_history[-1].finished_at.isoformat(),
            "recent_insights": [
                insight for d in self._dream_history[-3:]
                for insight in d.insights
            ][:10]
        }
    
    def get_last_dream_report(self) -> Optional[Dict[str, Any]]:
        """Получает отчёт о последнем сне"""
        if not self._dream_history:
            return None
        
        last = self._dream_history[-1]
        return {
            "started_at": last.started_at.isoformat(),
            "finished_at": last.finished_at.isoformat(),
            "duration_seconds": round(last.total_duration, 2),
            "phases_completed": last.phases_completed,
            "episodes_consolidated": last.episodes_consolidated,
            "new_knowledge_items": last.new_knowledge_items,
            "new_connections": last.new_connections,
            "insights": last.insights,
            "recommendations": last.recommendations
        }


# Глобальный экземпляр
_dream_system: Optional[DreamSystem] = None


def get_dream_system() -> DreamSystem:
    """Возвращает глобальную систему снов"""
    global _dream_system
    if _dream_system is None:
        _dream_system = DreamSystem()
    return _dream_system