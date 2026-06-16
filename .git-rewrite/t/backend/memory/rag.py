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

# ChromaDB для векторного поиска (опционально)
chromadb = None
Settings = None
chromadb_available = False
try:
    import chromadb as _chromadb
    from chromadb.config import Settings as _Settings
    chromadb = _chromadb
    Settings = _Settings
    chromadb_available = True
    logger.info("✅ ChromaDB доступен")
except Exception as e:
    logger.warning(f"⚠️ ChromaDB недоступен ({e}), используем SQLite")
    chromadb = None
    Settings = None
    chromadb_available = False

# Sentence Transformers для эмбеддингов
sentence_transformers_available = False
try:
    from sentence_transformers import SentenceTransformer
    sentence_transformers_available = True
    logger.info("✅ Sentence Transformers доступен")
except Exception as e:
    logger.warning(f"⚠️ Sentence Transformers недоступен ({e})")
    SentenceTransformer = None

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
    LLM-суммаризация текста через LiteLLM
    
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
        if persist_dir is None:
            persist_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "chroma"
            )
        
        logger.info(f"📁 Инициализация RAG Memory v3.0, директория: {persist_dir}")
        
        try:
            os.makedirs(persist_dir, exist_ok=True)
            logger.info(f"✅ Директория данных создана: {persist_dir}")
        except Exception as e:
            logger.error(f"❌ Ошибка создания директории: {e}")
            raise
        
        self.persist_dir = persist_dir
        self.use_llm_summarization = use_llm_summarization
        self.chroma_available = False

        # Инициализируем ChromaDB с graceful degradation
        if chromadb_available and chromadb is not None and Settings is not None:
            try:
                self.client = chromadb.PersistentClient(
                    path=persist_dir,
                    settings=Settings(anonymized_telemetry=False)
                )
                logger.info("✅ ChromaDB клиент инициализирован")

                self.collection = self.client.get_or_create_collection(
                    name="padplus_dialogs_v3",
                    metadata={"description": "История диалогов PAD+ v3"}
                )
                logger.info(f"✅ Коллекция создана: {self.collection.count()} записей")
                self.chroma_available = True
            except Exception as e:
                logger.warning(f"⚠️ ChromaDB недоступен ({e}), используем SQLite fallback")
                self.chroma_available = False
        else:
            self.chroma_available = False

        if not self.chroma_available:
            self.client = None
            self.collection = None
            # SQLite fallback
            import sqlite3
            self.sqlite_path = os.path.join(persist_dir, "rag_fallback.db")
            os.makedirs(persist_dir, exist_ok=True)
            self.sqlite_conn = sqlite3.connect(self.sqlite_path)
            self.sqlite_conn.execute("""
                CREATE TABLE IF NOT EXISTS dialogs (
                    id TEXT PRIMARY KEY,
                    user_message TEXT,
                    ai_response TEXT,
                    metadata TEXT,
                    timestamp REAL
                )
            """)
            self.sqlite_conn.commit()
            logger.info("✅ SQLite fallback инициализирован")

        self._keywords_cache: Dict[str, List[str]] = {}
        logger.info(f"🧠 RAG Memory v3.0 инициализирована (ChromaDB: {self.chroma_available})")
    
    def add_dialog(
        self,
        user_message: str,
        ai_response: str,
        metadata: Dict[str, Any] = None,
        user_id: Optional[str] = None  # === ФАЗА 2: Персонализация ===
    ) -> str:
        """Добавляет диалог в память с анализом"""
        import uuid
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

        # Полный текст для поиска
        doc_text = f"Вопрос: {user_summary}\nОтвет: {ai_summary}"

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

        # Добавляем в ChromaDB или SQLite fallback
        if self.chroma_available:
            self.collection.add(
                ids=[doc_id],
                documents=[doc_text],
                metadatas=[meta]
            )
        else:
            # SQLite fallback
            import sqlite3
            conn = sqlite3.connect(self.sqlite_path)
            conn.execute(
                "INSERT INTO dialogs (id, user_message, ai_response, metadata, timestamp) VALUES (?, ?, ?, ?, ?)",
                (doc_id, user_summary, ai_summary, json.dumps(meta, ensure_ascii=False), time.time())
            )
            conn.commit()
            conn.close()

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
        
        doc_text = f"Вопрос: {user_summary}\nОтвет: {ai_summary}"
        
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
        
        self.collection.add(
            ids=[doc_id],
            documents=[doc_text],
            metadatas=[meta]
        )
        
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
        if self.collection.count() == 0:
            return []

        # === ФАЗА 2: Фильтр по user_id и теме ===
        where_filter = None
        if topic_filter:
            where_filter = {"topic": topic_filter}

        # Семантический поиск
        semantic_results = self.collection.query(
            query_texts=[query],
            n_results=min(n_results * 3, 20),
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        if not semantic_results or not semantic_results['ids']:
            return []

        # === ФАЗА 2: Фильтрация по user_id после поиска ===
        if user_id:
            # Фильтруем результаты: оставляем записи пользователя ИЛИ без user_id
            filtered_ids = []
            filtered_docs = []
            filtered_metas = []
            filtered_distances = []
            
            for i, doc_id in enumerate(semantic_results['ids'][0]):
                meta = semantic_results['metadatas'][0][i] if semantic_results['metadatas'] else {}
                record_user_id = meta.get('user_id')
                
                # Оставляем если user_id совпадает ИЛИ user_id отсутствует
                if record_user_id == user_id or record_user_id is None:
                    filtered_ids.append(doc_id)
                    filtered_docs.append(semantic_results['documents'][0][i])
                    filtered_metas.append(meta)
                    filtered_distances.append(semantic_results['distances'][0][i])
            
            # Обновляем результаты
            semantic_results['ids'] = [filtered_ids[:n_results]]
            semantic_results['documents'] = [filtered_docs[:n_results]]
            semantic_results['metadatas'] = [filtered_metas[:n_results]]
            semantic_results['distances'] = [filtered_distances[:n_results]]
        
        if not semantic_results or not semantic_results['ids']:
            return []
        
        query_keywords = extract_keywords(query) if use_keywords else []
        now = datetime.now()
        
        ranked_results = []
        
        for i, doc_id in enumerate(semantic_results['ids'][0]):
            distance = semantic_results['distances'][0][i] if semantic_results['distances'] else 0
            semantic_score = max(0, 1 - min(distance, 2) / 2)
            
            if use_keywords and query_keywords:
                meta = semantic_results['metadatas'][0][i] if semantic_results['metadatas'] else {}
                doc_keywords_str = meta.get('keywords', '')
                doc_keywords = doc_keywords_str.split(',') if doc_keywords_str else []
                keyword_score = calculate_keyword_score(query_keywords, doc_keywords)
            else:
                keyword_score = 0.0
            
            if use_recency:
                meta = semantic_results['metadatas'][0][i] if semantic_results['metadatas'] else {}
                timestamp = meta.get('timestamp', '')
                recency_score = calculate_recency_score(timestamp, now)
            else:
                recency_score = 0.5
            
            relevance = semantic_score * 0.7 + keyword_score * 0.3
            combined_score = relevance * RELEVANCE_WEIGHT + recency_score * RECENCY_WEIGHT
            
            meta = semantic_results['metadatas'][0][i] if semantic_results['metadatas'] else {}
            
            # Парсим сущности и связи
            entities = []
            relations = []
            try:
                entities_json = meta.get('entities', '[]')
                entities = json.loads(entities_json) if entities_json else []
                relations_json = meta.get('relations', '[]')
                relations = json.loads(relations_json) if relations_json else []
            except Exception:
                pass
            
            ranked_results.append({
                "id": doc_id,
                "document": semantic_results['documents'][0][i] if semantic_results['documents'] else "",
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
        
        ranked_results.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return ranked_results[:n_results]
    
    def search(
        self, 
        query: str, 
        n_results: int = CONTEXT_WINDOW
    ) -> List[Dict[str, Any]]:
        """Базовый поиск"""
        return self.hybrid_search(query, n_results)
    
    def get_context(self, query: str, user_id: Optional[str] = None) -> str:
        """
        Формирует контекст для RAG
        """
        if self.chroma_available:
            dialogs = self.hybrid_search(query, n_results=CONTEXT_WINDOW, user_id=user_id)
        else:
            # SQLite fallback — простой поиск по ключевым словам
            import sqlite3
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.execute(
                "SELECT user_message, ai_response, metadata FROM dialogs WHERE user_message LIKE ? OR ai_response LIKE ? LIMIT 3",
                (f'%{query}%', f'%{query}%')
            )
            dialogs = []
            for row in cursor.fetchall():
                dialogs.append({
                    'metadata': json.loads(row[2]) if row[2] else {},
                    'combined_score': 0.5,
                    'topic': 'общее',
                })
            conn.close()

        if not dialogs:
            return ""

        relevant = [d for d in dialogs if d['combined_score'] > 0.25]

        if not relevant:
            return ""

        context_parts = ["📚 Релевантный контекст из памяти:\n"]

        for i, dialog in enumerate(relevant[:3], 1):
            meta = dialog['metadata']
            user_msg = meta.get('user_message', '')
            ai_resp = meta.get('ai_response', '')
            topic = dialog.get('topic', 'общее')
            
            # Добавляем пометку о персонализации
            owner = " (ваши данные)" if meta.get('user_id') == user_id else ""

            context_parts.append(
                f"[{i}]{owner} (тема: {topic}, score: {dialog['combined_score']:.2f})\n"
                f"Вопрос: {user_msg}\n"
                f"Ответ: {ai_resp}\n"
            )

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
        if self.collection.count() == 0:
            return []
        
        results = self.collection.get(include=["documents", "metadatas"])
        
        if not results or not results['ids']:
            return []
        
        now = datetime.now()
        cutoff = now - timedelta(days=days)
        
        recent = []
        for i, doc_id in enumerate(results['ids']):
            meta = results['metadatas'][i] if results['metadatas'] else {}
            timestamp = meta.get('timestamp', '')
            
            try:
                doc_time = datetime.fromisoformat(timestamp)
                if doc_time >= cutoff:
                    recent.append({
                        "id": doc_id,
                        "document": results['documents'][i] if results['documents'] else "",
                        "metadata": meta,
                        "timestamp": timestamp,
                        "topic": meta.get('topic', 'общее'),
                        "age_hours": (now - doc_time).total_seconds() / 3600
                    })
            except Exception:
                continue
        
        recent.sort(key=lambda x: x.get('age_hours', 999), reverse=False)
        
        return recent[:n_results]
    
    def get_topic_stats(self) -> Dict[str, int]:
        """Статистика по темам"""
        if self.collection.count() == 0:
            return {}
        
        results = self.collection.get(include=["metadatas"])
        
        topic_counts = {}
        if results and results['metadatas']:
            for meta in results['metadatas']:
                topic = meta.get('topic', 'общее')
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        return topic_counts
    
    def get_entity_index(self) -> Dict[str, List[str]]:
        """Индекс сущностей -> документы"""
        if self.collection.count() == 0:
            return {}
        
        results = self.collection.get(include=["metadatas"])
        
        entity_index = {}
        if results and results['metadatas']:
            for i, meta in enumerate(results['metadatas']):
                try:
                    entities_json = meta.get('entities', '[]')
                    entities = json.loads(entities_json) if entities_json else []
                    doc_id = results['ids'][i]
                    
                    for entity in entities:
                        entity_value = entity.get('value', '')
                        if entity_value:
                            if entity_value not in entity_index:
                                entity_index[entity_value] = []
                            entity_index[entity_value].append(doc_id)
                except Exception:
                    pass
        
        return entity_index
    
    def get_stats(self) -> Dict[str, Any]:
        """Расширенная статистика RAG"""
        if self.chroma_available:
            total = self.collection.count()
            results = self.collection.get(include=["metadatas"])
        else:
            # SQLite fallback
            import sqlite3
            conn = sqlite3.connect(self.sqlite_path)
            total = conn.execute("SELECT COUNT(*) FROM dialogs").fetchone()[0]
            results = None
            conn.close()

        keyword_count = 0
        summarized_count = 0
        total_entities = 0
        total_relations = 0
        topic_counts = {}
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}

        if self.chroma_available and results and results['metadatas']:
            for meta in results['metadatas']:
                if meta.get('keywords'):
                    keyword_count += 1
                if meta.get('is_summarized'):
                    summarized_count += 1
                
                # Темы
                topic = meta.get('topic', 'общее')
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
                
                # Сентимент
                sentiment = meta.get('sentiment', 'neutral')
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
                
                # Сущности
                try:
                    entities = json.loads(meta.get('entities', '[]'))
                    total_entities += len(entities)
                    relations = json.loads(meta.get('relations', '[]'))
                    total_relations += len(relations)
                except Exception:
                    pass
        
        return {
            "total_dialogs": total,
            "with_keywords": keyword_count,
            "summarized": summarized_count,
            "total_entities": total_entities,
            "total_relations": total_relations,
            "topic_distribution": topic_counts,
            "sentiment_distribution": sentiment_counts,
            "persist_dir": self.persist_dir,
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
            self.client.delete_collection("padplus_dialogs_v3")
        except Exception:
            pass
        
        self.collection = self.client.get_or_create_collection(
            name="padplus_dialogs_v3",
            metadata={"description": "История диалогов PAD+ v3"}
        )
        self._keywords_cache.clear()
        logger.info("🗑️ RAG Memory v3.0 очищена")


# Глобальный экземпляр
_rag_memory: Optional[RAGMemory] = None


def get_rag() -> RAGMemory:
    """Возвращает глобальную RAG память"""
    global _rag_memory
    if _rag_memory is None:
        _rag_memory = RAGMemory()
    return _rag_memory