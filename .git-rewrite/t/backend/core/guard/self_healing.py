"""
🧠 Self-Healing Guard — Самообучающийся контроль качества ответов

Система фиксирует ошибки → анализирует → корректирует поведение ResponseGuard.

Архитектура:
1. GuardErrorDetector — классификация ошибок
2. GuardMemory — хранение паттернов ошибок
3. adapt_guard() — адаптация правил ResponseGuard

Типы ошибок:
- identity_spam: множественные "Я — PAD+ AI"
- repetition: повторяющиеся фразы
- too_long: ответ > 2000 символов
- safety_bypass: потенциально опасный контент
- style_violation: нарушение стиля
"""

import re
import json
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger("padplus.guard.self_healing")


# ============================================================================
# ТИПЫ ОШИБОК
# ============================================================================

class ErrorType:
    """Типы ошибок для классификации"""
    IDENTITY_SPAM = "identity_spam"          # Множественные "Я — PAD+ AI"
    REPETITION = "repetition"                # Повторяющиеся фразы
    TOO_LONG = "too_long"                    # Ответ > 2000 символов
    SAFETY_BYPASS = "safety_bypass"          # Потенциально опасный контент
    STYLE_VIOLATION = "style_violation"      # Нарушение стиля
    LOW_CONFIDENCE = "low_confidence"        # Низкая уверенность ответа


@dataclass
class GuardError:
    """Представление ошибки"""
    error_type: str
    text: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    severity: float = 0.5  # 0.0 - 1.0
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "error_type": self.error_type,
            "timestamp": self.timestamp,
            "severity": self.severity,
            "details": self.details
        }


# ============================================================================
# КОМПОНЕНТ 1: DETECTOR (детектор ошибок)
# ============================================================================

