"""
Импульс (seed) — искра сознания NeuroMind AI

Это первый вопрос, который система задает себе при инициализации.
Он становится основой для всего последующего познания.
"""

from dataclasses import dataclass
from typing import Optional
import json
import os
from datetime import datetime


@dataclass
class Impulse:
    """Импульс сознания - точка зарождения"""
    
    question: str = "Что я могу понять?"
    layer: str = "roots"  # Корни - неизменяемый слой
    depth: int = 0
    source: str = "impulse"
    immutable: bool = True
    created_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """Преобразует импульс в словарь для сохранения"""
        return {
            "question": self.question,
            "layer": self.layer,
            "depth": self.depth,
            "source": self.source,
            "immutable": self.immutable,
            "created_at": self.created_at
        }
    
    def to_json(self) -> str:
        """Преобразует импульс в JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class ImpulseManager:
    """Менеджер импульса - управляет инициализацией и защитой"""
    
    DATA_DIR = "data"
    IMPULSE_FILE = "impulse.json"
    
    def __init__(self, base_path: str = None):
        if base_path is None:
            # Определяем базовый путь относительно этого файла
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_path = base_path
        self.data_dir = os.path.join(base_path, self.DATA_DIR)
        self.impulse_path = os.path.join(self.data_dir, self.IMPULSE_FILE)
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Создает директорию data если её нет"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def exists(self) -> bool:
        """Проверяет, существует ли уже импульс"""
        return os.path.exists(self.impulse_path)
    
    def start(self) -> dict:
        """
        Запускает импульс (идемпотентный).
        Если импульс уже существует - возвращает существующий.
        """
        if self.exists():
            return self.load()
        
        impulse = Impulse()
        self._save(impulse)
        print(f"🧠 Импульс запущен: {impulse.question}")
        return impulse.to_dict()
    
    def load(self) -> dict:
        """Загружает существующий импульс"""
        if not self.exists():
            raise FileNotFoundError("Импульс не найден")
        
        with open(self.impulse_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"🧠 Импульс уже инициализирован: {data['question']}")
        return data
    
    def _save(self, impulse: Impulse):
        """Сохраняет импульс в файл"""
        with open(self.impulse_path, 'w', encoding='utf-8') as f:
            f.write(impulse.to_json())
    
    def is_initialized(self) -> bool:
        """Проверяет, инициализирован ли импульс"""
        return self.exists()


# Глобальный экземпляр менеджера
_manager: Optional[ImpulseManager] = None


def get_manager() -> ImpulseManager:
    """Возвращает глобальный менеджер импульса"""
    global _manager
    if _manager is None:
        _manager = ImpulseManager()
    return _manager


def start_impulse() -> dict:
    """Запускает импульс (главная функция)"""
    return get_manager().start()


def is_impulse_initialized() -> bool:
    """Проверяет, инициализирован ли импульс"""
    return get_manager().is_initialized()


if __name__ == "__main__":
    # Запуск импульса напрямую
    result = start_impulse()
    print(f"\n📄 Импульс сохранён:")
    print(json.dumps(result, ensure_ascii=False, indent=2))