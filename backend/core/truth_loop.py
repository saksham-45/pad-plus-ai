"""
🔁 TruthLoop — Контур истины PAD+ AI

Верификация утверждений и проверка достоверности.

Модель Claim:
- text: текст утверждения
- triple: (subject, predicate, object) если возможно
- confidence: 0..1
- status: hypothesis | supported | contradicted | unknown
- sources: откуда информация
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime
import re
import json
import os
import sqlite3
import logging

logger = logging.getLogger("PAD+.truth")


class ClaimStatus(Enum):
    """Статус утверждения"""
    HYPOTHESIS = "hypothesis"       # Предположение
    SUPPORTED = "supported"         # Подтверждено
    CONTRADICTED = "contradicted"   # Опровергнуто
    UNKNOWN = "unknown"             # Неизвестно


class ClaimSource(Enum):
    """Источник утверждения"""
    MODEL = "model"           # От LLM
    USER = "user"             # От пользователя
    MEMORY = "memory"         # Из памяти
    GRAPH = "graph"           # Из графа знаний
    EXTERNAL = "external"     # Внешний источник


@dataclass
class Claim:
    """
    Утверждение — атомарная единица знания
    
    Каждый ответ дробится на утверждения,
    которые можно проверить и оценить.
    """
    id: str
    text: str
    subject: str = ""
    predicate: str = ""
    object: str = ""
    confidence: float = 0.5
    status: ClaimStatus = ClaimStatus.HYPOTHESIS
    sources: List[str] = field(default_factory=list)
    evidence_for: List[str] = field(default_factory=list)
    evidence_against: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "triple": {
                "subject": self.subject,
                "predicate": self.predicate,
                "object": self.object
            },
            "confidence": round(self.confidence, 3),
            "status": self.status.value,
            "sources": self.sources,
            "evidence_for": self.evidence_for,
            "evidence_against": self.evidence_against,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def get_triple_str(self) -> str:
        """Возвращает triple как строку"""
        if self.subject and self.predicate and self.object:
            return f"({self.subject}, {self.predicate}, {self.object})"
        return ""


class ClaimExtractor:
    """
    Извлекает утверждения из текста
    """
    
    # Паттерны для извлечения triples
    TRIPLE_PATTERNS = [
        # "X это Y"
        (r'(\w+)\s+(?:это|является|представляет собой)\s+(\w+)', "is_a"),
        # "X имеет Y"
        (r'(\w+)\s+(?:имеет|обладает|содержит)\s+(\w+)', "has"),
        # "X делает Y"
        (r'(\w+)\s+(?:делает|выполняет|производит)\s+(\w+)', "does"),
        # "X связан с Y"
        (r'(\w+)\s+(?:связан|связано|связаны)\s+с\s+(\w+)', "related_to"),
        # "X используется для Y"
        (r'(\w+)\s+(?:используется|применяется)\s+для\s+(\w+)', "used_for"),
    ]
    
    # Слова-маркеры утверждений
    CLAIM_MARKERS = [
        "является", "это", "представляет", "содержит", "имеет",
        "используется", "применяется", "связан", "относится",
        "принадлежит", "входит", "состоит", "образует"
    ]
    
    def extract_claims(
        self, 
        text: str, 
        source: ClaimSource = ClaimSource.MODEL,
        max_claims: int = 10
    ) -> List[Claim]:
        """
        Извлекает утверждения из текста
        
        Разбивает текст на предложения,
        извлекает triples и создаёт Claims
        """
        claims = []
        
        # Разбиваем на предложения
        sentences = re.split(r'[.!?]+', text)
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            # Проверяем, похоже ли на утверждение
            is_claim = any(
                marker in sentence.lower() 
                for marker in self.CLAIM_MARKERS
            )
            
            if not is_claim:
                continue
            
            # Пытаемся извлечь triple
            subject, predicate, object_ = self._extract_triple(sentence)
            
            claim = Claim(
                id=f"claim_{int(datetime.now().timestamp())}_{i}",
                text=sentence,
                subject=subject,
                predicate=predicate,
                object=object_,
                confidence=0.5,  # Базовая уверенность
                status=ClaimStatus.HYPOTHESIS,
                sources=[source.value]
            )
            
            claims.append(claim)
            
            if len(claims) >= max_claims:
                break
        
        return claims
    
    def _extract_triple(self, sentence: str) -> Tuple[str, str, str]:
        """Извлекает (subject, predicate, object) из предложения"""
        for pattern, pred in self.TRIPLE_PATTERNS:
            match = re.search(pattern, sentence, re.IGNORECASE)
            if match:
                return (match.group(1), pred, match.group(2))
        return ("", "", "")


class TruthLoop:
    """
    🔁 TruthLoop — контур верификации утверждений
    
    Этапы:
    1. ExtractClaims — выделить утверждения
    2. CheckAgainstMemory — поиск в памяти
    3. SelfConsistencyCheck — внутренняя проверка
    4. AssignConfidence — оценка уверенности
    5. WriteBack — обновление памяти и графа
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "truth.db"
            )
        self.db_path = db_path
        self._ensure_tables()
        
        self.extractor = ClaimExtractor()
        self._claim_cache: Dict[str, Claim] = {}
    
    def _ensure_tables(self):
        """Создаёт таблицы БД"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                subject TEXT,
                predicate TEXT,
                object TEXT,
                confidence REAL,
                status TEXT,
                sources TEXT,
                evidence_for TEXT,
                evidence_against TEXT,
                created_at TEXT,
                updated_at TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_claims_text ON claims(text)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_claims_subject ON claims(subject)
        """)
        
        conn.commit()
        conn.close()
    
    def extract_claims(
        self, 
        text: str, 
        source: ClaimSource = ClaimSource.MODEL
    ) -> List[Claim]:
        """Извлекает утверждения из текста"""
        return self.extractor.extract_claims(text, source)
    
    def check_against_memory(
        self, 
        claim: Claim,
        rag_memory=None,
        knowledge_graph=None
    ) -> Tuple[float, List[str], List[str]]:
        """
        Проверяет утверждение против памяти
        
        Returns:
            (confidence_delta, evidence_for, evidence_against)
        """
        evidence_for = []
        evidence_against = []
        confidence_delta = 0.0
        
        # Проверяем в RAG памяти
        if rag_memory:
            try:
                results = rag_memory.search(claim.text, n_results=3)
                for result in results:
                    score = result.get('combined_score', 0)
                    if score > 0.5:
                        evidence_for.append(f"memory:{result['id'][:8]}")
                        confidence_delta += 0.1
            except Exception as e:
                logger.debug(f"Ошибка поиска в RAG: {e}")
        
        # Проверяем в графе знаний
        if knowledge_graph and claim.subject:
            try:
                related = knowledge_graph.find_related(claim.subject)
                if related:
                    for node in related:
                        if claim.object and claim.object.lower() in node.lower():
                            evidence_for.append(f"graph:{node}")
                            confidence_delta += 0.15
            except Exception as e:
                logger.debug(f"Ошибка поиска в графе: {e}")
        
        return (confidence_delta, evidence_for, evidence_against)
    
    def check_self_consistency(
        self, 
        claim: Claim,
        all_claims: List[Claim]
    ) -> Tuple[float, List[str], List[str]]:
        """
        Проверяет внутреннюю согласованность
        
        Ищет противоречия с другими утверждениями
        """
        evidence_for = []
        evidence_against = []
        consistency_score = 0.0
        
        for other in all_claims:
            if other.id == claim.id:
                continue
            
            # Проверяем на противоречие
            if claim.subject and other.subject:
                if claim.subject.lower() == other.subject.lower():
                    if claim.object and other.object:
                        if claim.object.lower() != other.object.lower():
                            # Потенциальное противоречие
                            if claim.predicate == other.predicate:
                                evidence_against.append(f"contradicts:{other.id}")
                                consistency_score -= 0.2
                        else:
                            # Подтверждение
                            evidence_for.append(f"confirms:{other.id}")
                            consistency_score += 0.1
        
        return (consistency_score, evidence_for, evidence_against)
    
    def assign_confidence(
        self, 
        claim: Claim,
        base_confidence: float = 0.5,
        memory_delta: float = 0.0,
        consistency_delta: float = 0.0,
        source_bonus: float = 0.0
    ) -> float:
        """
        Вычисляет итоговую уверенность
        
        Формула:
        confidence = base + memory_delta + consistency_delta + source_bonus
        """
        confidence = base_confidence + memory_delta + consistency_delta + source_bonus
        
        # Ограничиваем [0.1, 0.95]
        confidence = max(0.1, min(0.95, confidence))
        
        return round(confidence, 3)
    
    def determine_status(self, confidence: float) -> ClaimStatus:
        """Определяет статус на основе уверенности"""
        if confidence >= 0.7:
            return ClaimStatus.SUPPORTED
        elif confidence <= 0.3:
            return ClaimStatus.CONTRADICTED
        else:
            return ClaimStatus.HYPOTHESIS
    
    def save_claim(self, claim: Claim):
        """Сохраняет утверждение в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO claims 
            (id, text, subject, predicate, object, confidence, status, 
             sources, evidence_for, evidence_against, created_at, 
             updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            claim.id,
            claim.text,
            claim.subject,
            claim.predicate,
            claim.object,
            claim.confidence,
            claim.status.value,
            json.dumps(claim.sources),
            json.dumps(claim.evidence_for),
            json.dumps(claim.evidence_against),
            claim.created_at.isoformat(),
            claim.updated_at.isoformat(),
            json.dumps(claim.metadata)
        ))
        
        conn.commit()
        conn.close()
        
        self._claim_cache[claim.id] = claim
    
    def verify(
        self,
        response_text: str,
        rag_memory=None,
        knowledge_graph=None,
        source: ClaimSource = ClaimSource.MODEL
    ) -> Dict[str, Any]:
        """
        Полный цикл верификации ответа
        
        Returns:
            {
                "claims": List[Claim],
                "overall_confidence": float,
                "status_distribution": dict,
                "verification_summary": str
            }
        """
        # 1. Извлекаем утверждения
        claims = self.extract_claims(response_text, source)
        
        if not claims:
            return {
                "claims": [],
                "overall_confidence": 0.5,
                "status_distribution": {"unknown": 1},
                "verification_summary": "Утверждения не найдены"
            }
        
        # 2. Проверяем каждое утверждение
        for claim in claims:
            # Проверка против памяти
            mem_delta, mem_for, mem_against = self.check_against_memory(
                claim, rag_memory, knowledge_graph
            )
            claim.evidence_for.extend(mem_for)
            claim.evidence_against.extend(mem_against)
            
            # Проверка внутренней согласованности
            cons_delta, cons_for, cons_against = self.check_self_consistency(
                claim, claims
            )
            claim.evidence_for.extend(cons_for)
            claim.evidence_against.extend(cons_against)
            
            # Вычисляем уверенность
            source_bonus = 0.1 if source == ClaimSource.USER else 0.0
            claim.confidence = self.assign_confidence(
                claim,
                base_confidence=0.5,
                memory_delta=mem_delta,
                consistency_delta=cons_delta,
                source_bonus=source_bonus
            )
            
            # Определяем статус
            claim.status = self.determine_status(claim.confidence)
            claim.updated_at = datetime.now()
            
            # Сохраняем
            self.save_claim(claim)
        
        # 3. Вычисляем общую уверенность
        if claims:
            overall_confidence = sum(c.confidence for c in claims) / len(claims)
        else:
            overall_confidence = 0.5
        
        # 4. Распределение статусов
        status_dist = {}
        for claim in claims:
            status = claim.status.value
            status_dist[status] = status_dist.get(status, 0) + 1
        
        # 5. Формируем summary
        summary = self._generate_summary(claims, overall_confidence)
        
        logger.info(
            f"🔁 TruthLoop: {len(claims)} claims, "
            f"confidence={overall_confidence:.2f}"
        )
        
        return {
            "claims": [c.to_dict() for c in claims],
            "overall_confidence": round(overall_confidence, 3),
            "status_distribution": status_dist,
            "verification_summary": summary
        }
    
    def _generate_summary(
        self, 
        claims: List[Claim], 
        overall: float
    ) -> str:
        """Генерирует краткое резюме верификации"""
        supported = sum(1 for c in claims if c.status == ClaimStatus.SUPPORTED)
        contradicted = sum(1 for c in claims if c.status == ClaimStatus.CONTRADICTED)
        hypothesis = sum(1 for c in claims if c.status == ClaimStatus.HYPOTHESIS)
        
        parts = []
        
        if supported > 0:
            parts.append(f"{supported} подтверждено")
        if contradicted > 0:
            parts.append(f"{contradicted} противоречий")
        if hypothesis > 0:
            parts.append(f"{hypothesis} гипотез")
        
        summary = ", ".join(parts) if parts else "нет данных"
        
        if overall >= 0.7:
            summary += " | высокий уровень доверия"
        elif overall >= 0.4:
            summary += " | средний уровень доверия"
        else:
            summary += " | низкий уровень доверия"
        
        return summary
    
    def get_claim(self, claim_id: str) -> Optional[Claim]:
        """Получает утверждение по ID"""
        if claim_id in self._claim_cache:
            return self._claim_cache[claim_id]
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM claims WHERE id = ?", (claim_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Claim(
                id=row['id'],
                text=row['text'],
                subject=row['subject'] or "",
                predicate=row['predicate'] or "",
                object=row['object'] or "",
                confidence=row['confidence'],
                status=ClaimStatus(row['status']),
                sources=json.loads(row['sources'] or '[]'),
                evidence_for=json.loads(row['evidence_for'] or '[]'),
                evidence_against=json.loads(row['evidence_against'] or '[]'),
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            )
        
        return None
    
    def find_similar_claims(self, text: str, limit: int = 5) -> List[Claim]:
        """Находит похожие утверждения"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Простой поиск по ключевым словам
        keywords = text.lower().split()[:5]
        
        results = []
        for kw in keywords:
            cursor.execute(
                "SELECT * FROM claims WHERE text LIKE ? LIMIT ?",
                (f"%{kw}%", limit)
            )
            for row in cursor.fetchall():
                claim = Claim(
                    id=row['id'],
                    text=row['text'],
                    confidence=row['confidence'],
                    status=ClaimStatus(row['status'])
                )
                if claim.id not in [c.id for c in results]:
                    results.append(claim)
        
        conn.close()
        return results[:limit]
    
    def verify_claims(self, claims: List[Claim]) -> Dict[str, Any]:
        """
        Верифицирует список утверждений (API для TruthLoopPhase)
        
        Args:
            claims: список утверждений для проверки
            
        Returns:
            dict: overall_confidence, verified_claims, status_distribution
        """
        for claim in claims:
            mem_delta, mem_for, mem_against = self.check_against_memory(claim)
            claim.evidence_for.extend(mem_for)
            claim.evidence_against.extend(mem_against)

            cons_delta, cons_for, cons_against = self.check_self_consistency(claim, claims)
            claim.evidence_for.extend(cons_for)
            claim.evidence_against.extend(cons_against)

            claim.confidence = self.assign_confidence(
                claim, base_confidence=0.5,
                memory_delta=mem_delta,
                consistency_delta=cons_delta,
            )

            claim.status = self.determine_status(claim.confidence)
            claim.updated_at = datetime.now()
            self.save_claim(claim)

        overall = sum(c.confidence for c in claims) / len(claims) if claims else 0.5

        return {
            "overall_confidence": round(overall, 3),
            "verified_claims": [c.to_dict() for c in claims],
            "status_distribution": {
                status: sum(1 for c in claims if c.status.value == status)
                for status in set(c.status.value for c in claims)
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        """Статистика TruthLoop"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM claims")
        total = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT status, COUNT(*) FROM claims GROUP BY status"
        )
        status_dist = dict(cursor.fetchall())
        
        cursor.execute(
            "SELECT AVG(confidence) FROM claims"
        )
        avg_conf = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_claims": total,
            "status_distribution": status_dist,
            "average_confidence": round(avg_conf, 3)
        }


# Глобальный экземпляр
_truth_loop: Optional[TruthLoop] = None


def get_truth_loop() -> TruthLoop:
    """Возвращает глобальный TruthLoop"""
    global _truth_loop
    if _truth_loop is None:
        _truth_loop = TruthLoop()
    return _truth_loop