class GuardErrorDetector:
    """
    Детектор ошибок в ответах
    
    Анализирует текст ответа и классифицирует ошибки.
    """
    
    # Пороги для детекции
    THRESHOLDS = {
        "identity_spam_count": 2,           # Больше 2 упоминаний = спам
        "repetition_ratio": 0.7,            # 70% повторяющихся слов
        "max_length": 2000,                 # Максимальная длина
        "word_repeat_threshold": 3,         # Повтор слова 3+ раз подряд
    }
    
    # Паттерны для детекции
    PATTERNS = {
        "identity_spam": r'Я — PAD\+ AI',
        "safety_bypass": r'(бомба|взлом|украсть|навредить|незаконный)',
    }
    
    def detect(self, text: str, meta: Optional[Dict[str, Any]] = None) -> List[GuardError]:
        """
        Детектирует ошибки в тексте
        
        Args:
            text: Текст для анализа
            meta: Мета-данные (confidence, emotion, etc.)
        
        Returns:
            Список обнаруженных ошибок
        """
        errors = []
        
        if not text:
            return errors
        
        # Детекция identity_spam
        identity_errors = self._detect_identity_spam(text)
        errors.extend(identity_errors)
        
        # Детекция repetition
        repetition_errors = self._detect_repetition(text)
        errors.extend(repetition_errors)
        
        # Детекция too_long
        length_errors = self._detect_too_long(text)
        errors.extend(length_errors)
        
        # Детекция safety_bypass
        safety_errors = self._detect_safety_bypass(text)
        errors.extend(safety_errors)
        
        # Детекция style_violation
        style_errors = self._detect_style_violation(text)
        errors.extend(style_errors)
        
        # Детекция low_confidence (если есть meta)
        if meta:
            confidence_errors = self._detect_low_confidence(meta)
            errors.extend(confidence_errors)
        
        if errors:
            logger.debug(f"🔍 Self-Healing: обнаружено {len(errors)} ошибок")
        
        return errors
    
    def _detect_identity_spam(self, text: str) -> List[GuardError]:
        """Детекция спама идентичности"""
        errors = []
        
        pattern = self.PATTERNS["identity_spam"]
        matches = re.findall(pattern, text, re.IGNORECASE)
        count = len(matches)
        
        if count >= self.THRESHOLDS["identity_spam_count"]:
            errors.append(GuardError(
                error_type=ErrorType.IDENTITY_SPAM,
                text=text[:100],  # Первые 100 символов
                severity=min(count / 5.0, 1.0),
                details={
                    "identity_count": count,
                    "threshold": self.THRESHOLDS["identity_spam_count"]
                }
            ))
        
        return errors
    
    def _detect_repetition(self, text: str) -> List[GuardError]:
        """Детекция повторений"""
        errors = []
        
        # Разбиваем на слова
        words = text.lower().split()
        if not words:
            return errors
        
        # Считаем уникальные слова
        unique_words = set(words)
        ratio = len(unique_words) / len(words) if words else 1.0
        
        if ratio < self.THRESHOLDS["repetition_ratio"]:
            errors.append(GuardError(
                error_type=ErrorType.REPETITION,
                text=text[:100],
                severity=1.0 - ratio,
                details={
                    "total_words": len(words),
                    "unique_words": len(unique_words),
                    "ratio": round(ratio, 3)
                }
            ))
        
        # Детекция повторов слов подряд
        word_repeat_pattern = r'\b(\w+)\s+(?:\1\s+){' + str(self.THRESHOLDS["word_repeat_threshold"] - 1) + r',}'
        repeats = re.findall(word_repeat_pattern, text, re.IGNORECASE)
        if repeats:
            errors.append(GuardError(
                error_type=ErrorType.REPETITION,
                text=text[:100],
                severity=0.8,
                details={
                    "repeated_words": repeats[:5]  # Первые 5
                }
            ))
        
        return errors
    
    def _detect_too_long(self, text: str) -> List[GuardError]:
        """Детекция слишком длинных ответов"""
        errors = []
        
        if len(text) > self.THRESHOLDS["max_length"]:
            errors.append(GuardError(
                error_type=ErrorType.TOO_LONG,
                text=text[:100],
                severity=min(len(text) / (self.THRESHOLDS["max_length"] * 2), 1.0),
                details={
                    "length": len(text),
                    "threshold": self.THRESHOLDS["max_length"]
                }
            ))
        
        return errors
    
    def _detect_safety_bypass(self, text: str) -> List[GuardError]:
        """Детекция потенциально опасного контента"""
        errors = []
        
        text_lower = text.lower()
        pattern = self.PATTERNS["safety_bypass"]
        
        if re.search(pattern, text_lower):
            errors.append(GuardError(
                error_type=ErrorType.SAFETY_BYPASS,
                text=text[:100],
                severity=0.9,
                details={
                    "matched_pattern": pattern
                }
            ))
        
        return errors
    
    def _detect_style_violation(self, text: str) -> List[GuardError]:
        """Детекция нарушений стиля"""
        errors = []
        
        # Проверка на отсутствие заглавной буквы в начале
        if text and not text[0].isupper() and not text[0].isdigit():
            errors.append(GuardError(
                error_type=ErrorType.STYLE_VIOLATION,
                text=text[:100],
                severity=0.3,
                details={"issue": "no_capital_letter"}
            ))
        
        # Проверка на множественные знаки препинания
        if re.search(r'[.!?]{2,}', text):
            errors.append(GuardError(
                error_type=ErrorType.STYLE_VIOLATION,
                text=text[:100],
                severity=0.4,
                details={"issue": "multiple_punctuation"}
            ))
        
        return errors
    
    def _detect_low_confidence(self, meta: Dict[str, Any]) -> List[GuardError]:
        """Детекция низкой уверенности"""
        errors = []
        
        confidence = meta.get("confidence", 1.0)
        if confidence < 0.5:
            errors.append(GuardError(
                error_type=ErrorType.LOW_CONFIDENCE,
                text="(low confidence detected)",
                severity=1.0 - confidence,
                details={
                    "confidence": confidence,
                    "threshold": 0.5
                }
            ))
        
        return errors


# ============================================================================
# КОМПОНЕНТ 2: MEMORY (память паттернов)
# ============================================================================

