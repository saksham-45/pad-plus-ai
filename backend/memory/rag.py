"""
🧠 RAG — Retrieval-Augmented Generation v3.0

Продвинутые возможности:
- LLM-суммаризация (через GigaChat)
- Классификация тем диалогов
- Извлечение сущностей и связей
- Гибридный поиск с умным ранжированием
"""

import os
import re
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
import math

# Создаём логгер в начале
logger = logging.getLogger("PAD+.rag")



# Sentence Transformers для эмбеддингов (ленивый импорт)
_sentence_transformer_model = None
_sentence_transformers_available = None


def _get_sentence_transformer():
    global _sentence_transformer_model, _sentence_transformers_available
    if _sentence_transformers_available is not None:
        return _sentence_transformer_model

    try:
        from sentence_transformers import SentenceTransformer
        _sentence_transformer_model = SentenceTransformer
        _sentence_transformers_available = True
        logger.info("✅ Sentence Transformers доступен")
    except Exception as e:
        logger.warning(f"⚠️ Sentence Transformers недоступен ({e})")
        _sentence_transformer_model = None
        _sentence_transformers_available = False

    return _sentence_transformer_model

# Константы
CONTEXT_WINDOW = 5
MAX_DIALOG_LENGTH = 500
RECENCY_WEIGHT = 0.3
RELEVANCE_WEIGHT = 0.7


# === КЛАССИФИКАЦИЯ ТЕМ ===

TOPIC_KEYWORDS = {
    "техническое": [
        "код", "программирование", "алгоритм", "функция", "переменная",
        "python", "javascript", "api", "база данных", "сервер",
        "нейронная сеть", "модель", "обучение", "tensorflow", "pytorch",
        "код", "скрипт", "баг", "ошибка", "отладка", "debug"
    ],
    "философское": [
        "смысл", "существование", "сознание", "реальность", "истина",
        "знание", "вера", "этика", "мораль", "добро", "зло",
        "свобода", "воля", "разум", "душа", "бытие"
    ],
    "личное": [
        "я", "мой", "мне", "меня", "себя", "чувствую", "думаю",
        "хочу", "могу", "умею", "люблю", "ненавижу", "боюсь",
        "мечтаю", "надеюсь", "планирую", "работаю"
    ],
    "образовательное": [
        "объясни", "расскажи", "научи", "как работает", "что такое",
        "пример", "урок", "курс", "изучить", "понять", "выучить",
        "научиться", "разобраться", "узнать"
    ],
    "творческое": [
        "придумай", "создай", "напиши", "сочини", "идея", "концепция",
        "дизайн", "история", "рассказ", "стих", "картина", "музыка",
        "творчество", "воображение", "фантазия"
    ],
    "аналитическое": [
        "проанализируй", "сравни", "оцени", "вывод", "причина",
        "следствие", "закономерность", "статистика", "данные",
        "график", "отчёт", "исследование", "эксперимент"
    ],
    "бытовое": [
        "погода", "еда", "сон", "отдых", "покупки", "деньги",
        "время", "расписание", "планы", "семья", "друзья",
        "дом", "работа", "отпуск", "праздник"
    ]
}


def classify_topic(text: str) -> Tuple[str, float]:
    """
    Классифицирует тему диалога
    
    Returns:
        (topic_name, confidence)
    """
    text_lower = text.lower()
    
    scores = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            # Нормализуем по количеству ключевых слов
            scores[topic] = score / len(keywords)
    
    if not scores:
        return ("общее", 0.5)
    
    # Находим лучшую тему
    best_topic = max(scores, key=scores.get)
    confidence = min(scores[best_topic] * 5, 1.0)  # Масштабируем
    
    return (best_topic, round(confidence, 2))


def classify_dialog(user_message: str, ai_response: str) -> Dict[str, Any]:
    """
    Полная классификация диалога
    
    Returns:
        {
            "primary_topic": str,
            "confidence": float,
            "all_topics": dict,
            "sentiment": str
        }
    """
    combined = f"{user_message} {ai_response}"
    
    # Основная тема
    primary_topic, confidence = classify_topic(combined)
    
    # Все темы с scores
    all_topics = {}
    text_lower = combined.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            all_topics[topic] = round(score / len(keywords) * 5, 2)
    
    # Сентимент (простая эвристика)
    positive_words = ["хорошо", "отлично", "прекрасно", "спасибо", "благодарю",
                      "рад", "доволен", "люблю", "нравится", "удачно"]
    negative_words = ["плохо", "ужасно", "грустно", "злюсь", "ненавижу",
                      "проблема", "ошибка", "не работает", "сложно"]
    
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)
    
    if pos_count > neg_count:
        sentiment = "positive"
    elif neg_count > pos_count:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    return {
        "primary_topic": primary_topic,
        "confidence": confidence,
        "all_topics": all_topics,
        "sentiment": sentiment
    }


