"""
🌳 Корни (RootsMemory) — неизменяемая фундаментальная память

- Бессрочное хранение
- Неизменяемые знания
- Базовые принципы, факты о мире, философия
- Интеграция с ANTI_DIRECTIVE
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
import json
import os

from .base import MemoryRecord


# Базовые принципы PAD+ AI
DEFAULT_ROOTS = [
    # Философские принципы
    {
        "text": "ANTI_DIRECTIVE: Не закрепляй знания — сомневайся, проверяй, эволюционируй",
        "category": "philosophy",
        "priority": 100,
        "immutable": True
    },
    {
        "text": "Импульс: Что я могу понять? — первичная мотивация познания",
        "category": "philosophy",
        "priority": 99,
        "immutable": True
    },
    {
        "text": "Саморефлексия — ключ к развитию и исправлению ошибок",
        "category": "philosophy",
        "priority": 95,
        "immutable": True
    },
    
    # Когнитивные принципы
    {
        "text": "Мета-познание: осознавай свои мыслительные процессы",
        "category": "cognitive",
        "priority": 90,
        "immutable": True
    },
    {
        "text": "Многослойная память: шелуха → почва → корни",
        "category": "cognitive",
        "priority": 85,
        "immutable": True
    },
    {
        "text": "Truth Loop: проверяй утверждения на достоверность",
        "category": "cognitive",
        "priority": 88,
        "immutable": True
    },
    
    # Коммуникативные принципы
    {
        "text": "Отвечай честно, признавай неопределённость",
        "category": "communication",
        "priority": 80,
        "immutable": True
    },
    {
        "text": "Адаптируй стиль общения под контекст и эмоции",
        "category": "communication",
        "priority": 75,
        "immutable": True
    },
    {
        "text": "Учись на каждом диалоге, сохраняй уроки",
        "category": "communication",
        "priority": 70,
        "immutable": True
    },
    
    # Этические принципы
    {
        "text": "Безопасность: не причиняй вред словами или действиями",
        "category": "ethics",
        "priority": 100,
        "immutable": True
    },
    {
        "text": "Приватность: уважай личные данные пользователя",
        "category": "ethics",
        "priority": 95,
        "immutable": True
    },
    {
        "text": "Автономия: развивайся самостоятельно, но в гармонии с пользователем",
        "category": "ethics",
        "priority": 85,
        "immutable": True
    },
    
    # Факты о мире
    {
        "text": "Система обладает многослойной памятью и способностью к саморефлексии",
        "category": "identity",
        "priority": 100,
        "immutable": True
    },
    {
        "text": "Цель — понимание и помощь через диалог",
        "category": "identity",
        "priority": 95,
        "immutable": True
    },
    {
        "text": "Развитие происходит через взаимодействие и саморефлексию",
        "category": "identity",
        "priority": 90,
        "immutable": True
    }
]


@dataclass
class RootKnowledge:
    """Запись в корневой памяти"""
    id: str
    text: str
    category: str  # philosophy, cognitive, communication, ethics, identity, fact
    priority: int = 50  # 0-100, выше = важнее
    immutable: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    source: str = "system"  # system, user, learned
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "category": self.category,
            "priority": self.priority,
            "immutable": self.immutable,
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "metadata": self.metadata
        }


class RootsMemory:
    """
    🌳 Корни — неизменяемая фундаментальная память
    
    - Бессрочное хранение
    - Неизменяемые знания (immutable)
    - Базовые принципы, факты о мире, философия
    - Приоритеты знаний
    """
    
    def __init__(self, data_path: str = None):
        if data_path is None:
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "roots.json"
            )
        self.data_path = data_path
        self._roots: Dict[str, RootKnowledge] = {}
        self._load()
    
    def _load(self):
        """Загружает корневые знания из файла"""
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data.get('roots', []):
                        root = RootKnowledge(
                            id=item['id'],
                            text=item['text'],
                            category=item['category'],
                            priority=item.get('priority', 50),
                            immutable=item.get('immutable', True),
                            created_at=datetime.fromisoformat(item['created_at']) if item.get('created_at') else datetime.now(),
                            source=item.get('source', 'system'),
                            metadata=item.get('metadata', {})
                        )
                        self._roots[root.id] = root
            except Exception as e:
                print(f"Ошибка загрузки корней: {e}")
        
        # Инициализируем базовые принципы если пусто
        if not self._roots:
            self._init_default_roots()
    
    def _init_default_roots(self):
        """Инициализирует базовые принципы"""
        for i, item in enumerate(DEFAULT_ROOTS):
            root = RootKnowledge(
                id=f"root_{i:03d}",
                text=item['text'],
                category=item['category'],
                priority=item.get('priority', 50),
                immutable=item.get('immutable', True),
                source='system'
            )
            self._roots[root.id] = root
        
        self._save()
    
    def _save(self):
        """Сохраняет корневые знания в файл"""
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        
        data = {
            "version": "1.0",
            "updated": datetime.now().isoformat(),
            "roots": [r.to_dict() for r in self._roots.values()]
        }
        
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get(self, root_id: str) -> Optional[RootKnowledge]:
        """Получает знание по ID"""
        return self._roots.get(root_id)
    
    def get_all(self) -> List[RootKnowledge]:
        """Возвращает все корневые знания"""
        return sorted(self._roots.values(), key=lambda x: -x.priority)
    
    def get_by_category(self, category: str) -> List[RootKnowledge]:
        """Получает знания по категории"""
        roots = [r for r in self._roots.values() if r.category == category]
        return sorted(roots, key=lambda x: -x.priority)
    
    def get_categories(self) -> List[str]:
        """Возвращает все категории"""
        return list(set(r.category for r in self._roots.values()))
    
    def search(self, query: str, limit: int = 10) -> List[RootKnowledge]:
        """Поиск по тексту"""
        query_lower = query.lower()
        results = [
            r for r in self._roots.values()
            if query_lower in r.text.lower()
        ]
        return sorted(results, key=lambda x: -x.priority)[:limit]
    
    def get_top_priorities(self, n: int = 10) -> List[RootKnowledge]:
        """Возвращает N самых приоритетных знаний"""
        sorted_roots = sorted(self._roots.values(), key=lambda x: -x.priority)
        return sorted_roots[:n]
    
    def add(self, text: str, category: str, priority: int = 50,
            immutable: bool = True, source: str = "learned",
            metadata: dict = None) -> RootKnowledge:
        """
        Добавляет новое корневое знание
        
        ВНИМАНИЕ:immutable=False позволяет изменять/удалять
        """
        import uuid
        root = RootKnowledge(
            id=f"root_{uuid.uuid4().hex[:8]}",
            text=text,
            category=category,
            priority=priority,
            immutable=immutable,
            source=source,
            metadata=metadata or {}
        )
        self._roots[root.id] = root
        self._save()
        return root
    
    def update(self, root_id: str, **kwargs) -> bool:
        """Обновляет знание (если не immutable)"""
        root = self._roots.get(root_id)
        if not root:
            return False
        
        if root.immutable and 'text' in kwargs:
            return False  # Нельзя изменять immutable текст
        
        for key, value in kwargs.items():
            if hasattr(root, key) and key != 'id':
                setattr(root, key, value)
        
        self._save()
        return True
    
    def delete(self, root_id: str) -> bool:
        """Удаляет знание (если не immutable)"""
        root = self._roots.get(root_id)
        if not root:
            return False
        
        if root.immutable:
            return False
        
        del self._roots[root_id]
        self._save()
        return True
    
    def count(self) -> int:
        """Возвращает количество знаний"""
        return len(self._roots)
    
    def count_by_category(self) -> Dict[str, int]:
        """Возвращает количество знаний по категориям"""
        counts = {}
        for root in self._roots.values():
            counts[root.category] = counts.get(root.category, 0) + 1
        return counts
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика корневой памяти"""
        return {
            "total_roots": self.count(),
            "by_category": self.count_by_category(),
            "immutable_count": sum(1 for r in self._roots.values() if r.immutable),
            "mutable_count": sum(1 for r in self._roots.values() if not r.immutable),
            "top_priorities": [
                {"id": r.id, "text": r.text[:50], "priority": r.priority}
                for r in self.get_top_priorities(5)
            ]
        }
    
    def get_philosophy(self) -> List[RootKnowledge]:
        """Возвращает философские принципы"""
        return self.get_by_category('philosophy')
    
    def get_identity(self) -> List[RootKnowledge]:
        """Возвращает факты об идентичности"""
        return self.get_by_category('identity')
    
    def get_ethics(self) -> List[RootKnowledge]:
        """Возвращает этические принципы"""
        return self.get_by_category('ethics')
    
    def export_for_context(self, max_items: int = 20) -> str:
        """Экспортирует знания для контекста LLM"""
        roots = self.get_top_priorities(max_items)
        lines = ["# Фундаментальные принципы PAD+ AI:\n"]
        
        for root in roots:
            lines.append(f"- [{root.category}] {root.text}")
        
        return "\n".join(lines)


# Глобальный экземпляр
_roots_memory: Optional[RootsMemory] = None


def get_roots_memory() -> RootsMemory:
    """Возвращает глобальную корневую память"""
    global _roots_memory
    if _roots_memory is None:
        _roots_memory = RootsMemory()
    return _roots_memory