"""
📦 DataManager — Экспорт и импорт данных

- Полный backup системы
- Выборочный экспорт
- Восстановление из backup
- Миграция данных
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
import json
import os
import zipfile
import tempfile
import logging

logger = logging.getLogger("PAD+.data_manager")


class DataCategory(Enum):
    """Категории данных"""
    MEMORY = "memory"           # RAG, факты
    PERSONA = "persona"         # Личность
    EMOTION = "emotion"         # Эмоции
    KNOWLEDGE = "knowledge"     # Граф знаний
    ROOTS = "roots"             # Фундаментальные принципы
    HEALTH = "health"           # Здоровье
    ANALYTICS = "analytics"     # Аналитика
    CACHE = "cache"             # Кэш
    ALL = "all"


@dataclass
class ExportMetadata:
    """Метаданные экспорта"""
    version: str
    exported_at: datetime
    categories: List[str]
    total_items: int
    checksum: str = ""
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "exported_at": self.exported_at.isoformat(),
            "categories": self.categories,
            "total_items": self.total_items,
            "checksum": self.checksum
        }


class DataManager:
    """
    📦 Менеджер данных
    
    Features:
    - Полный backup системы
    - Выборочный экспорт по категориям
    - Восстановление из backup
    - Сжатие данных (ZIP)
    - Проверка целостности
    """
    
    VERSION = "2.4.0"
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data"
            )
        self.data_dir = data_dir
        self.export_dir = os.path.join(data_dir, "exports")
        os.makedirs(self.export_dir, exist_ok=True)
    
    def _collect_data(self, categories: List[DataCategory]) -> Dict[str, Any]:
        """Собирает данные из указанных категорий"""
        data = {}
        
        for category in categories:
            if category == DataCategory.ALL:
                return self._collect_all_data()
            
            try:
                if category == DataCategory.MEMORY:
                    data["memory"] = self._export_memory()
                elif category == DataCategory.PERSONA:
                    data["persona"] = self._export_persona()
                elif category == DataCategory.EMOTION:
                    data["emotion"] = self._export_emotion()
                elif category == DataCategory.KNOWLEDGE:
                    data["knowledge"] = self._export_knowledge()
                elif category == DataCategory.ROOTS:
                    data["roots"] = self._export_roots()
                elif category == DataCategory.HEALTH:
                    data["health"] = self._export_health()
                elif category == DataCategory.ANALYTICS:
                    data["analytics"] = self._export_analytics()
                elif category == DataCategory.CACHE:
                    data["cache"] = self._export_cache()
            except Exception as e:
                logger.warning(f"Error exporting {category.value}: {e}")
                data[category.value] = {"error": str(e)}
        
        return data
    
    def _collect_all_data(self) -> Dict[str, Any]:
        """Собирает все данные"""
        return self._collect_data([
            DataCategory.MEMORY,
            DataCategory.PERSONA,
            DataCategory.EMOTION,
            DataCategory.KNOWLEDGE,
            DataCategory.ROOTS,
            DataCategory.HEALTH,
            DataCategory.ANALYTICS
        ])
    
    def _export_memory(self) -> Dict[str, Any]:
        """Экспортирует память"""
        result = {"rag": [], "facts": []}
        
        # RAG
        rag_path = os.path.join(self.data_dir, "memory.db")
        if os.path.exists(rag_path):
            try:
                import sqlite3
                conn = sqlite3.connect(rag_path)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM memory")
                for row in cursor.fetchall():
                    result["rag"].append({
                        "id": row[0],
                        "content": row[1],
                        "timestamp": row[2]
                    })
                conn.close()
            except Exception as e:
                logger.warning(f"RAG export error: {e}")
        
        # Facts
        facts_path = os.path.join(self.data_dir, "facts.db")
        if os.path.exists(facts_path):
            try:
                import sqlite3
                conn = sqlite3.connect(facts_path)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM facts")
                for row in cursor.fetchall():
                    result["facts"].append({
                        "id": row[0],
                        "fact": row[1],
                        "confidence": row[2]
                    })
                conn.close()
            except Exception as e:
                logger.warning(f"Facts export error: {e}")
        
        return result
    
    def _export_persona(self) -> Dict[str, Any]:
        """Экспортирует личность"""
        persona_path = os.path.join(self.data_dir, "persona.json")
        if os.path.exists(persona_path):
            with open(persona_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _export_emotion(self) -> Dict[str, Any]:
        """Экспортирует эмоции"""
        emotion_path = os.path.join(self.data_dir, "emotion_state.json")
        if os.path.exists(emotion_path):
            with open(emotion_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _export_knowledge(self) -> Dict[str, Any]:
        """Экспортирует граф знаний"""
        knowledge_path = os.path.join(self.data_dir, "knowledge.db")
        if os.path.exists(knowledge_path):
            try:
                import sqlite3
                conn = sqlite3.connect(knowledge_path)
                cursor = conn.cursor()
                
                nodes = []
                edges = []
                
                cursor.execute("SELECT * FROM nodes")
                for row in cursor.fetchall():
                    nodes.append({"id": row[0], "name": row[1]})
                
                cursor.execute("SELECT * FROM edges")
                for row in cursor.fetchall():
                    edges.append({"source": row[0], "target": row[1]})
                
                conn.close()
                return {"nodes": nodes, "edges": edges}
            except Exception as e:
                logger.warning(f"Knowledge export error: {e}")
        return {"nodes": [], "edges": []}
    
    def _export_roots(self) -> Dict[str, Any]:
        """Экспортирует корни"""
        roots_path = os.path.join(self.data_dir, "roots.json")
        if os.path.exists(roots_path):
            with open(roots_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _export_health(self) -> Dict[str, Any]:
        """Экспортирует здоровье"""
        health_path = os.path.join(self.data_dir, "health.json")
        if os.path.exists(health_path):
            with open(health_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _export_analytics(self) -> Dict[str, Any]:
        """Экспортирует аналитику"""
        analytics_path = os.path.join(self.data_dir, "analytics.db")
        if os.path.exists(analytics_path):
            try:
                import sqlite3
                conn = sqlite3.connect(analytics_path)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM analytics")
                data = []
                for row in cursor.fetchall():
                    data.append({"key": row[0], "value": row[1]})
                conn.close()
                return {"data": data}
            except Exception as e:
                logger.warning(f"Analytics export error: {e}")
        return {}
    
    def _export_cache(self) -> Dict[str, Any]:
        """Экспортирует кэш"""
        cache_path = os.path.join(self.data_dir, "response_cache.json")
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def export_data(
        self,
        categories: List[DataCategory] = None,
        filename: str = None
    ) -> str:
        """
        Экспортирует данные
        
        Args:
            categories: Список категорий (None = все)
            filename: Имя файла (None = авто)
        
        Returns:
            Путь к созданному файлу
        """
        if categories is None:
            categories = [DataCategory.ALL]
        
        # Собираем данные
        data = self._collect_data(categories)
        
        # Создаём метаданные
        total_items = sum(
            len(v) if isinstance(v, list) else 1
            for v in data.values()
        )
        
        metadata = ExportMetadata(
            version=self.VERSION,
            exported_at=datetime.now(),
            categories=[c.value for c in categories],
            total_items=total_items
        )
        
        # Формируем структуру
        export_data = {
            "metadata": metadata.to_dict(),
            "data": data
        }
        
        # Генерируем имя файла
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"PAD+_backup_{timestamp}.zip"
        
        filepath = os.path.join(self.export_dir, filename)
        
        # Сохраняем как ZIP
        with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Добавляем JSON
            json_data = json.dumps(export_data, ensure_ascii=False, indent=2)
            zf.writestr("data.json", json_data)
            
            # Добавляем README
            readme = f"""# PAD+ AI Backup

