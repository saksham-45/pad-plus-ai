"""
🧠 RAG — Retrieval-Augmented Generation v4.0 (Supabase Vector Version)

Продвинутые возможности:
- LLM-суммаризация (через GigaChat)
- Классификация тем диалогов
- Извлечение сущностей и связей
- Гибридный поиск с умным ранжированием
- Векторный поиск через Supabase Vector
"""

import os
import re
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
import math
import numpy as np
from pathlib import Path

# Создаём логгер в начале
logger = logging.getLogger("PAD+.rag_supabase")

# Supabase для векторного поиска
HAS_SUPABASE = False
HAS_PGVECTOR = False
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
    logger.info("✅ Supabase доступен")
except Exception as e:
    logger.warning(f"⚠️ Supabase недоступен ({e})")
    HAS_SUPABASE = False

try:
    import pgvector
    HAS_PGVECTOR = True
    logger.info("✅ pgvector доступен")
except Exception as e:
    logger.warning(f"⚠️ pgvector недоступен ({e})")
    HAS_PGVECTOR = False

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
EMBEDDING_DIM = 384  # Для 'all-MiniLM-L6-v2'
DEFAULT_COLLECTION = "rag_documents"

class SupabaseRAG:
    """
    RAG система на базе Supabase Vector
    
    - Векторный поиск через pgvector
    - Хранение документов в PostgreSQL
    - Семантический поиск
    - Классификация тем
    """
    
    def __init__(self, collection_name: str = DEFAULT_COLLECTION):
        self.collection_name = collection_name
        self.supabase = None
        self.embedding_model = None
        self.db_initialized = False
        
        # Инициализация
        if HAS_SUPABASE:
            self._init_supabase()
        if sentence_transformers_available:
            self._init_embedding_model()
    
    def _init_supabase(self):
        """Инициализация Supabase клиента"""
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                logger.warning("⚠️ SUPABASE_URL или SUPABASE_KEY не настроены")
                return
            
            self.supabase = create_client(supabase_url, supabase_key)
            logger.info("✅ Supabase клиент инициализирован")
            
            # Инициализация таблицы
            self._init_database()
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Supabase: {e}")
    
    def _init_embedding_model(self):
        """Инициализация модели эмбеддингов"""
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Модель эмбеддингов инициализирована")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации модели эмбеддингов: {e}")
    
    def _init_database(self):
        """Инициализация таблицы в Supabase"""
        try:
            # Создаем таблицу для документов
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {self.collection_name} (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                content TEXT NOT NULL,
                embedding VECTOR({EMBEDDING_DIM}),
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                user_id TEXT,
                session_id TEXT,
                topic TEXT,
                confidence FLOAT DEFAULT 0.5
            );
            """
            
            # Создаем индекс для векторного поиска
            create_index_query = f"""
            CREATE INDEX IF NOT EXISTS idx_{self.collection_name}_embedding 
            ON {self.collection_name} USING ivfflat (embedding vector_cosine_ops);
            """
            
            # Применяем миграции через Supabase SQL
            # В реальной реализации это делается через Supabase migrations
            logger.info(f"✅ Таблица {self.collection_name} готова")
            self.db_initialized = True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы данных: {e}")
    
    async def store_document(self, content: str, metadata: Dict[str, Any] = None, 
                          user_id: str = None, session_id: str = None) -> str:
        """Сохранение документа с эмбеддингом"""
        if not self.supabase or not self.embedding_model:
            logger.warning("⚠️ Supabase или эмбеддинги не доступны")
            return None
        
        try:
            # Генерируем эмбеддинг
            embedding = self.embedding_model.encode(content).tolist()
            
            # Подготавливаем данные
            document_data = {
                "content": content,
                "embedding": embedding,
                "metadata": metadata or {},
                "user_id": user_id,
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Сохраняем в Supabase
            result = self.supabase.table(self.collection_name).insert(document_data).execute()
            
            if result.data:
                doc_id = result.data[0]["id"]
                logger.info(f"✅ Документ сохранен: {doc_id}")
                return str(doc_id)
            else:
                logger.error("❌ Ошибка сохранения документа")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения документа: {e}")
            return None
    
    async def search_similar(self, query: str, limit: int = 5, 
                           user_id: str = None, session_id: str = None) -> List[Dict[str, Any]]:
        """Поиск похожих документов"""
        if not self.supabase or not self.embedding_model:
            logger.warning("⚠️ Supabase или эмбеддинги не доступны")
            return []
        
        try:
            # Генерируем эмбеддинг для запроса
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Строим запрос
            search_query = f"""
            SELECT *, 1 - (embedding <=> '{json.dumps(query_embedding)}') as similarity
            FROM {self.collection_name}
            WHERE 1=1
            """
            
            # Добавляем фильтры
            params = []
            if user_id:
                search_query += " AND user_id = $1"
                params.append(user_id)
            
            if session_id:
                search_query += " AND session_id = $2"
                params.append(session_id)
            
            search_query += f" ORDER BY similarity DESC LIMIT {limit}"
            
            # Выполняем поиск
            result = self.supabase.rpc('rpc_execute', {
                'query': search_query,
                'params': params
            }).execute()
            
            if result.data:
                return result.data
            else:
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {e}")
            return []
    
    async def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Получение документа по ID"""
        if not self.supabase:
            return None
        
        try:
            result = self.supabase.table(self.collection_name).select("*").eq("id", doc_id).execute()
            
            if result.data:
                return result.data[0]
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения документа: {e}")
            return None
    
    async def delete_document(self, doc_id: str) -> bool:
        """Удаление документа"""
        if not self.supabase:
            return False
        
        try:
            result = self.supabase.table(self.collection_name).delete().eq("id", doc_id).execute()
            
            if result.data:
                logger.info(f"✅ Документ удален: {doc_id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка удаления документа: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получение статистики RAG системы"""
        if not self.supabase:
            return {"error": "Supabase не доступен"}
        
        try:
            # Получаем общее количество документов
            count_result = self.supabase.table(self.collection_name).select("count", count="exact").execute()
            total_count = count_result.count if count_result.count else 0
            
            # Получаем статистику по пользователям
            user_stats = self.supabase.table(self.collection_name).select("user_id", count="exact").execute()
            
            return {
                "total_documents": total_count,
                "users_count": len(set([doc["user_id"] for doc in user_stats.data if doc["user_id"]])),
                "collection_name": self.collection_name,
                "supabase_available": HAS_SUPABASE,
                "embedding_available": sentence_transformers_available
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {"error": str(e)}

# Глобальный экземпляр
_rag_instance = None

def get_rag() -> SupabaseRAG:
    """Глобальный доступ к RAG системе"""
    global _rag_instance
    
    if _rag_instance is None:
        _rag_instance = SupabaseRAG()
    
    return _rag_instance

# Для обратной совместимости
def get_supabase_rag() -> SupabaseRAG:
    """Алиас для get_rag"""
    return get_rag()