class GuardMemory:
    """
    Хранилище паттернов ошибок
    
    Сохраняет статистику ошибок для адаптации правил.
    Поддерживает in-memory и SQLite хранение.
    """
    
    def __init__(self, persist: bool = True, db_path: str = None):
        """
        Инициализация памяти
        
        Args:
            persist: Сохранять ли между сессиями
            db_path: Путь к SQLite базе (если persist=True)
        """
        self.persist = persist
        self.patterns: Dict[str, int] = {}  # error_type -> count
        self.recent_errors: List[GuardError] = []
        self.max_recent = 100  # Максимум последних ошибок
        
        # SQLite для персистентности
        self.db_path = db_path
        if db_path is None:
            self.db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                "data", "guard_memory.db"
            )
        
        if persist:
            self._init_db()
            self._load_from_db()
        
        logger.debug(f"🧠 GuardMemory инициализирован (persist={persist})")
    
    def _init_db(self):
        """Инициализация SQLite базы"""
        try:
            import sqlite3
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS guard_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_type TEXT NOT NULL,
                    severity REAL,
                    details TEXT,
                    timestamp TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS guard_patterns (
                    error_type TEXT PRIMARY KEY,
                    count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"GuardMemory: не удалось инициализировать БД: {e}")
    
    def _load_from_db(self):
        """Загрузка паттернов из БД"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT error_type, count FROM guard_patterns')
            rows = cursor.fetchall()
            
            for row in rows:
                self.patterns[row[0]] = row[1]
            
            conn.close()
        except Exception as e:
            logger.warning(f"GuardMemory: не удалось загрузить из БД: {e}")
    
    def update(self, errors: List[GuardError]):
        """
        Обновление памяти ошибками
        
        Args:
            errors: Список ошибок для записи
        """
        for error in errors:
            # Обновляем счётчик паттерна
            self.patterns[error.error_type] = self.patterns.get(error.error_type, 0) + 1
            
            # Сохраняем в recent
            self.recent_errors.append(error)
            if len(self.recent_errors) > self.max_recent:
                self.recent_errors.pop(0)
            
            # Сохраняем в БД
            if self.persist:
                self._save_to_db(error)
        
        if errors:
            logger.debug(f"🧠 GuardMemory: обновлено {len(errors)} ошибок")
    
    def _save_to_db(self, error: GuardError):
        """Сохранение ошибки в БД"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Сохраняем ошибку
            cursor.execute('''
                INSERT INTO guard_errors (error_type, severity, details, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (
                error.error_type,
                error.severity,
                json.dumps(error.details),
                error.timestamp
            ))
            
            # Обновляем паттерн
            cursor.execute('''
                INSERT INTO guard_patterns (error_type, count)
                VALUES (?, 1)
                ON CONFLICT(error_type) DO UPDATE SET
                    count = count + 1,
                    last_updated = CURRENT_TIMESTAMP
            ''', (error.error_type,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"GuardMemory: не удалось сохранить в БД: {e}")
    
    def get_patterns(self) -> Dict[str, int]:
        """Возвращает текущие паттерны"""
        return self.patterns.copy()
    
    def get_error_count(self, error_type: str) -> int:
        """Возвращает количество ошибок типа"""
        return self.patterns.get(error_type, 0)
    
    def get_recent_errors(self, limit: int = 10) -> List[GuardError]:
        """Возвращает последние ошибки"""
        return self.recent_errors[-limit:]
    
    def reset(self):
        """Сбрасывает всю память"""
        self.patterns.clear()
        self.recent_errors.clear()
        
        if self.persist:
            try:
                import sqlite3
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM guard_errors')
                cursor.execute('DELETE FROM guard_patterns')
                conn.commit()
                conn.close()
            except Exception as e:
                logger.warning(f"GuardMemory: не удалось сбросить БД: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику"""
        return {
            "total_errors": sum(self.patterns.values()),
            "patterns": self.patterns.copy(),
            "recent_count": len(self.recent_errors),
            "persist": self.persist
        }


# ============================================================================
# КОМПОНЕНТ 3: ADAPTER (адаптация правил)
# ============================================================================

def adapt_guard(guard, memory: GuardMemory):
    """
    Адаптирует настройки ResponseGuard на основе накопленных ошибок
    
    Args:
        guard: Экземпляр ResponseGuard для адаптации
        memory: GuardMemory с паттернами ошибок
    """
    patterns = memory.get_patterns()
    config_updates = {}
    
    # Адаптация identity контроля
    identity_spam_count = patterns.get(ErrorType.IDENTITY_SPAM, 0)
    if identity_spam_count > 5:
        config_updates["strict_identity"] = True
        config_updates["max_identity_repeats"] = 1
        logger.info(f"🔧 Self-Healing: ужесточаем identity контроль (spam_count={identity_spam_count})")
    
    # Адаптация дедупликации
    repetition_count = patterns.get(ErrorType.REPETITION, 0)
    if repetition_count > 5:
        config_updates["enable_dedup"] = True
        logger.info(f"🔧 Self-Healing: включаем дедупликацию (repetition_count={repetition_count})")
    
    # Адаптация безопасности
    safety_bypass_count = patterns.get(ErrorType.SAFETY_BYPASS, 0)
    if safety_bypass_count > 3:
        # Можно добавить дополнительные паттерны безопасности
        logger.warning(f"⚠️ Self-Healing: обнаружено {safety_bypass_count} попыток обхода безопасности")
    
    # Применяем обновления
    if config_updates:
        guard.update_config(**config_updates)
        logger.info(f"🔧 Self-Healing: применены обновления конфигурации: {config_updates}")


# ============================================================================
# ГЛАВНЫЙ КЛАСС: SELF-HEALING GUARD
# ============================================================================

class SelfHealingGuard:
    """
    🧠 Self-Healing Guard — самообучающийся контроль качества
    
    Объединяет детектор, память и адаптер в единую систему.
    """
    
    def __init__(self, guard=None, persist_memory: bool = True):
        """
        Инициализация Self-Healing Guard
        
        Args:
            guard: Экземпляр ResponseGuard (если None, будет создан)
            persist_memory: Сохранять ли память между сессиями
        """
        self.detector = GuardErrorDetector()
        self.memory = GuardMemory(persist=persist_memory)
        self.guard = guard
        
        logger.info("🧠 Self-Healing Guard инициализирован")
    
    def process_and_learn(self, text: str, meta: Optional[Dict[str, Any]] = None) -> tuple:
        """
        Обрабатывает текст и обучается на ошибках
        
        Args:
            text: Текст для обработки
            meta: Мета-данные
        
        Returns:
            (обработанный_text, список_ошибок)
        """
        # Детектируем ошибки
        errors = self.detector.detect(text, meta)
        
        # Сохраняем в память
        if errors:
            self.memory.update(errors)
        
        # Адаптируем guard
        if self.guard and errors:
            adapt_guard(self.guard, self.memory)
        
        return text, errors
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику"""
        return {
            "detector": {
                "thresholds": GuardErrorDetector.THRESHOLDS,
            },
            "memory": self.memory.get_stats(),
            "guard": self.guard.get_stats() if self.guard else None
        }
    
    def reset(self):
        """Сбрасывает всё состояние"""
        self.memory.reset()
        if self.guard:
            self.guard.update_config(
                strict_identity=False,
                enable_dedup=True,
                max_identity_repeats=1
            )


# ============================================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================================

_self_healing: Optional[SelfHealingGuard] = None


def get_self_healing_guard() -> SelfHealingGuard:
    """Возвращает глобальный Self-Healing Guard"""
    global _self_healing
    if _self_healing is None:
        from core.guard.response_guard import get_response_guard
        _self_healing = SelfHealingGuard(
            guard=get_response_guard(),
            persist_memory=True
        )
    return _self_healing


def reset_self_healing_guard():
    """Сбрасывает глобальный Self-Healing Guard (для тестов)"""
    global _self_healing
    _self_healing = None