"""
Граф знаний PAD+ AI

NetworkX-based граф для хранения связей между концепциями.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Set
import json
import os
import sqlite3

# NetworkX для графа
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None


@dataclass
class Concept:
    """Концепция в графе знаний"""
    id: str
    name: str
    concept_type: str = "concept"  # concept, fact, skill, question
    confidence: float = 0.5
    source: str = "user"
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.concept_type,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


@dataclass 
class Relation:
    """Связь между концепциями"""
    source_id: str
    target_id: str
    relation_type: str = "related"  # is_a, part_of, causes, related, contradicts
    weight: float = 1.0
    confidence: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.relation_type,
            "weight": self.weight,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat()
        }


class KnowledgeGraph:
    """
    Граф знаний на NetworkX
    
    Хранит концепции и связи между ними.
    Поддерживает поиск путей, кластеризацию, анализ.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "knowledge.db"
            )
        self.db_path = db_path
        self._ensure_tables()
        
        # Создаём граф
        if NETWORKX_AVAILABLE:
            self.graph = nx.DiGraph()
        else:
            self.graph = None
        
        # Кэш концепций
        self._concepts: Dict[str, Concept] = {}
        self._load_from_db()
    
    def _ensure_tables(self):
        """Создаёт таблицы в БД"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица концепций
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concepts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT DEFAULT 'concept',
                confidence REAL DEFAULT 0.5,
                source TEXT DEFAULT 'user',
                created_at TEXT NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        
        # Таблица связей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                type TEXT DEFAULT 'related',
                weight REAL DEFAULT 1.0,
                confidence REAL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES concepts(id),
                FOREIGN KEY (target_id) REFERENCES concepts(id)
            )
        """)
        
        # Индексы
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_concepts_name ON concepts(name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_id)
        """)
        
        conn.commit()
        conn.close()
    
    def _load_from_db(self):
        """Загружает граф из БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Загружаем концепции
        cursor.execute("SELECT * FROM concepts")
        for row in cursor.fetchall():
            concept = Concept(
                id=row['id'],
                name=row['name'],
                concept_type=row['type'],
                confidence=row['confidence'],
                source=row['source'],
                created_at=datetime.fromisoformat(row['created_at']),
                metadata=json.loads(row['metadata'])
            )
            self._concepts[concept.id] = concept
            
            if self.graph:
                self.graph.add_node(concept.id, **concept.to_dict())
        
        # Загружаем связи
        cursor.execute("SELECT * FROM relations")
        for row in cursor.fetchall():
            if self.graph:
                self.graph.add_edge(
                    row['source_id'], 
                    row['target_id'],
                    type=row['type'],
                    weight=row['weight'],
                    confidence=row['confidence']
                )
        
        conn.close()
    
    def add_concept(self, name: str, concept_type: str = "concept",
                    confidence: float = 0.5, source: str = "user",
                    metadata: dict = None) -> Concept:
        """Добавляет концепцию в граф"""
        import uuid
        concept_id = str(uuid.uuid4())[:8]
        
        concept = Concept(
            id=concept_id,
            name=name,
            concept_type=concept_type,
            confidence=confidence,
            source=source,
            metadata=metadata or {}
        )
        
        # Сохраняем в БД
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO concepts (id, name, type, confidence, source, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            concept.id, concept.name, concept.concept_type,
            concept.confidence, concept.source,
            concept.created_at.isoformat(),
            json.dumps(concept.metadata, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
        
        # Добавляем в память и граф
        self._concepts[concept.id] = concept
        if self.graph:
            self.graph.add_node(concept.id, **concept.to_dict())
        
        return concept
    
    def add_relation(self, source_id: str, target_id: str,
                     relation_type: str = "related",
                     weight: float = 1.0,
                     confidence: float = 0.5) -> Optional[Relation]:
        """Добавляет связь между концепциями"""
        # Проверяем существование концепций
        if source_id not in self._concepts or target_id not in self._concepts:
            return None
        
        relation = Relation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            confidence=confidence
        )
        
        # Сохраняем в БД
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO relations (source_id, target_id, type, weight, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            relation.source_id, relation.target_id,
            relation.relation_type, relation.weight,
            relation.confidence,
            relation.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Добавляем в граф
        if self.graph:
            self.graph.add_edge(
                source_id, target_id,
                type=relation_type,
                weight=weight,
                confidence=confidence
            )
        
        return relation
    
    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Получает концепцию по ID"""
        return self._concepts.get(concept_id)
    
    def find_concepts(self, query: str, limit: int = 10) -> List[Concept]:
        """Ищет концепции по имени"""
        query_lower = query.lower()
        results = []
        
        for concept in self._concepts.values():
            if query_lower in concept.name.lower():
                results.append(concept)
                if len(results) >= limit:
                    break
        
        return results
    
    def get_related(self, concept_id: str, depth: int = 1) -> List[Concept]:
        """Получает связанные концепции"""
        if not self.graph or concept_id not in self._concepts:
            return []
        
        related = set()
        
        # Прямые связи
        if self.graph.has_node(concept_id):
            for neighbor in self.graph.neighbors(concept_id):
                if neighbor in self._concepts:
                    related.add(self._concepts[neighbor])
        
        # Обратные связи
        if self.graph.has_node(concept_id):
            for predecessor in self.graph.predecessors(concept_id):
                if predecessor in self._concepts:
                    related.add(self._concepts[predecessor])
        
        return list(related)
    
    def find_path(self, source_id: str, target_id: str) -> List[str]:
        """Находит путь между концепциями"""
        if not self.graph:
            return []
        
        try:
            path = nx.shortest_path(self.graph, source_id, target_id)
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
    
    def get_stats(self) -> dict:
        """Возвращает статистику графа"""
        if self.graph:
            return {
                "nodes": self.graph.number_of_nodes(),
                "edges": self.graph.number_of_edges(),
                "density": nx.density(self.graph) if self.graph.number_of_nodes() > 1 else 0,
                "networkx_available": True
            }
        return {
            "nodes": len(self._concepts),
            "edges": 0,
            "density": 0,
            "networkx_available": False
        }
    
    def to_dict(self) -> dict:
        """Экспортирует граф в словарь"""
        nodes = [c.to_dict() for c in self._concepts.values()]
        
        links = []
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM relations")
        
        for row in cursor.fetchall():
            links.append({
                "source": row['source_id'],
                "target": row['target_id'],
                "type": row['type'],
                "weight": row['weight']
            })
        
        conn.close()
        
        return {
            "nodes": nodes,
            "links": links,
            "stats": self.get_stats()
        }


# Глобальный экземпляр
_knowledge_graph: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    """Возвращает глобальный граф знаний"""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraph()
    return _knowledge_graph