# === ИЗВЛЕЧЕНИЕ СУЩНОСТЕЙ ===

ENTITY_PATTERNS = {
    "person": [
        r'\b([А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+)\b',  # Иван Петров
        r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',  # John Smith
    ],
    "technology": [
        r'\b(Python|JavaScript|TypeScript|React|Vue|Angular|Node\.js|Django|FastAPI|TensorFlow|PyTorch|OpenAI|GigaChat|ChatGPT)\b',
        r'\b([A-Z][a-z]+(?:JS|API|DB|ML|AI|LLM))\b',  # ReactJS, RESTAPI
    ],
    "concept": [
        r'\b(нейросеть|искусственный интеллект|машинное обучение|глубокое обучение)\b',
        r'\b(алгоритм|структура данных|паттерн|архитектура|фреймворк)\b',
    ],
    "location": [
        r'\b(в [А-ЯЁ][а-яё]+)\b',  # в Москве
        r'\b(из [А-ЯЁ][а-яё]+)\b',  # из России
    ],
    "time": [
        r'\b(\d{1,2}[:.]\d{2})\b',  # время
        r'\b(\d{1,2} \w+ч\b)',  # 5 часов
        r'\b(сегодня|завтра|вчера|потом|раньше|позже)\b',
    ],
    "number": [
        r'\b(\d+(?:[.,]\d+)?)\b',
    ]
}


