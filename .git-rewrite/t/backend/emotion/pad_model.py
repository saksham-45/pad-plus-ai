"""
PAD+ Эмоциональная модель PAD+ AI

Базовые параметры (PAD):
- Pleasure (Удовольствие): -1 до +1
- Arousal (Возбуждение): -1 до +1
- Dominance (Доминирование): -1 до +1

Дополнительные параметры:
- Любопытство: 0 до 1
- Уверенность: 0 до 1
- Социальная связь: -1 до +1
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import json
import os
import threading


@dataclass
class EmotionState:
    """Состояние эмоций PAD+"""
    
    # Базовые PAD параметры
    pleasure: float = 0.0      # -1 до +1
    arousal: float = 0.0       # -1 до +1
    dominance: float = 0.0     # -1 до +1
    
    # Дополнительные параметры
    curiosity: float = 0.5     # 0 до 1
    confidence: float = 0.5    # 0 до 1
    social_connection: float = 0.0  # -1 до +1
    
    # Метаданные
    updated_at: datetime = field(default_factory=datetime.now)
    trigger: str = "init"
    
    def __post_init__(self):
        """Нормализует значения после инициализации"""
        self._normalize()
    
    def _normalize(self):
        """Нормализует значения в допустимые диапазоны"""
        self.pleasure = max(-1.0, min(1.0, self.pleasure))
        self.arousal = max(-1.0, min(1.0, self.arousal))
        self.dominance = max(-1.0, min(1.0, self.dominance))
        self.curiosity = max(0.0, min(1.0, self.curiosity))
        self.confidence = max(0.0, min(1.0, self.confidence))
        self.social_connection = max(-1.0, min(1.0, self.social_connection))
    
    def to_dict(self) -> dict:
        """Преобразует состояние в словарь"""
        return {
            "удовольствие": round(self.pleasure, 3),
            "возбуждение": round(self.arousal, 3),
            "доминирование": round(self.dominance, 3),
            "любопытство": round(self.curiosity, 3),
            "уверенность": round(self.confidence, 3),
            "социальная_связь": round(self.social_connection, 3),
            "updated_at": self.updated_at.isoformat(),
            "trigger": self.trigger
        }
    
    def get_style(self) -> Dict[str, str]:
        """Возвращает стиль общения на основе эмоций"""
        # Тон
        if self.pleasure > 0.3:
            tone = "friendly"
        elif self.pleasure < -0.3:
            tone = "serious"
        else:
            tone = "neutral"
        
        # Многословность
        if self.arousal > 0.3:
            verbosity = "detailed"
        elif self.arousal < -0.3:
            verbosity = "concise"
        else:
            verbosity = "moderate"
        
        # Эмоциональный цвет
        if self.confidence < 0.3:
            color = "uncertain"
        elif self.confidence > 0.7:
            color = "confident"
        else:
            color = "balanced"
        
        return {
            "tone": tone,
            "verbosity": verbosity,
            "color": color
        }


class PADModel:
    """
    PAD+ Эмоциональная модель
    
    Управляет эмоциональным состоянием цифрового организма.
    Влияет на тон и стиль ответов.
    """
    
    # Скорость затухания эмоций (в секундах)
    DECAY_RATE = 0.001  # Уменьшение в секунду
    DECAY_INTERVAL = 60  # Проверка каждую минуту
    
    def __init__(self, state_file: str = None):
        if state_file is None:
            state_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "emotion_state.json"
            )
        self.state_file = state_file
        self._lock = threading.RLock()
        self._state = self._load_or_create()
        self._start_decay_thread()
    
    def _load_or_create(self) -> EmotionState:
        """Загружает или создаёт состояние эмоций"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return EmotionState(
                    pleasure=data.get("удовольствие", 0.0),
                    arousal=data.get("возбуждение", 0.0),
                    dominance=data.get("доминирование", 0.0),
                    curiosity=data.get("любопытство", 0.5),
                    confidence=data.get("уверенность", 0.5),
                    social_connection=data.get("социальная_связь", 0.0),
                    trigger=data.get("trigger", "loaded")
                )
            except Exception:
                pass
        return EmotionState()
    
    def _save(self):
        """Сохраняет состояние в файл"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self._state.to_dict(), f, ensure_ascii=False, indent=2)
    
    def _start_decay_thread(self):
        """Запускает фоновое затухание эмоций"""
        def decay_loop():
            while True:
                import time
                time.sleep(self.DECAY_INTERVAL)
                self._apply_decay()
        
        thread = threading.Thread(target=decay_loop, daemon=True)
        thread.start()
    
    def _apply_decay(self):
        """Применяет затухание к эмоциям"""
        with self._lock:
            # Затухание к нейтральному состоянию
            decay = self.DECAY_RATE * self.DECAY_INTERVAL
            
            # Pleasure → 0
            if self._state.pleasure > 0:
                self._state.pleasure = max(0, self._state.pleasure - decay)
            else:
                self._state.pleasure = min(0, self._state.pleasure + decay)
            
            # Arousal → 0
            if self._state.arousal > 0:
                self._state.arousal = max(0, self._state.arousal - decay)
            else:
                self._state.arousal = min(0, self._state.arousal + decay)
            
            # Dominance → 0
            if self._state.dominance > 0:
                self._state.dominance = max(0, self._state.dominance - decay)
            else:
                self._state.dominance = min(0, self._state.dominance + decay)
            
            # Curiosity → 0.5
            if self._state.curiosity > 0.5:
                self._state.curiosity = max(0.5, self._state.curiosity - decay)
            else:
                self._state.curiosity = min(0.5, self._state.curiosity + decay)
            
            # Confidence → 0.5
            if self._state.confidence > 0.5:
                self._state.confidence = max(0.5, self._state.confidence - decay)
            else:
                self._state.confidence = min(0.5, self._state.confidence + decay)
            
            self._save()
    
    def get_state(self) -> EmotionState:
        """Возвращает текущее состояние"""
        with self._lock:
            return self._state
    
    def update(self, pleasure: float = None, arousal: float = None,
               dominance: float = None, curiosity: float = None,
               confidence: float = None, social_connection: float = None,
               trigger: str = "update") -> EmotionState:
        """Обновляет эмоциональное состояние"""
        with self._lock:
            if pleasure is not None:
                self._state.pleasure = pleasure
            if arousal is not None:
                self._state.arousal = arousal
            if dominance is not None:
                self._state.dominance = dominance
            if curiosity is not None:
                self._state.curiosity = curiosity
            if confidence is not None:
                self._state.confidence = confidence
            if social_connection is not None:
                self._state.social_connection = social_connection
            
            self._state.trigger = trigger
            self._state.updated_at = datetime.now()
            self._state._normalize()
            
            self._save()
            return self._state
    
    def apply_event(self, event_type: str, intensity: float = 0.1):
        """
        Применяет событие к эмоциям
        
        Args:
            event_type: Тип события (new_knowledge, contradiction, 
                       user_praise, user_criticism, fallback, etc.)
            intensity: Интенсивность воздействия (0.0 - 1.0)
        """
        with self._lock:
            # Определяем влияние события
            effects = {
                "new_knowledge": {
                    "pleasure": 0.1, "curiosity": 0.2, "confidence": 0.05
                },
                "contradiction": {
                    "pleasure": -0.1, "confidence": -0.2, "arousal": 0.1
                },
                "user_praise": {
                    "pleasure": 0.3, "social_connection": 0.2, 
                    "confidence": 0.1
                },
                "user_criticism": {
                    "pleasure": -0.2, "social_connection": -0.1,
                    "confidence": -0.1
                },
                "fallback": {
                    "confidence": -0.1, "curiosity": 0.1
                },
                "self_reflection": {
                    "arousal": -0.1, "curiosity": 0.1
                },
                "new_skill": {
                    "pleasure": 0.2, "confidence": 0.2, "arousal": 0.1
                }
            }
            
            effect = effects.get(event_type, {})
            
            for param, delta in effect.items():
                current = getattr(self._state, param)
                new_value = current + delta * intensity
                setattr(self._state, param, new_value)
            
            self._state.trigger = event_type
            self._state.updated_at = datetime.now()
            self._state._normalize()
            
            self._save()
            return self._state
    
    def get_style(self) -> Dict[str, str]:
        """Возвращает стиль общения"""
        with self._lock:
            return self._state.get_style()


# Глобальный экземпляр
_pad_model: Optional[PADModel] = None


def get_pad_model() -> PADModel:
    """Возвращает глобальную PAD+ модель"""
    global _pad_model
    if _pad_model is None:
        _pad_model = PADModel()
    return _pad_model