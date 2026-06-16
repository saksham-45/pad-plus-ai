"""
🔄 Консолидация памяти — Memory Consolidation

Механизм переноса знаний между слоями памяти:
- Episodic → Semantic (извлечение общих знаний из эпизодов)
- Semantic → Roots (стабилизация важных знаний)
- RAG → Semantic (извлечение фактов)
- Semantic → Knowledge Graph (связи между концепциями)

Основан на принципах нейронауки:
- Повторное воспроизведение укрепляет память
- Эмоционально заряженные воспоминания консолидируются быстрее
- Сон способствует консолидации
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging
import json
import os

from .episodic import get_episodic_memory, Episode
from .semantic import get_semantic_memory, SemanticMemory, KnowledgeType
from .roots import get_roots_memory
from .rag import get_rag as get_rag_memory

logger = logging.getLogger("PAD+.consolidation")


@dataclass
class ConsolidationResult:
    """Результат консолидации"""
    source_type: str
    target_type: str
    items_processed: int
    items_consolidated: int
    insights: List[str]
    duration_seconds: float
    timestamp: datetime


class MemoryConsolidator:
    """
    🔄 Консолидатор памяти
    
    Переносит знания между слоями памяти на основе:
    - Частоты использования
    - Эмоциональной значимости
    - Связности с другими знаниями
    - Времени с момента создания
    """
    
    def __init__(self):
        self.episodic = get_episodic_memory()
        self.semantic = get_semantic_memory()
        self.roots = get_roots_memory()
        self.rag = get_rag_memory()
        
        # Параметры консолидации
        self.config = {
            # Пороги для консолидации эпизодов
            "min_access_count": 3,           # Минимум использований
            "min_significance": 0.6,         # Минимальная значимость
            "min_age_hours": 1,              # Минимальный возраст
            
            # Эмоциональные пороги
            "emotion_boost_threshold": 0.3,  # Ускорение для эмоциональных
            
            # Пороги для Roots
            "roots_confidence": 0.9,         # Уверенность для Roots
            "roots_access_count": 10,        # Использований для Roots
            
            # Лимиты
            "max_consolidation_batch": 50,
            "similarity_threshold": 0.85
        }
        
        # История консолидаций
        self._history: List[ConsolidationResult] = []
        
        logger.info("✅ Консолидатор памяти инициализирован")
    
    def consolidate_all(self, user_id: Optional[str] = None) -> Dict[str, ConsolidationResult]:
        """
        Полная консолидация всех типов памяти
        
        Args:
            user_id: ID пользователя для персональной консолидации (None для общей)
        """
        results = {}

        # 1. Эпизодическая → Семантическая
        results["episodic_to_semantic"] = self.consolidate_episodes_to_semantic(user_id=user_id)

        # 2. RAG → Семантическая
        results["rag_to_semantic"] = self.consolidate_rag_to_semantic(user_id=user_id)

        # 3. Семантическая → Roots
        results["semantic_to_roots"] = self.consolidate_semantic_to_roots(user_id=user_id)

        # 4. Обновление связей
        results["update_connections"] = self.update_knowledge_connections(user_id=user_id)

        return results
    
    def consolidate_episodes_to_semantic(self, user_id: Optional[str] = None) -> ConsolidationResult:
        """
        Консолидация эпизодов в семантическую память
        
        Извлекает общие знания из повторяющихся эпизодов
        
        Args:
            user_id: ID пользователя для персональной консолидации
        """
        start_time = datetime.now()
        insights = []
        items_processed = 0
        items_consolidated = 0

        # Получаем кандидатов для консолидации
        candidates = self._get_episode_candidates(user_id=user_id)
        items_processed = len(candidates)
        
        # Группируем по теме
        by_topic: Dict[str, List[Episode]] = {}
        for episode in candidates:
            topic = episode.topic
            if topic not in by_topic:
                by_topic[topic] = []
            by_topic[topic].append(episode)
        
        # Извлекаем общие знания из каждой группы
        for topic, episodes in by_topic.items():
            if len(episodes) >= 2:  # Нужно минимум 2 эпизода
                # Извлекаем общие концепции
                common_concepts = self._extract_common_concepts(episodes)
                
                for concept in common_concepts:
                    # Проверяем, нет ли уже такого знания
                    existing = self.semantic.search_knowledge(
                        query=concept,
                        knowledge_type=KnowledgeType.CONCEPTUAL,
                        limit=1
                    )
                    
                    if not existing:
                        # Создаём новое концептуальное знание
                        self.semantic.add_concept(
                            name=concept,
                            definition=f"Концепция, выявленная из {len(episodes)} диалогов на тему '{topic}'",
                            domain=topic,
                            examples=[ep.user_message[:100] for ep in episodes[:3]]
                        )
                        items_consolidated += 1
                        insights.append(f"Новая концепция: {concept} (из {len(episodes)} эпизодов)")
        
        # Извлекаем процедурные знания из успешных паттернов
        procedures = self._extract_procedures(candidates)
        for proc in procedures:
            self.semantic.learn_procedure(
                name=proc["name"],
                steps=proc["steps"],
                triggers=proc["triggers"],
                domain=proc.get("domain", "general")
            )
            items_consolidated += 1
            insights.append(f"Новая процедура: {proc['name']}")
        
        result = ConsolidationResult(
            source_type="episodic",
            target_type="semantic",
            items_processed=items_processed,
            items_consolidated=items_consolidated,
            insights=insights,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now()
        )
        
        self._history.append(result)
        logger.info(f"🔄 Консолидация Episodic→Semantic: {items_consolidated}/{items_processed}")
        
        return result
    
    def consolidate_rag_to_semantic(self) -> ConsolidationResult:
        """
        Консолидация RAG памяти в семантическую
        
        Извлекает факты и концепции из диалогов
        """
        start_time = datetime.now()
        insights = []
        items_processed = 0
        items_consolidated = 0
        
        # Получаем недавние диалоги
        try:
            recent = self.rag.get_recent(days=7, limit=self.config["max_consolidation_batch"])
            items_processed = len(recent)
        except Exception as e:
            logger.warning(f"Не удалось получить RAG записи: {e}")
            recent = []
        
        for dialog in recent:
            # Извлекаем факты
            entities = dialog.get("entities", [])
            for entity in entities:
                entity_type = entity.get("type", "unknown")
                entity_name = entity.get("name", "")
                
                if entity_name and entity_type:
                    # Создаём декларативное знание
                    existing = self.semantic.search_knowledge(
                        query=entity_name,
                        knowledge_type=KnowledgeType.DECLARATIVE,
                        limit=1
                    )
                    
                    if not existing:
                        self.semantic.add_knowledge(
                            content=f"{entity_name} ({entity_type})",
                            knowledge_type=KnowledgeType.DECLARATIVE,
                            tags=[entity_type, entity_name],
                            source="rag_extraction"
                        )
                        items_consolidated += 1
        
        # Извлекаем часто встречающиеся темы как концепции
        try:
            topic_stats = self.rag.get_topic_stats()
            for topic, count in topic_stats.items():
                if count >= 3:  # Минимум 3 диалога на тему
                    existing = self.semantic.search_knowledge(
                        query=topic,
                        knowledge_type=KnowledgeType.CONCEPTUAL,
                        limit=1
                    )
                    
                    if not existing:
                        self.semantic.add_concept(
                            name=topic,
                            definition=f"Тема, обсуждаемая в {count} диалогах",
                            domain=topic
                        )
                        items_consolidated += 1
                        insights.append(f"Тема как концепция: {topic}")
        except Exception as e:
            logger.warning(f"Не удалось получить статистику тем: {e}")
        
        result = ConsolidationResult(
            source_type="rag",
            target_type="semantic",
            items_processed=items_processed,
            items_consolidated=items_consolidated,
            insights=insights,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now()
        )
        
        self._history.append(result)
        logger.info(f"🔄 Консолидация RAG→Semantic: {items_consolidated}/{items_processed}")
        
        return result
    
    def consolidate_semantic_to_roots(self) -> ConsolidationResult:
        """
        Консолидация семантической памяти в Roots
        
        Переносит стабильные, высокоуверенные знания в корневую память
        """
        start_time = datetime.now()
        insights = []
        items_processed = 0
        items_consolidated = 0
        
        # Получаем знания с высокой уверенностью
        high_confidence = self.semantic.search_knowledge(
            min_confidence=self.config["roots_confidence"],
            limit=self.config["max_consolidation_batch"]
        )
        
        items_processed = len(high_confidence)
        
        for knowledge in high_confidence:
            # Проверяем частоту использования
            if knowledge.access_count >= self.config["roots_access_count"]:
                # Проверяем, нет ли уже в Roots
                existing = self.roots.search(knowledge.content)
                
                if not existing:
                    # Определяем категорию
                    category = self._determine_roots_category(knowledge)
                    
                    # Добавляем в Roots
                    self.roots.add_root(
                        category=category,
                        content=knowledge.content,
                        confidence=knowledge.confidence
                    )
                    items_consolidated += 1
                    insights.append(f"Знание стабилизировано: {knowledge.content[:50]}...")
        
        result = ConsolidationResult(
            source_type="semantic",
            target_type="roots",
            items_processed=items_processed,
            items_consolidated=items_consolidated,
            insights=insights,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now()
        )
        
        self._history.append(result)
        logger.info(f"🔄 Консолидация Semantic→Roots: {items_consolidated}/{items_processed}")
        
        return result
    
    def update_knowledge_connections(self) -> ConsolidationResult:
        """
        Обновляет связи между знаниями
        """
        start_time = datetime.now()
        insights = []
        items_processed = 0
        items_consolidated = 0
        
        # Получаем все концептуальные знания
        concepts = self.semantic.search_knowledge(
            knowledge_type=KnowledgeType.CONCEPTUAL,
            limit=100
        )
        
        items_processed = len(concepts)
        
        # Находим связанные концепции
        for i, concept1 in enumerate(concepts):
            for concept2 in concepts[i+1:]:
                # Проверяем общие теги
                common_tags = set(concept1.tags) & set(concept2.tags)
                
                if common_tags:
                    # Добавляем связь
                    if concept2.id not in concept1.related_concepts:
                        concept1.related_concepts.append(concept2.id)
                        items_consolidated += 1
                    
                    if concept1.id not in concept2.related_concepts:
                        concept2.related_concepts.append(concept1.id)
                    
                    self.semantic._save_knowledge(concept1)
                    self.semantic._save_knowledge(concept2)
        
        if items_consolidated > 0:
            insights.append(f"Создано {items_consolidated} связей между концепциями")
        
        result = ConsolidationResult(
            source_type="semantic",
            target_type="semantic_connections",
            items_processed=items_processed,
            items_consolidated=items_consolidated,
            insights=insights,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now()
        )
        
        self._history.append(result)
        logger.info(f"🔄 Обновление связей: {items_consolidated}/{items_processed}")
        
        return result
    
    def _get_episode_candidates(self, user_id: Optional[str] = None) -> List[Episode]:
        """
        Получает эпизоды-кандидаты для консолидации
        
        Args:
            user_id: ID пользователя для персональной консолидации
        """
        # Значимые эпизоды
        significant = self.episodic.get_significant_episodes(
            min_significance=self.config["min_significance"],
            limit=self.config["max_consolidation_batch"]
        )

        # Часто используемые (через поиск)
        # === ФАЗА 5: Персонализация — фильтр по user_id ===
        all_episodes = self.episodic.search_episodes(limit=100, user_id=user_id)

        # Фильтруем по критериям
        candidates = []
        cutoff_time = datetime.now() - timedelta(hours=self.config["min_age_hours"])

        seen_ids = set()
        for ep in significant + all_episodes:
            if ep.id in seen_ids:
                continue
            seen_ids.add(ep.id)

            # Проверяем возраст
            if ep.timestamp < cutoff_time:
                # Проверяем частоту использования ИЛИ эмоциональную значимость
                if (ep.access_count >= self.config["min_access_count"] or
                    abs(ep.emotion_impact) >= self.config["emotion_boost_threshold"]):
                    candidates.append(ep)

        return candidates
    
    def _extract_common_concepts(self, episodes: List[Episode]) -> List[str]:
        """
        Извлекает общие концепции из группы эпизодов
        """
        # Собираем все концепции
        all_concepts = []
        for ep in episodes:
            all_concepts.extend(ep.concepts)
        
        # Считаем частоту
        concept_counts: Dict[str, int] = {}
        for concept in all_concepts:
            concept_counts[concept] = concept_counts.get(concept, 0) + 1
        
        # Возвращаем концепции, встречающиеся минимум в половине эпизодов
        threshold = len(episodes) / 2
        return [
            concept for concept, count in concept_counts.items()
            if count >= threshold
        ]
    
    def _extract_procedures(self, episodes: List[Episode]) -> List[Dict]:
        """
        Извлекает процедурные знания из успешных паттернов
        """
        procedures = []
        
        # Группируем успешные эпизоды по намерению
        by_intent: Dict[str, List[Episode]] = {}
        for ep in episodes:
            if ep.success:
                intent = ep.intent
                if intent not in by_intent:
                    by_intent[intent] = []
                by_intent[intent].append(ep)
        
        # Для каждого намерения извлекаем паттерн
        for intent, eps in by_intent.items():
            if len(eps) >= 2:
                # Извлекаем триггеры
                triggers = list(set(
                    keyword for ep in eps 
                    for keyword in ep.keywords[:3]
                ))[:5]
                
                # Создаём процедуру
                procedures.append({
                    "name": f"Обработка {intent}",
                    "steps": [
                        f"1. Определить контекст: {intent}",
                        "2. Извлечь релевантную информацию",
                        "3. Сформировать ответ",
                        "4. Проверить качество"
                    ],
                    "triggers": triggers,
                    "domain": eps[0].topic if eps else "general"
                })
        
        return procedures
    
    def _determine_roots_category(self, knowledge) -> str:
        """
        Определяет категорию для Roots
        """
        content_lower = knowledge.content.lower()
        tags_lower = [t.lower() for t in knowledge.tags]
        
        # Философские
        if any(word in content_lower for word in ["смысл", "цель", "ценность", "философ"]):
            return "philosophy"
        
        # Этические
        if any(word in content_lower for word in ["должен", "нельзя", "правильно", "этич"]):
            return "ethics"
        
        # Идентичность
        if any(word in content_lower for word in ["я ", "мой ", "мне ", "себя"]):
            return "identity"
        
        # По тегам
        if "philosophy" in tags_lower:
            return "philosophy"
        if "ethics" in tags_lower:
            return "ethics"
        
        return "knowledge"
    
    def get_consolidation_stats(self) -> Dict[str, Any]:
        """
        Статистика консолидации
        """
        if not self._history:
            return {
                "total_consolidations": 0,
                "history": []
            }
        
        total_processed = sum(r.items_processed for r in self._history)
        total_consolidated = sum(r.items_consolidated for r in self._history)
        
        by_type: Dict[str, int] = {}
        for result in self._history:
            key = f"{result.source_type}→{result.target_type}"
            by_type[key] = by_type.get(key, 0) + result.items_consolidated
        
        return {
            "total_consolidations": len(self._history),
            "total_items_processed": total_processed,
            "total_items_consolidated": total_consolidated,
            "success_rate": total_consolidated / total_processed if total_processed > 0 else 0,
            "by_type": by_type,
            "last_consolidation": self._history[-1].timestamp.isoformat() if self._history else None,
            "recent_insights": [
                insight for r in self._history[-5:] 
                for insight in r.insights
            ][:10]
        }
    
    def run_scheduled_consolidation(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Запускает плановую консолидацию (например, раз в час)
        
        Args:
            user_id: ID пользователя для персональной консолидации (None для общей)
        """
        if user_id:
            logger.info(f"🌙 Запуск плановой консолидации для пользователя {user_id[:8]}...")
        else:
            logger.info("🌙 Запуск плановой консолидации...")

        results = self.consolidate_all(user_id=user_id)

        summary = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "results": {
                key: {
                    "processed": r.items_processed,
                    "consolidated": r.items_consolidated,
                    "insights": r.insights
                }
                for key, r in results.items()
            }
        }

        logger.info(f"✅ Плановая консолидация завершена")

        return summary


# Глобальный экземпляр
_consolidator: Optional[MemoryConsolidator] = None


def get_consolidator() -> MemoryConsolidator:
    """Возвращает глобальный консолидатор"""
    global _consolidator
    if _consolidator is None:
        _consolidator = MemoryConsolidator()
    return _consolidator