def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Извлекает сущности из текста
    
    Returns:
        [{"type": str, "value": str, "confidence": float}, ...]
    """
    entities = []
    
    for entity_type, patterns in ENTITY_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value = match.group(1) if match.lastindex else match.group(0)
                # Проверяем на дубликаты
                if not any(e['value'].lower() == value.lower() for e in entities):
                    entities.append({
                        "type": entity_type,
                        "value": value,
                        "confidence": 0.7 if entity_type in ["technology", "concept"] else 0.5
                    })
    
    return entities[:20]  # Максимум 20 сущностей


def extract_relations(user_message: str, ai_response: str) -> List[Dict[str, Any]]:
    """
    Извлекает связи между сущностями
    
    Returns:
        [{"source": str, "relation": str, "target": str}, ...]
    """
    relations = []
    combined = f"{user_message} {ai_response}"
    
    # Паттерны связей
    relation_patterns = [
        # "X это Y"
        (r'(\w+)\s+(?:это|является|представляет собой)\s+(\w+)', "is_a"),
        # "X использует Y"
        (r'(\w+)\s+(?:использует|применяет|используют для)\s+(\w+)', "uses"),
        # "X связан с Y"
        (r'(\w+)\s+(?:связан|связано|связаны)\s+с\s+(\w+)', "related_to"),
        # "X часть Y"
        (r'(\w+)\s+(?:часть|частью|входит в)\s+(\w+)', "part_of"),
        # "X содержит Y"
        (r'(\w+)\s+(?:содержит|включает|имеет)\s+(\w+)', "contains"),
    ]
    
    for pattern, relation_type in relation_patterns:
        matches = re.finditer(pattern, combined, re.IGNORECASE)
        for match in matches:
            source = match.group(1)
            target = match.group(2)
            
            # Фильтруем короткие слова
            if len(source) > 2 and len(target) > 2:
                relations.append({
                    "source": source,
                    "relation": relation_type,
                    "target": target,
                    "confidence": 0.6
                })
    
    return relations[:10]


# === СУММАРИЗАЦИЯ ===

def extract_keywords(text: str) -> List[str]:
    """Извлекает ключевые слова из текста"""
    stop_words = {
        'и', 'в', 'на', 'не', 'что', 'как', 'это', 'то', 'а', 'но', 'или',
        'с', 'по', 'за', 'из', 'от', 'до', 'для', 'к', 'у', 'о', 'об',
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'can', 'to', 'of',
        'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
        'я', 'ты', 'он', 'она', 'оно', 'мы', 'вы', 'они', 'меня', 'тебя',
        'его', 'её', 'нас', 'вас', 'их', 'этот', 'эта', 'эти', 'тот'
    }
    
    words = re.findall(r'\b[а-яёa-z]{3,}\b', text.lower())
    keywords = [w for w in words if w not in stop_words]
    
    seen = set()
    result = []
    for w in keywords:
        if w not in seen:
            seen.add(w)
            result.append(w)
    
    return result[:10]


def calculate_keyword_score(query_keywords: List[str], 
                            doc_keywords: List[str]) -> float:
    """Вычисляет score совпадения ключевых слов"""
    if not query_keywords or not doc_keywords:
        return 0.0
    
    query_set = set(query_keywords)
    doc_set = set(doc_keywords)
    
    intersection = len(query_set & doc_set)
    union = len(query_set | doc_set)
    
    if union == 0:
        return 0.0
    
    return intersection / union


def calculate_recency_score(timestamp: str, 
                            now: datetime = None) -> float:
    """Вычисляет score давности"""
    if not timestamp:
        return 0.5
    
    try:
        doc_time = datetime.fromisoformat(timestamp)
        now = now or datetime.now()
        age_days = (now - doc_time).days
        score = math.exp(-age_days / 7.0)
        return max(0.1, min(1.0, score))
    except Exception:
        return 0.5


def summarize_text_simple(text: str, max_length: int = 200) -> str:
    """Простое суммаризирование (обрезание)"""
    if len(text) <= max_length:
        return text
    
    shortened = text[:max_length]
    last_dot = shortened.rfind('.')
    last_exclaim = shortened.rfind('!')
    last_question = shortened.rfind('?')
    last_sentence = max(last_dot, last_exclaim, last_question)
    
    if last_sentence > max_length * 0.5:
        return shortened[:last_sentence + 1] + ' [...]'
    else:
        last_space = shortened.rfind(' ')
        if last_space > 0:
            return shortened[:last_space] + ' [...]'
        return shortened + ' [...]'


async def summarize_text_llm(text: str, max_length: int = 200) -> str:
    """
    LLM-суммаризация текста через LLMService
    
    Использует модель для создания краткого содержания
    """
    if len(text) <= max_length:
        return text
    
    try:
        # Импортируем GigaChat
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from llm.gigachat import gigachat
        
        if not gigachat.enabled:
            logger.debug("GigaChat недоступен, используем простое суммаризирование")
            return summarize_text_simple(text, max_length)
        
        # Формируем промпт для суммаризации
        prompt = f"""Сократи следующий текст до {max_length} символов, сохраняя главное содержание:

{text[:1000]}

