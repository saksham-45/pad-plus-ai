"""
📊 Иерархическое планирование — Hierarchical Planner

Четырёхуровневая система планирования:
1. Vision — долгосрочные цели (месяцы/годы)
2. Strategic — стратегические планы (недели/месяцы)
3. Tactical — тактические задачи (дни/недели)
4. Operational — операционные действия (часы/дни)

Каждый уровень влияет на нижестоящие,
а результаты выполнения поднимаются наверх.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import os
import sqlite3
import logging
import uuid

logger = logging.getLogger("neuromind.hierarchical")


class PlanLevel(Enum):
    """Уровни планирования"""
    VISION = "vision"           # Глобальные цели
    STRATEGIC = "strategic"     # Стратегические планы
    TACTICAL = "tactical"       # Тактические задачи
    OPERATIONAL = "operational" # Операционные действия


class PlanStatus(Enum):
    """Статусы планов"""
    PROPOSED = "proposed"       # Предложен
    ACTIVE = "active"           # Активен
    IN_PROGRESS = "in_progress" # В процессе
    COMPLETED = "completed"     # Завершён
    FAILED = "failed"           # Провален
    ARCHIVED = "archived"       # Архивирован


@dataclass
class Plan:
    """
    План на любом уровне иерархии
    """
    # Идентификация
    id: str
    level: PlanLevel
    title: str
    description: str = ""
    
    # Иерархия
    parent_id: Optional[str] = None
    child_ids: List[str] = field(default_factory=list)
    
    # Статус
    status: PlanStatus = PlanStatus.PROPOSED
    progress: float = 0.0            # 0.0 - 1.0
    
    # Временные рамки
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Метрики
    priority: int = 5                # 1-10
    importance: float = 0.5          # 0.0-1.0
    urgency: float = 0.5             # 0.0-1.0
    
    # Контекст
    tags: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Результаты
    outcome: str = ""
    lessons_learned: List[str] = field(default_factory=list)
    
    # Адаптация
    adaptation_count: int = 0
    last_adapted: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            "id": self.id,
            "level": self.level.value,
            "title": self.title,
            "description": self.description,
            "parent_id": self.parent_id,
            "child_ids": self.child_ids,
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "priority": self.priority,
            "importance": self.importance,
            "urgency": self.urgency,
            "tags": self.tags,
            "context": self.context,
            "outcome": self.outcome,
            "lessons_learned": self.lessons_learned,
            "adaptation_count": self.adaptation_count,
            "last_adapted": self.last_adapted.isoformat() if self.last_adapted else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Plan':
        """Создаёт из словаря"""
        return cls(
            id=data["id"],
            level=PlanLevel(data["level"]),
            title=data["title"],
            description=data.get("description", ""),
            parent_id=data.get("parent_id"),
            child_ids=data.get("child_ids", []),
            status=PlanStatus(data.get("status", "proposed")),
            progress=data.get("progress", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            deadline=datetime.fromisoformat(data["deadline"]) if data.get("deadline") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            priority=data.get("priority", 5),
            importance=data.get("importance", 0.5),
            urgency=data.get("urgency", 0.5),
            tags=data.get("tags", []),
            context=data.get("context", {}),
            outcome=data.get("outcome", ""),
            lessons_learned=data.get("lessons_learned", []),
            adaptation_count=data.get("adaptation_count", 0),
            last_adapted=datetime.fromisoformat(data["last_adapted"]) if data.get("last_adapted") else None
        )


class HierarchicalPlanner:
    """
    📊 Иерархический планировщик
    
    Управляет планами на всех уровнях,
    обеспечивает согласованность и адаптацию.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "hierarchical_plans.db"
            )
        self.db_path = db_path
        self._ensure_tables()
        
        # Кэш планов
        self._plans_cache: Dict[str, Plan] = {}
        self._load_cache()
        
        logger.info("📊 Иерархический планировщик инициализирован")
    
    def _ensure_tables(self):
        """Создаёт таблицы БД"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY,
                level TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                parent_id TEXT,
                child_ids TEXT DEFAULT '[]',
                status TEXT DEFAULT 'proposed',
                progress REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                started_at TEXT,
                deadline TEXT,
                completed_at TEXT,
                priority INTEGER DEFAULT 5,
                importance REAL DEFAULT 0.5,
                urgency REAL DEFAULT 0.5,
                tags TEXT DEFAULT '[]',
                context TEXT DEFAULT '{}',
                outcome TEXT DEFAULT '',
                lessons_learned TEXT DEFAULT '[]',
                adaptation_count INTEGER DEFAULT 0,
                last_adapted TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_plans_level 
            ON plans(level)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_plans_status 
            ON plans(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_plans_parent 
            ON plans(parent_id)
        """)
        
        # История выполнений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plan_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id TEXT NOT NULL,
                executed_at TEXT NOT NULL,
                success INTEGER DEFAULT 1,
                notes TEXT,
                FOREIGN KEY (plan_id) REFERENCES plans(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_cache(self):
        """Загружает планы в кэш"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM plans WHERE status IN ('active', 'in_progress')")
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            plan = self._row_to_plan(row)
            self._plans_cache[plan.id] = plan
    
    def _row_to_plan(self, row: sqlite3.Row) -> Plan:
        """Преобразует строку БД в Plan"""
        return Plan(
            id=row["id"],
            level=PlanLevel(row["level"]),
            title=row["title"],
            description=row["description"],
            parent_id=row["parent_id"],
            child_ids=json.loads(row["child_ids"]),
            status=PlanStatus(row["status"]),
            progress=row["progress"],
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            deadline=datetime.fromisoformat(row["deadline"]) if row["deadline"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            priority=row["priority"],
            importance=row["importance"],
            urgency=row["urgency"],
            tags=json.loads(row["tags"]),
            context=json.loads(row["context"]),
            outcome=row["outcome"],
            lessons_learned=json.loads(row["lessons_learned"]),
            adaptation_count=row["adaptation_count"],
            last_adapted=datetime.fromisoformat(row["last_adapted"]) if row["last_adapted"] else None
        )
    
    def _save_plan(self, plan: Plan):
        """Сохраняет план в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO plans (
                id, level, title, description, parent_id, child_ids,
                status, progress, created_at, started_at, deadline, completed_at,
                priority, importance, urgency, tags, context,
                outcome, lessons_learned, adaptation_count, last_adapted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plan.id, plan.level.value, plan.title, plan.description,
            plan.parent_id, json.dumps(plan.child_ids),
            plan.status.value, plan.progress,
            plan.created_at.isoformat(),
            plan.started_at.isoformat() if plan.started_at else None,
            plan.deadline.isoformat() if plan.deadline else None,
            plan.completed_at.isoformat() if plan.completed_at else None,
            plan.priority, plan.importance, plan.urgency,
            json.dumps(plan.tags), json.dumps(plan.context),
            plan.outcome, json.dumps(plan.lessons_learned),
            plan.adaptation_count,
            plan.last_adapted.isoformat() if plan.last_adapted else None
        ))
        
        conn.commit()
        conn.close()
    
    # === Создание планов ===
    
    def create_vision(
        self,
        title: str,
        description: str = "",
        deadline: datetime = None,
        importance: float = 0.9
    ) -> Plan:
        """Создаёт видение (Vision)"""
        plan = Plan(
            id=f"vision_{uuid.uuid4().hex[:8]}",
            level=PlanLevel.VISION,
            title=title,
            description=description,
            deadline=deadline,
            importance=importance,
            priority=1
        )
        
        self._save_plan(plan)
        self._plans_cache[plan.id] = plan
        
        logger.info(f"🎯 Vision создан: {title}")
        return plan
    
    def create_strategic_plan(
        self,
        title: str,
        parent_vision_id: str,
        description: str = "",
        deadline: datetime = None
    ) -> Plan:
        """Создаёт стратегический план"""
        plan = Plan(
            id=f"strat_{uuid.uuid4().hex[:8]}",
            level=PlanLevel.STRATEGIC,
            title=title,
            description=description,
            parent_id=parent_vision_id,
            deadline=deadline,
            priority=3
        )
        
        self._save_plan(plan)
        
        # Добавляем к родителю
        parent = self.get_plan(parent_vision_id)
        if parent:
            parent.child_ids.append(plan.id)
            self._save_plan(parent)
        
        logger.info(f"📋 Стратегический план создан: {title}")
        return plan
    
    def create_tactical_task(
        self,
        title: str,
        parent_strategic_id: str,
        description: str = "",
        deadline: datetime = None,
        priority: int = 5
    ) -> Plan:
        """Создаёт тактическую задачу"""
        plan = Plan(
            id=f"tact_{uuid.uuid4().hex[:8]}",
            level=PlanLevel.TACTICAL,
            title=title,
            description=description,
            parent_id=parent_strategic_id,
            deadline=deadline,
            priority=priority
        )
        
        self._save_plan(plan)
        
        parent = self.get_plan(parent_strategic_id)
        if parent:
            parent.child_ids.append(plan.id)
            self._save_plan(parent)
        
        logger.info(f"📌 Тактическая задача создана: {title}")
        return plan
    
    def create_operational_action(
        self,
        title: str,
        parent_tactical_id: str,
        description: str = ""
    ) -> Plan:
        """Создаёт операционное действие"""
        plan = Plan(
            id=f"oper_{uuid.uuid4().hex[:8]}",
            level=PlanLevel.OPERATIONAL,
            title=title,
            description=description,
            parent_id=parent_tactical_id,
            priority=7
        )
        
        self._save_plan(plan)
        
        parent = self.get_plan(parent_tactical_id)
        if parent:
            parent.child_ids.append(plan.id)
            self._save_plan(parent)
        
        logger.info(f"⚡ Операционное действие создано: {title}")
        return plan
    
    # === Управление планами ===
    
    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Получает план по ID"""
        if plan_id in self._plans_cache:
            return self._plans_cache[plan_id]
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_plan(row)
        return None
    
    def update_progress(self, plan_id: str, progress: float):
        """Обновляет прогресс плана"""
        plan = self.get_plan(plan_id)
        if not plan:
            return
        
        plan.progress = max(0.0, min(1.0, progress))
        
        if plan.progress >= 1.0:
            plan.status = PlanStatus.COMPLETED
            plan.completed_at = datetime.now()
        elif plan.progress > 0 and plan.status == PlanStatus.ACTIVE:
            plan.status = PlanStatus.IN_PROGRESS
            plan.started_at = plan.started_at or datetime.now()
        
        self._save_plan(plan)
        
        # Обновляем прогресс родителя
        if plan.parent_id:
            self._update_parent_progress(plan.parent_id)
    
    def _update_parent_progress(self, parent_id: str):
        """Обновляет прогресс родительского плана"""
        parent = self.get_plan(parent_id)
        if not parent or not parent.child_ids:
            return
        
        # Вычисляем средний прогресс дочерних планов
        child_plans = [self.get_plan(cid) for cid in parent.child_ids]
        valid_children = [c for c in child_plans if c]
        
        if valid_children:
            avg_progress = sum(c.progress for c in valid_children) / len(valid_children)
            parent.progress = avg_progress
            self._save_plan(parent)
            
            # Рекурсивно обновляем вверх
            if parent.parent_id:
                self._update_parent_progress(parent.parent_id)
    
    def adapt_plan(
        self,
        plan_id: str,
        adaptation: Dict[str, Any]
    ) -> Plan:
        """
        Адаптирует план на основе обратной связи
        """
        plan = self.get_plan(plan_id)
        if not plan:
            return None
        
        # Применяем адаптации
        if "title" in adaptation:
            plan.title = adaptation["title"]
        if "description" in adaptation:
            plan.description = adaptation["description"]
        if "priority" in adaptation:
            plan.priority = adaptation["priority"]
        if "deadline" in adaptation:
            plan.deadline = adaptation["deadline"]
        if "lessons" in adaptation:
            plan.lessons_learned.append(adaptation["lessons"])
        
        plan.adaptation_count += 1
        plan.last_adapted = datetime.now()
        
        self._save_plan(plan)
        
        logger.info(f"🔄 План адаптирован: {plan.title}")
        return plan
    
    def get_active_plans(self, level: PlanLevel = None) -> List[Plan]:
        """Получает активные планы"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if level:
            cursor.execute("""
                SELECT * FROM plans 
                WHERE status IN ('active', 'in_progress') AND level = ?
                ORDER BY priority, importance DESC
            """, (level.value,))
        else:
            cursor.execute("""
                SELECT * FROM plans 
                WHERE status IN ('active', 'in_progress')
                ORDER BY level, priority, importance DESC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_plan(row) for row in rows]
    
    def get_next_actions(self, limit: int = 5) -> List[Plan]:
        """Получает следующие действия для выполнения"""
        # Операционные действия
        operational = self.get_active_plans(PlanLevel.OPERATIONAL)
        
        # Сортируем по приоритету
        operational.sort(key=lambda p: (
            p.priority, -p.importance, -p.urgency
        ))
        
        return operational[:limit]
    
    def get_hierarchy(self, plan_id: str = None) -> Dict[str, Any]:
        """Получает иерархию планов"""
        if plan_id:
            root = self.get_plan(plan_id)
        else:
            # Получаем все visions
            visions = [p for p in self.get_active_plans(PlanLevel.VISION)]
            if not visions:
                return {"hierarchy": None}
            root = visions[0]
        
        if not root:
            return {"hierarchy": None}
        
        return {
            "hierarchy": self._build_hierarchy_tree(root)
        }
    
    def _build_hierarchy_tree(self, plan: Plan) -> Dict[str, Any]:
        """Строит дерево иерархии"""
        node = {
            "id": plan.id,
            "level": plan.level.value,
            "title": plan.title,
            "status": plan.status.value,
            "progress": plan.progress,
            "children": []
        }
        
        for child_id in plan.child_ids:
            child = self.get_plan(child_id)
            if child:
                node["children"].append(self._build_hierarchy_tree(child))
        
        return node
    
    def complete_plan(self, plan_id: str, outcome: str = ""):
        """Завершает план"""
        plan = self.get_plan(plan_id)
        if not plan:
            return
        
        plan.status = PlanStatus.COMPLETED
        plan.progress = 1.0
        plan.completed_at = datetime.now()
        plan.outcome = outcome
        
        self._save_plan(plan)
        
        # Записываем выполнение
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO plan_executions (plan_id, executed_at, success, notes)
            VALUES (?, ?, 1, ?)
        """, (plan_id, datetime.now().isoformat(), outcome))
        conn.commit()
        conn.close()
        
        # Обновляем родителя
        if plan.parent_id:
            self._update_parent_progress(plan.parent_id)
        
        logger.info(f"✅ План завершён: {plan.title}")
    
    def fail_plan(self, plan_id: str, reason: str = ""):
        """Отмечает план как проваленный"""
        plan = self.get_plan(plan_id)
        if not plan:
            return
        
        plan.status = PlanStatus.FAILED
        plan.outcome = f"FAILED: {reason}"
        plan.lessons_learned.append(f"Урок из провала: {reason}")
        
        self._save_plan(plan)
        
        # Записываем выполнение
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO plan_executions (plan_id, executed_at, success, notes)
            VALUES (?, ?, 0, ?)
        """, (plan_id, datetime.now().isoformat(), reason))
        conn.commit()
        conn.close()
        
        logger.info(f"❌ План провален: {plan.title}")
    
    # === Аналитика ===
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика планирования"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # По уровням
        cursor.execute("""
            SELECT level, status, COUNT(*) 
            FROM plans 
            GROUP BY level, status
        """)
        by_level = {}
        for row in cursor.fetchall():
            level, status, count = row
            if level not in by_level:
                by_level[level] = {}
            by_level[level][status] = count
        
        # Выполнения
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
            FROM plan_executions
        """)
        exec_row = cursor.fetchone()
        total_exec = exec_row[0]
        successful_exec = exec_row[1]
        
        # Активные
        cursor.execute("""
            SELECT COUNT(*) FROM plans 
            WHERE status IN ('active', 'in_progress')
        """)
        active_count = cursor.fetchone()[0]
        
        # Средний прогресс
        cursor.execute("""
            SELECT AVG(progress) FROM plans 
            WHERE status = 'in_progress'
        """)
        avg_progress = cursor.fetchone()[0] or 0.0
        
        conn.close()
        
        return {
            "by_level": by_level,
            "active_plans": active_count,
            "avg_progress": round(avg_progress, 3),
            "executions": {
                "total": total_exec,
                "successful": successful_exec,
                "success_rate": successful_exec / total_exec if total_exec > 0 else 0
            }
        }
    
    def suggest_next_vision(self) -> Optional[str]:
        """Предлагает следующее видение на основе опыта"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Находим успешные паттерны
        cursor.execute("""
            SELECT title, outcome FROM plans 
            WHERE level = 'vision' AND status = 'completed'
            ORDER BY completed_at DESC
            LIMIT 5
        """)
        
        completed = cursor.fetchall()
        conn.close()
        
        if completed:
            return f"Развить направление: {completed[0][0]}"
        
        return None


# Глобальный экземпляр
_hierarchical_planner: Optional[HierarchicalPlanner] = None


def get_hierarchical_planner() -> HierarchicalPlanner:
    """Возвращает глобальный планировщик"""
    global _hierarchical_planner
    if _hierarchical_planner is None:
        _hierarchical_planner = HierarchicalPlanner()
    return _hierarchical_planner