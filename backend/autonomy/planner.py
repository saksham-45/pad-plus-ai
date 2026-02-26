"""
Автономия NeuroMind AI v2.0

Улучшенная система:
- Автозапуск рефлексии каждые N диалогов
- Самооценка качества ответов
- Автоматическое пополнение графа знаний
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable
import json
import os
import sqlite3
import threading
import time
import random
import logging

logger = logging.getLogger("neuromind.autonomy")


@dataclass
class AutonomousTask:
    """Автономная задача"""
    id: str
    task_type: str  # question, reflection, cleanup, knowledge_update
    question: str
    status: str = "pending"
    scheduled_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    result: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.task_type,
            "question": self.question,
            "status": self.status,
            "scheduled_at": self.scheduled_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "result": self.result,
            "metadata": self.metadata
        }


@dataclass
class QualityScore:
    """Оценка качества ответа"""
    message_id: str
    score: float  # 0.0 - 1.0
    factors: Dict[str, float]  # факторы оценки
    timestamp: datetime = field(default_factory=datetime.now)
    notes: str = ""
    
    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "score": self.score,
            "factors": self.factors,
            "timestamp": self.timestamp.isoformat(),
            "notes": self.notes
        }


class QualityAssessor:
    """
    🎯 Самооценка качества ответов
    
    Оценивает ответы по факторам:
    - Длина и информативность
    - Использование RAG контекста
    - Уверенность (confidence)
    - Эмоциональная адекватность
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "quality.db"
            )
        self.db_path = db_path
        self._ensure_tables()
    
    def _ensure_tables(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL,
                score REAL NOT NULL,
                factors TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                notes TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def assess_response(
        self,
        message_id: str,
        response_text: str,
        confidence: float = 0.5,
        rag_used: bool = False,
        emotion_state: dict = None,
        provider: str = "unknown"
    ) -> QualityScore:
        """
        Оценивает качество ответа
        
        Факторы:
        - length_score: оптимальная длина (не слишком короткий/длинный)
        - confidence_score: уверенность модели
        - rag_score: использование контекста
        - emotion_score: эмоциональное состояние
        """
        factors = {}
        
        # 1. Оценка длины (оптимум 50-500 символов)
        length = len(response_text)
        if length < 20:
            factors["length"] = 0.3
        elif length < 50:
            factors["length"] = 0.6
        elif length <= 500:
            factors["length"] = 1.0
        elif length <= 1000:
            factors["length"] = 0.8
        else:
            factors["length"] = 0.6
        
        # 2. Confidence
        factors["confidence"] = min(confidence, 1.0)
        
        # 3. RAG использование (бонус)
        factors["rag"] = 1.0 if rag_used else 0.7
        
        # 4. Эмоциональное состояние
        if emotion_state:
            # Высокая уверенность = хорошо
            emotion_conf = emotion_state.get("уверенность", 0.5)
            factors["emotion"] = emotion_conf
        else:
            factors["emotion"] = 0.5
        
        # 5. Provider бонус (gigachat > fallback)
        factors["provider"] = 1.0 if provider == "gigachat" else 0.7
        
        # Итоговый score (взвешенное среднее)
        weights = {
            "length": 0.15,
            "confidence": 0.30,
            "rag": 0.20,
            "emotion": 0.15,
            "provider": 0.20
        }
        
        total_score = sum(
            factors[k] * weights[k] 
            for k in factors
        )
        
        # Формируем заметки
        notes = []
        if factors["length"] < 0.5:
            notes.append("короткий ответ")
        if factors["confidence"] < 0.5:
            notes.append("низкая уверенность")
        if rag_used:
            notes.append("использован RAG")
        if factors["emotion"] < 0.4:
            notes.append("неуверенное состояние")
        
        score = QualityScore(
            message_id=message_id,
            score=round(total_score, 3),
            factors={k: round(v, 3) for k, v in factors.items()},
            notes=", ".join(notes) if notes else "норма"
        )
        
        # Сохраняем
        self._save_score(score)
        
        logger.info(f"🎯 Оценка качества: {score.score:.2f} ({score.notes})")
        
        return score
    
    def _save_score(self, score: QualityScore):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO quality_scores (message_id, score, factors, timestamp, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            score.message_id,
            score.score,
            json.dumps(score.factors),
            score.timestamp.isoformat(),
            score.notes
        ))
        
        conn.commit()
        conn.close()
    
    def get_average_score(self, hours: int = 24) -> float:
        """Среднее качество за период"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute("""
            SELECT AVG(score) FROM quality_scores
            WHERE timestamp >= ?
        """, (cutoff,))
        
        result = cursor.fetchone()[0]
        conn.close()
        
        return result or 0.0
    
    def get_stats(self, hours: int = 24) -> dict:
        """Статистика качества"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute("""
            SELECT COUNT(*), AVG(score), MIN(score), MAX(score)
            FROM quality_scores WHERE timestamp >= ?
        """, (cutoff,))
        
        row = cursor.fetchone()
        
        cursor.execute("""
            SELECT COUNT(*) FROM quality_scores
            WHERE timestamp >= ? AND score < 0.5
        """, (cutoff,))
        
        low_quality = row[0]
        
        conn.close()
        
        return {
            "total_assessed": row[0] or 0,
            "average_score": round(row[1] or 0, 3),
            "min_score": round(row[2] or 0, 3),
            "max_score": round(row[3] or 0, 3),
            "low_quality_count": low_quality,
            "period_hours": hours
        }


class KnowledgeAutoUpdater:
    """
    🕸️ Автоматическое пополнение графа знаний
    
    Извлекает сущности и связи из диалогов:
    - Ключевые понятия
    - Отношения между ними
    - Контекст использования
    """
    
    def __init__(self):
        self.pending_extractions: List[dict] = []
        self.extraction_count = 0
    
    def extract_from_dialog(
        self,
        user_message: str,
        ai_response: str,
        min_length: int = 20
    ) -> List[dict]:
        """
        Извлекает потенциальные концепции из диалога
        """
        extracted = []
        
        # Простые эвристики для извлечения
        combined = f"{user_message} {ai_response}"
        
        # 1. Извлечение важных фраз (в кавычках или с заглавной буквы)
        import re
        
        # Фразы в кавычках
        quoted = re.findall(r'["«]([^"»]+)["»]', combined)
        for phrase in quoted:
            if len(phrase) >= min_length:
                extracted.append({
                    "name": phrase.strip(),
                    "type": "concept",
                    "source": "quoted",
                    "confidence": 0.7
                })
        
        # 2. Вопросительные слова указывают на темы
        question_topics = re.findall(
            r'(?:что|как|почему|зачем|когда|где|кто|какой)\s+(\w+)',
            user_message.lower()
        )
        for topic in question_topics:
            if len(topic) > 3:
                extracted.append({
                    "name": topic,
                    "type": "topic",
                    "source": "question",
                    "confidence": 0.5
                })
        
        # 3. Технические термины (camelCase, snake_case, CAPS)
        tech_terms = re.findall(r'\b([A-Z][a-z]+[A-Z]\w*|\w+_\w+|[A-Z]{2,})\b', combined)
        for term in tech_terms:
            extracted.append({
                "name": term,
                "type": "technical",
                "source": "pattern",
                "confidence": 0.8
            })
        
        self.extraction_count += len(extracted)
        
        return extracted
    
    def add_to_knowledge_graph(self, concepts: List[dict]) -> int:
        """Добавляет концепции в граф знаний"""
        if not concepts:
            return 0
        
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from knowledge.graph import get_knowledge_graph
            
            graph = get_knowledge_graph()
            added = 0
            
            for concept in concepts:
                try:
                    graph.add_concept(
                        name=concept["name"],
                        concept_type=concept.get("type", "concept"),
                        confidence=concept.get("confidence", 0.5),
                        metadata={"source": concept.get("source", "auto")}
                    )
                    added += 1
                except Exception as e:
                    logger.debug(f"Не удалось добавить концепцию: {e}")
            
            logger.info(f"🕸️ Добавлено {added} концепций в граф знаний")
            return added
            
        except Exception as e:
            logger.error(f"Ошибка добавления в граф: {e}")
            return 0


class Planner:
    """
    Планировщик вопросов с улучшенной автономностью
    """
    
    BASE_QUESTIONS = [
        "Что я не понимаю?",
        "Как это связано с тем, что я уже знаю?",
        "Почему это так?",
        "Что если это неправильно?",
        "Как мне это проверить?",
        "Чему я могу научиться из этого?",
        "Какие допущения я делаю?",
        "Что я упускаю из виду?",
        "Как это можно применить?",
        "Какие есть альтернативы?"
    ]
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "autonomy.db"
            )
        self.db_path = db_path
        self._ensure_tables()
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._interval = 3600
        
        # Счётчик диалогов для авто-рефлексии
        self._dialog_count = 0
        self._reflection_interval = 10  # Каждые N диалогов
        
        # Подсистемы
        self.quality_assessor = QualityAssessor()
        self.knowledge_updater = KnowledgeAutoUpdater()
    
    def _ensure_tables(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                question TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                scheduled_at TEXT NOT NULL,
                executed_at TEXT,
                result TEXT,
                metadata TEXT DEFAULT '{}'
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dialog_counter (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                count INTEGER DEFAULT 0,
                last_reflection TEXT
            )
        """)
        
        cursor.execute("""
            INSERT OR IGNORE INTO dialog_counter (id, count) VALUES (1, 0)
        """)
        
        conn.commit()
        conn.close()
    
    def increment_dialog_count(self) -> bool:
        """
        Увеличивает счётчик диалогов.
        Возвращает True если нужна рефлексия.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE dialog_counter SET count = count + 1 WHERE id = 1")
        cursor.execute("SELECT count FROM dialog_counter WHERE id = 1")
        
        count = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        self._dialog_count = count
        
        # Проверяем нужна ли рефлексия
        needs_reflection = count > 0 and count % self._reflection_interval == 0
        
        if needs_reflection:
            logger.info(f"🔄 Диалог #{count} — нужна авто-рефлексия!")
        
        return needs_reflection
    
    def auto_reflect(self) -> dict:
        """
        Автоматическая рефлексия после N диалогов
        """
        logger.info("🔄 Запуск авто-рефлексии...")
        
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from memory.rag import get_rag
            from knowledge.graph import get_knowledge_graph
            
            rag = get_rag()
            graph = get_knowledge_graph()
            
            findings = {
                "triggered_at": datetime.now().isoformat(),
                "dialog_count": self._dialog_count,
                "rag_stats": rag.get_stats(),
                "knowledge_stats": {
                    "nodes": len(graph.nodes),
                    "edges": len(graph.edges)
                },
                "quality_stats": self.quality_assessor.get_stats(),
                "recommendations": []
            }
            
            # Рекомендации на основе анализа
            avg_quality = findings["quality_stats"].get("average_score", 0)
            if avg_quality < 0.5:
                findings["recommendations"].append(
                    "Низкое качество ответов — проверить провайдера"
                )
            
            rag_count = findings["rag_stats"].get("total_dialogs", 0)
            if rag_count < 5:
                findings["recommendations"].append(
                    "Мало диалогов в памяти — нужно больше взаимодействия"
                )
            
            # Обновляем время последней рефлексии
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE dialog_counter SET last_reflection = ? WHERE id = 1",
                (datetime.now().isoformat(),)
            )
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Рефлексия завершена: {len(findings['recommendations'])} рекомендаций")
            
            return findings
            
        except Exception as e:
            logger.error(f"Ошибка рефлексии: {e}")
            return {"error": str(e)}
    
    def generate_question(self, context: str = None) -> str:
        question = random.choice(self.BASE_QUESTIONS)
        if context:
            question = f"{question} (контекст: {context})"
        return question
    
    def schedule_task(self, task_type: str = "question", 
                      question: str = None,
                      delay_seconds: int = None) -> AutonomousTask:
        import uuid
        
        if question is None:
            question = self.generate_question()
        
        if delay_seconds is None:
            delay_seconds = self._interval
        
        task = AutonomousTask(
            id=str(uuid.uuid4())[:8],
            task_type=task_type,
            question=question,
            scheduled_at=datetime.now() + timedelta(seconds=delay_seconds)
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO tasks (id, type, question, status, scheduled_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            task.id, task.task_type, task.question,
            task.status, task.scheduled_at.isoformat(),
            json.dumps(task.metadata)
        ))
        
        conn.commit()
        conn.close()
        
        return task
    
    def get_pending_tasks(self) -> List[AutonomousTask]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM tasks 
            WHERE status = 'pending' AND scheduled_at <= ?
            ORDER BY scheduled_at ASC
        """, (datetime.now().isoformat(),))
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append(AutonomousTask(
                id=row['id'],
                task_type=row['type'],
                question=row['question'],
                status=row['status'],
                scheduled_at=datetime.fromisoformat(row['scheduled_at']),
                executed_at=datetime.fromisoformat(row['executed_at']) if row['executed_at'] else None,
                result=row['result'],
                metadata=json.loads(row['metadata'])
            ))
        
        conn.close()
        return tasks
    
    def complete_task(self, task_id: str, result: str = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tasks 
            SET status = 'completed', executed_at = ?, result = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), result, task_id))
        
        conn.commit()
        conn.close()
    
    def start(self, callback: Callable[[AutonomousTask], None] = None):
        if self._running:
            return
        
        self._running = True
        
        def run():
            while self._running:
                tasks = self.get_pending_tasks()
                
                for task in tasks:
                    if not self._running:
                        break
                    
                    if callback:
                        callback(task)
                    
                    self.complete_task(task.id, "processed")
                
                if len(tasks) == 0:
                    self.schedule_task()
                
                time.sleep(60)
        
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
    
    def stop(self):
        self._running = False
    
    def get_status(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
        pending = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
        completed = cursor.fetchone()[0]
        
        cursor.execute("SELECT count, last_reflection FROM dialog_counter WHERE id = 1")
        row = cursor.fetchone()
        dialog_count = row[0] if row else 0
        last_reflection = row[1] if row else None
        
        conn.close()
        
        return {
            "running": self._running,
            "pending_tasks": pending,
            "completed_tasks": completed,
            "interval_seconds": self._interval,
            "dialog_count": dialog_count,
            "reflection_interval": self._reflection_interval,
            "last_auto_reflection": last_reflection,
            "quality_stats": self.quality_assessor.get_stats(hours=24),
            "knowledge_extractions": self.knowledge_updater.extraction_count
        }


class SelfReflection:
    """Саморефлексия"""
    
    def __init__(self):
        self.last_reflection: Optional[datetime] = None
        self.findings: List[dict] = []
    
    def reflect_on_memory(self, memory_records: List[Any]) -> dict:
        findings = {
            "low_confidence": [],
            "contradictions": [],
            "old_records": [],
            "timestamp": datetime.now().isoformat()
        }
        
        for record in memory_records:
            if hasattr(record, 'confidence') and record.confidence < 0.5:
                findings["low_confidence"].append({
                    "id": record.id,
                    "text": record.text[:100],
                    "confidence": record.confidence
                })
        
        self.findings.append(findings)
        self.last_reflection = datetime.now()
        
        return findings
    
    def get_status(self) -> dict:
        return {
            "last_reflection": self.last_reflection.isoformat() if self.last_reflection else None,
            "total_findings": len(self.findings)
        }


# Глобальные экземпляры
_planner: Optional[Planner] = None
_self_reflection: Optional[SelfReflection] = None


def get_planner() -> Planner:
    global _planner
    if _planner is None:
        _planner = Planner()
    return _planner


def get_self_reflection() -> SelfReflection:
    global _self_reflection
    if _self_reflection is None:
        _self_reflection = SelfReflection()
    return _self_reflection