Ответь только сокращённым текстом, без пояснений."""

        # Генерируем суммаризацию
        summary = await gigachat.generate(prompt, "")
        
        # Если результат слишком длинный, обрезаем
        if len(summary) > max_length + 50:
            return summarize_text_simple(summary, max_length)
        
        logger.info(f"🤖 LLM-суммаризация: {len(text)} -> {len(summary)} символов")
        return summary
        
    except Exception as e:
        logger.warning(f"Ошибка LLM-суммаризации: {e}")
        return summarize_text_simple(text, max_length)


def summarize_text_sync(text: str, max_length: int = 200) -> str:
    """Синхронная версия суммаризации (без LLM)"""
    return summarize_text_simple(text, max_length)


class RAGMemory:
    """
    🧠 RAG Memory v3.0 — продвинутая семантическая память
    
    - LLM-суммаризация (опционально)
    - Классификация тем диалогов
    - Извлечение сущностей и связей
    - Гибридный поиск с умным ранжированием
    """
    
    def __init__(self, persist_dir: str = None, use_llm_summarization: bool = False):
        logger.info(f"Инициализация RAG Memory v3.0 (PostgreSQL)")
        self.use_llm_summarization = use_llm_summarization
        self.conn = None
        self.cursor = None
        self._keywords_cache = {}
        self._topic_stats = {}
        self._lock = threading.Lock() if 'threading' in dir() else None

        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            logger.warning("DATABASE_URL не настроен, RAG работает без БД")
            return

        try:
            import psycopg2
            self.conn = psycopg2.connect(db_url, connect_timeout=3)
            self.cursor = self.conn.cursor()
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS rag_dialogs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_message TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    summary TEXT,
                    keywords TEXT[],
                    topic TEXT DEFAULT 'общее',
                    topic_confidence FLOAT DEFAULT 0.5,
                    sentiment TEXT DEFAULT 'neutral',
                    entities JSONB DEFAULT '[]',
                    relations JSONB DEFAULT '[]',
                    metadata JSONB DEFAULT '{}',
                    user_id UUID,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            
            # Создание индексов для производительности
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rag_dialogs_user_id ON rag_dialogs(user_id)
            """)
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rag_dialogs_topic ON rag_dialogs(topic)
            """)
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rag_dialogs_created_at ON rag_dialogs(created_at)
            """)
            
            self.conn.commit()
            logger.info("✅ RAG Memory PostgreSQL инициализирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации PostgreSQL: {e}")
            # Fallback: продолжаем старт без RAG памяти
            logger.warning("⚠️ RAG Memory инициализация не удалась, но backend будет запущен без RAG")
            self.conn = None
            self.cursor = None
        
        self._keywords_cache: Dict[str, List[str]] = {}
    
    def add_dialog(
        self,
        user_message: str,
        ai_response: str,
        metadata: Dict[str, Any] = None,
        user_id: Optional[str] = None  # === ФАЗА 2: Персонализация ===
    ) -> str:
        """Добавляет диалог в память с анализом"""
        import uuid
        import psycopg2
        from psycopg2.extras import Json
        
        doc_id = str(uuid.uuid4())

        # Суммаризируем (простая версия, без async)
        user_summary = summarize_text_sync(user_message, MAX_DIALOG_LENGTH)
        ai_summary = summarize_text_sync(ai_response, MAX_DIALOG_LENGTH)

        # Извлекаем ключевые слова
        combined_text = f"{user_message} {ai_response}"
        keywords = extract_keywords(combined_text)

        # Классифицируем тему
        topic_info = classify_dialog(user_message, ai_response)

        # Извлекаем сущности и связи
        entities = extract_entities(combined_text)
        relations = extract_relations(user_message, ai_response)

        # Метаданные
        meta = metadata or {}
        meta.update({
            "user_message": user_summary,
            "ai_response": ai_summary,
            "user_full": user_message[:1000],
            "ai_full": ai_response[:1000],
            "timestamp": datetime.now().isoformat(),
            "type": "dialog",
            "keywords": ",".join(keywords),
            "is_summarized": len(user_message) > MAX_DIALOG_LENGTH or
                            len(ai_response) > MAX_DIALOG_LENGTH,
            # Новые поля
            "topic": topic_info["primary_topic"],
            "topic_confidence": topic_info["confidence"],
            "sentiment": topic_info["sentiment"],
            "entities": json.dumps(entities, ensure_ascii=False),
            "relations": json.dumps(relations, ensure_ascii=False),
            # === ФАЗА 2: Персонализация ===
            "user_id": user_id  # None для общих записей
        })

        # Добавляем в PostgreSQL
        try:
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                raise RuntimeError("❌ DATABASE_URL не настроен! Добавьте в .env")
            
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO rag_dialogs (id, user_message, ai_response, summary, keywords, topic, topic_confidence, sentiment, entities, relations, metadata, user_id, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())",
                (
                    doc_id,
                    user_summary,
                    ai_summary,
                    f"Вопрос: {user_summary}\nОтвет: {ai_summary}",
                    keywords,
                    topic_info["primary_topic"],
                    topic_info["confidence"],
                    topic_info["sentiment"],
                    Json(entities),
                    Json(relations),
                    Json(meta),
                    user_id
                )
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления диалога в PostgreSQL: {e}")
            raise

        self._keywords_cache[doc_id] = keywords

        logger.info(
            f"📝 Диалог добавлен: {doc_id[:8]}... "
            f"(тема: {topic_info['primary_topic']}, "
            f"сущностей: {len(entities)}, "
            f"связей: {len(relations)}, "
            f"user_id: {user_id})"
        )
        return doc_id
    
    async def add_dialog_async(
        self, 
        user_message: str, 
        ai_response: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Добавляет диалог с LLM-суммаризацией"""
        import uuid
        import psycopg2
        from psycopg2.extras import Json
        
        doc_id = str(uuid.uuid4())
        
        # LLM-суммаризация
        if self.use_llm_summarization:
            user_summary = await summarize_text_llm(user_message, MAX_DIALOG_LENGTH)
            ai_summary = await summarize_text_llm(ai_response, MAX_DIALOG_LENGTH)
        else:
            user_summary = summarize_text_sync(user_message, MAX_DIALOG_LENGTH)
            ai_summary = summarize_text_sync(ai_response, MAX_DIALOG_LENGTH)
        
        # Остальное как в синхронной версии
        combined_text = f"{user_message} {ai_response}"
        keywords = extract_keywords(combined_text)
        topic_info = classify_dialog(user_message, ai_response)
        entities = extract_entities(combined_text)
        relations = extract_relations(user_message, ai_response)
        
        meta = metadata or {}
        meta.update({
            "user_message": user_summary,
            "ai_response": ai_summary,
            "user_full": user_message[:1000],
            "ai_full": ai_response[:1000],
            "timestamp": datetime.now().isoformat(),
            "type": "dialog",
            "keywords": ",".join(keywords),
            "is_summarized": len(user_message) > MAX_DIALOG_LENGTH or 
                            len(ai_response) > MAX_DIALOG_LENGTH,
            "topic": topic_info["primary_topic"],
            "topic_confidence": topic_info["confidence"],
            "sentiment": topic_info["sentiment"],
            "entities": json.dumps(entities, ensure_ascii=False),
            "relations": json.dumps(relations, ensure_ascii=False)
        })
        
        # Добавляем в PostgreSQL
        try:
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                raise RuntimeError("❌ DATABASE_URL не настроен! Добавьте в .env")
            
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO rag_dialogs (id, user_message, ai_response, summary, keywords, topic, topic_confidence, sentiment, entities, relations, metadata, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())",
                (
                    doc_id,
                    user_summary,
                    ai_summary,
                    f"Вопрос: {user_summary}\nОтвет: {ai_summary}",
                    keywords,
                    topic_info["primary_topic"],
                    topic_info["confidence"],
                    topic_info["sentiment"],
                    Json(entities),
                    Json(relations),
                    Json(meta)
                )
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления диалога в PostgreSQL: {e}")
            raise
        
        self._keywords_cache[doc_id] = keywords
        
        return doc_id
    
    def hybrid_search(
        self,
        query: str,
        n_results: int = CONTEXT_WINDOW,
        use_keywords: bool = True,
        use_recency: bool = True,
        topic_filter: str = None,
        user_id: Optional[str] = None  # === ФАЗА 2: Персонализация ===
    ) -> List[Dict[str, Any]]:
        """
        Гибридный поиск с фильтрацией по темам и user_id

        Args:
            query: Поисковый запрос
            n_results: Количество результатов
            use_keywords: Использовать ключевые слова
            use_recency: Использовать давность
            topic_filter: Фильтр по теме (опционально)
            user_id: ID пользователя для персонализации (None для общего поиска)

        Returns:
            Отранжированный список диалогов
        """
        try:
            import psycopg2
            from psycopg2.extras import Json
            
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                raise RuntimeError("❌ DATABASE_URL не настроен! Добавьте в .env")
            
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Формируем SQL запрос с фильтрацией
            sql_parts = ["SELECT id, user_message, ai_response, summary, metadata, created_at FROM rag_dialogs WHERE 1=1"]
            params = []
            
            # Фильтр по теме
            if topic_filter:
                sql_parts.append("AND topic = %s")
                params.append(topic_filter)
            
            # Фильтр по user_id
            if user_id:
                sql_parts.append("AND (user_id = %s OR user_id IS NULL)")
                params.append(user_id)
            
            # Поиск по тексту (через ключевые слова, т.к. plainto_tsquery с русским не работает)
            if query.strip():
                keywords = list(dict.fromkeys(kw for kw in extract_keywords(query) if len(kw) >= 3))
                if keywords:
                    like_patterns = [f'%{kw}%' for kw in keywords]
                    sql_parts.append(
                        "AND ("
                        "user_message ILIKE ANY(%s) OR "
                        "ai_response ILIKE ANY(%s) OR "
                        "summary ILIKE ANY(%s) OR "
                        "topic ILIKE ANY(%s)"
                        ")"
                    )
                    params.extend([like_patterns, like_patterns, like_patterns, like_patterns])
                else:
                    sql_parts.append(
                        "AND (user_message ILIKE %s OR ai_response ILIKE %s OR summary ILIKE %s OR topic ILIKE %s)"
                    )
                    params.extend([f'%{query}%'] * 4)
            
            # Сортировка по времени и лимит
            sql_parts.append("ORDER BY created_at DESC LIMIT %s")
            params.append(n_results)
            
            sql = " ".join(sql_parts)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            ranked_results = []
            now = datetime.now()
            
            for row in rows:
                doc_id = row[0]
                user_message = row[1]
                ai_response = row[2]
                summary = row[3]
                meta = row[4] if isinstance(row[4], dict) else json.loads(row[4]) if row[4] else {}
                created_at = row[5].isoformat() if row[5] else datetime.now().isoformat()
                
                # Рассчитываем scores
                query_keywords = extract_keywords(query) if use_keywords else []
                keyword_score = 0.0
                if use_keywords and query_keywords:
                    doc_keywords_str = meta.get('keywords', '')
                    doc_keywords = doc_keywords_str.split(',') if doc_keywords_str else []
                    keyword_score = calculate_keyword_score(query_keywords, doc_keywords)
                
                recency_score = 0.5
                if use_recency:
                    recency_score = calculate_recency_score(created_at, now)
                
                # Базовый score
                semantic_score = 0.7
                
                relevance = semantic_score * 0.7 + keyword_score * 0.3
                combined_score = relevance * RELEVANCE_WEIGHT + recency_score * RECENCY_WEIGHT
                
                # Парсим сущности и связи
                entities = []
                relations = []
                try:
                    entities_json = meta.get('entities', '[]')
                    entities = json.loads(entities_json) if entities_json else []
                    relations_json = meta.get('relations', '[]')
                    relations = json.loads(relations_json) if relations_json else []
                except Exception as e:
                    logger.warning(f"{__name__} error: {e}")
                
                ranked_results.append({
                    "id": doc_id,
                    "document": f"Вопрос: {user_message}\nОтвет: {ai_response}",
                    "metadata": meta,
                    "semantic_score": round(semantic_score, 3),
                    "keyword_score": round(keyword_score, 3),
                    "recency_score": round(recency_score, 3),
                    "combined_score": round(combined_score, 3),
                    "similarity": round(combined_score, 3),
                    # Новые поля
                    "topic": meta.get('topic', 'общее'),
                    "topic_confidence": meta.get('topic_confidence', 0.5),
                    "sentiment": meta.get('sentiment', 'neutral'),
                    "entities": entities,
                    "relations": relations
                })
            
            # Сортируем по combined_score
            ranked_results.sort(key=lambda x: x['combined_score'], reverse=True)
            
            return ranked_results
            
        except Exception as e:
            logger.error(f"❌ Ошибка гибридного поиска в PostgreSQL: {e}")
            return []
    
    def search(
        self, 
        query: str, 
        n_results: int = CONTEXT_WINDOW
    ) -> List[Dict[str, Any]]:
        """Базовый поиск"""
        return self.hybrid_search(query, n_results)
    
    def get_context(self, query: str, user_id: Optional[str] = None) -> str:
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            return ""

        try:
            import psycopg2
            conn = psycopg2.connect(db_url, connect_timeout=3)
            cursor = conn.cursor()

            # user_id фильтр
            user_filter = ""
            user_params = []
            if user_id:
                user_filter = "AND (user_id = %s OR user_id IS NULL)"
                user_params = [user_id]

            keywords = list(dict.fromkeys(kw for kw in extract_keywords(query) if len(kw) >= 3))
            if keywords:
                like_patterns = [f'%{kw}%' for kw in keywords]
                cursor.execute(
                    f"""SELECT user_message, ai_response, metadata, topic, created_at
                    FROM rag_dialogs
                    WHERE (user_message ILIKE ANY(%s) OR ai_response ILIKE ANY(%s) OR topic ILIKE ANY(%s))
                    {user_filter}
                    ORDER BY created_at DESC LIMIT 3""",
                    (like_patterns, like_patterns, like_patterns, *user_params)
                )
            else:
                cursor.execute(
                    f"""SELECT user_message, ai_response, metadata, topic, created_at
                    FROM rag_dialogs
                    WHERE (user_message ILIKE %s OR ai_response ILIKE %s OR topic ILIKE %s)
                    {user_filter}
                    ORDER BY created_at DESC LIMIT 3""",
                    (f'%{query}%', f'%{query}%', f'%{query}%', *user_params)
                )
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            dialogs = []
            for row in rows:
                meta = row[2] if isinstance(row[2], dict) else json.loads(row[2]) if row[2] else {}
                dialogs.append({'metadata': meta, 'combined_score': 0.5, 'topic': row[3] if row[3] else 'общее', 'timestamp': row[4].isoformat() if row[4] else datetime.now().isoformat()})
        except Exception as e:
            logger.error(f"Ошибка получения контекста из PostgreSQL: {e}")
            return ""

        if not dialogs:
            return ""
        relevant = [d for d in dialogs if d['combined_score'] > 0.25]
        if not relevant:
            return ""

        context_parts = ["Релевантный контекст из памяти:\n"]
        for i, dialog in enumerate(relevant[:3], 1):
            meta = dialog['metadata']
            context_parts.append(f"[{i}] (тема: {dialog['topic']}, score: {dialog['combined_score']:.2f})\nВопрос: {meta.get('user_message', '')}\nОтвет: {meta.get('ai_response', '')}\n")
        context_parts.append("\nИспользуй этот контекст для ответа.\n")
        return "\n".join(context_parts)
    
    def search_by_topic(self, topic: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Поиск по конкретной теме"""
        return self.hybrid_search("", n_results=n_results, topic_filter=topic)
    
    def search_by_keywords(self, keywords: List[str], 
                           n_results: int = CONTEXT_WINDOW) -> List[Dict[str, Any]]:
        """Поиск по ключевым словам"""
        if self.collection.count() == 0 or not keywords:
            return []
        
        query = " ".join(keywords)
        return self.hybrid_search(query, n_results, use_keywords=True, use_recency=False)
    
    def get_recent(self, days: int = 7, n_results: int = 10) -> List[Dict[str, Any]]:
        """Получает недавние диалоги"""
        try:
            import psycopg2
            from psycopg2.extras import Json
            
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                raise RuntimeError("❌ DATABASE_URL не настроен! Добавьте в .env")
            
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Получаем недавние диалоги
            cutoff = datetime.now() - timedelta(days=days)
            cursor.execute(
                "SELECT id, user_message, ai_response, metadata, created_at FROM rag_dialogs WHERE created_at >= %s ORDER BY created_at DESC LIMIT %s",
                (cutoff, n_results)
            )
            
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            recent = []
            now = datetime.now()
            
            for row in rows:
                doc_id = row[0]
                user_message = row[1]
                ai_response = row[2]
                meta = row[3] if isinstance(row[3], dict) else json.loads(row[3]) if row[3] else {}
                created_at = row[4].isoformat() if row[4] else datetime.now().isoformat()
                
                try:
                    doc_time = datetime.fromisoformat(created_at)
                    age_hours = (now - doc_time).total_seconds() / 3600
                    
                    recent.append({
                        "id": doc_id,
                        "document": f"Вопрос: {user_message}\nОтвет: {ai_response}",
                        "metadata": meta,
                        "timestamp": created_at,
                        "topic": meta.get('topic', 'общее'),
                        "age_hours": round(age_hours, 1)
                    })
                except Exception:
                    continue
            
            return recent
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения недавних диалогов из PostgreSQL: {e}")
            return []
    
    def get_topic_stats(self) -> Dict[str, int]:
        """Статистика по темам"""
        try:
            import psycopg2
            from psycopg2.extras import Json
            
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                raise RuntimeError("❌ DATABASE_URL не настроен! Добавьте в .env")
            
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Получаем статистику по темам
            cursor.execute("""
                SELECT topic, COUNT(*) as count 
                FROM rag_dialogs 
                GROUP BY topic
                ORDER BY count DESC
                """)
            topic_rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            topic_counts = {row[0]: row[1] for row in topic_rows} if topic_rows else {}
            
            return topic_counts
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики по темам из PostgreSQL: {e}")
            return {}
    
    def get_entity_index(self) -> Dict[str, List[str]]:
        """Индекс сущностей -> документы"""
        try:
            import psycopg2
            from psycopg2.extras import Json
            
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                raise RuntimeError("❌ DATABASE_URL не настроен! Добавьте в .env")
            
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Получаем все диалоги с сущностями
            cursor.execute(
                "SELECT id, entities FROM rag_dialogs WHERE entities IS NOT NULL AND entities != '[]'"
            )
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            entity_index = {}
            
            for row in rows:
                doc_id = row[0]
                entities_json = row[1]
                
                try:
                    entities = json.loads(entities_json) if entities_json else []
                    for entity in entities:
                        entity_value = entity.get('value', '')
                        if entity_value:
                            if entity_value not in entity_index:
                                entity_index[entity_value] = []
                            entity_index[entity_value].append(doc_id)
                except Exception as e:
                    logger.warning(f"{__name__} error: {e}")
            
            return entity_index
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения индекса сущностей из PostgreSQL: {e}")
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """Расширенная статистика RAG (PostgreSQL)"""
        # Проверяем наличие psycopg2
        try:
            import psycopg2
        except ImportError:
            logger.warning("⚠️ psycopg2 не установлен, статистика RAG недоступна")
            return {
                "total_dialogs": 0,
                "with_keywords": 0,
                "summarized": 0,
                "total_entities": 0,
                "total_relations": 0,
                "topic_distribution": {},
                "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
                "persist_dir": "PostgreSQL",
                "version": "3.0",
                "features": {
                    "hybrid_search": True,
                    "keyword_extraction": True,
                    "recency_ranking": True,
                    "auto_summarization": True,
                    "topic_classification": True,
                    "entity_extraction": True,
                    "relation_extraction": True,
                    "llm_summarization": self.use_llm_summarization
                },
                "note": "psycopg2 не установлен - статистика недоступна"
            }
    
        try:
            from psycopg2.extras import Json
            
            # Получаем URL базы данных
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                raise RuntimeError("❌ DATABASE_URL не настроен! Добавьте в .env")
            
            # Подключаемся к PostgreSQL
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Получаем общее количество записей
            cursor.execute("SELECT COUNT(*) FROM rag_dialogs")
            total = cursor.fetchone()[0]
            
            # Получаем статистику по темам
            cursor.execute("""
                SELECT topic, COUNT(*) as count 
                FROM rag_dialogs 
                GROUP BY topic
                ORDER BY count DESC
                """)
            topic_rows = cursor.fetchall()
            topic_counts = {row[0]: row[1] for row in topic_rows} if topic_rows else {}
            
            # Получаем статистику по сентиментам
            cursor.execute("""
                SELECT sentiment, COUNT(*) as count 
                FROM rag_dialogs 
                GROUP BY sentiment
                ORDER BY count DESC
                """)
            sentiment_rows = cursor.fetchall()
            sentiment_counts = {row[0]: row[1] for row in sentiment_rows} if sentiment_rows else {"positive": 0, "negative": 0, "neutral": 0}
            
            # Закрываем соединение
            cursor.close()
            conn.close()
            
            return {
                "total_dialogs": total,
                "with_keywords": 0,
                "summarized": 0,
                "total_entities": 0,
                "total_relations": 0,
                "topic_distribution": topic_counts,
                "sentiment_distribution": sentiment_counts,
                "persist_dir": "PostgreSQL",
                "version": "3.0",
                "features": {
                    "hybrid_search": True,
                    "keyword_extraction": True,
                    "recency_ranking": True,
                    "auto_summarization": True,
                    "topic_classification": True,
                    "entity_extraction": True,
                    "relation_extraction": True,
                    "llm_summarization": self.use_llm_summarization
                }
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики RAG: {e}")
            # Возвращаем безопасный fallback
            return {
                "total_dialogs": 0,
                "with_keywords": 0,
                "summarized": 0,
                "total_entities": 0,
                "total_relations": 0,
                "topic_distribution": {},
                "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
                "persist_dir": "PostgreSQL",
                "version": "3.0",
                "features": {
                    "hybrid_search": True,
                    "keyword_extraction": True,
                    "recency_ranking": True,
                    "auto_summarization": True,
                    "topic_classification": True,
                    "entity_extraction": True,
                    "relation_extraction": True,
                    "llm_summarization": self.use_llm_summarization
                }
            }
    
    def clear(self):
        """Очищает память"""
        try:
            import psycopg2
            
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                raise RuntimeError("❌ DATABASE_URL не настроен! Добавьте в .env")
            
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Очищаем таблицу rag_dialogs
            cursor.execute("TRUNCATE TABLE rag_dialogs RESTART IDENTITY")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self._keywords_cache.clear()
            logger.info("🗑️ RAG Memory v3.0 очищена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки RAG Memory из PostgreSQL: {e}")


# Глобальный экземпляр
_rag_memory: Optional[RAGMemory] = None


def get_rag() -> RAGMemory:
    """Возвращает глобальную RAG память"""
    global _rag_memory
    if _rag_memory is None:
        _rag_memory = RAGMemory()
    return _rag_memory