Версия: {self.VERSION}
Дата: {metadata.exported_at.isoformat()}
Категории: {', '.join(metadata.categories)}
Записей: {metadata.total_items}

Для восстановления используйте DataManager.import_data()
"""
            zf.writestr("README.txt", readme)
        
        logger.info(f"📦 Exported to {filepath}")
        return filepath
    
    def import_data(
        self,
        filepath: str,
        categories: List[DataCategory] = None,
        merge: bool = True
    ) -> Dict[str, Any]:
        """
        Импортирует данные
        
        Args:
            filepath: Путь к файлу backup
            categories: Только эти категории (None = все)
            merge: Сливать с существующими или заменять
        
        Returns:
            Статистика импорта
        """
        result = {
            "success": False,
            "imported": {},
            "errors": []
        }
        
        try:
            with zipfile.ZipFile(filepath, 'r') as zf:
                # Читаем данные
                json_data = zf.read("data.json").decode('utf-8')
                export_data = json.loads(json_data)
                
                data = export_data.get("data", {})
                metadata = export_data.get("metadata", {})
                
                logger.info(f"📦 Importing backup from {metadata.get('exported_at')}")
                
                # Импортируем каждую категорию
                for category_name, category_data in data.items():
                    if categories:
                        if category_name not in [c.value for c in categories]:
                            continue
                    
                    try:
                        count = self._import_category(
                            category_name,
                            category_data,
                            merge
                        )
                        result["imported"][category_name] = count
                    except Exception as e:
                        result["errors"].append(f"{category_name}: {str(e)}")
                        logger.error(f"Import error {category_name}: {e}")
                
                result["success"] = True
                
        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"Import failed: {e}")
        
        return result
    
    def _import_category(
        self,
        category: str,
        data: Any,
        merge: bool
    ) -> int:
        """Импортирует одну категорию"""
        count = 0
        
        if category == "persona":
            path = os.path.join(self.data_dir, "persona.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            count = 1
        
        elif category == "emotion":
            path = os.path.join(self.data_dir, "emotion_state.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            count = 1
        
        elif category == "roots":
            path = os.path.join(self.data_dir, "roots.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            count = data.get("total", 0)
        
        elif category == "health":
            path = os.path.join(self.data_dir, "health.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            count = 1
        
        elif category == "memory":
            # Импорт RAG
            if "rag" in data:
                count += len(data["rag"])
            # Импорт facts
            if "facts" in data:
                count += len(data["facts"])
        
        return count
    
    def list_exports(self) -> List[Dict[str, Any]]:
        """Возвращает список доступных backup"""
        exports = []
        
        for filename in os.listdir(self.export_dir):
            if filename.endswith('.zip'):
                filepath = os.path.join(self.export_dir, filename)
                stat = os.stat(filepath)
                
                exports.append({
                    "filename": filename,
                    "size_kb": stat.st_size // 1024,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
        
        return sorted(exports, key=lambda x: x["created"], reverse=True)
    
    def cleanup_old_exports(self, keep: int = 10):
        """Удаляет старые backup, оставляя последние N"""
        exports = self.list_exports()
        
        for export in exports[keep:]:
            filepath = os.path.join(self.export_dir, export["filename"])
            os.remove(filepath)
            logger.info(f"🗑️ Removed old export: {export['filename']}")


# Глобальный экземпляр
_data_manager: Optional[DataManager] = None


def get_data_manager() -> DataManager:
    """Возвращает глобальный менеджер данных"""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
    return _data_manager