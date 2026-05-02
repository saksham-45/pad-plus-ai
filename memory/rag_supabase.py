"""
RAG Memory с поддержкой Supabase Vector (pgvector)

Поддерживает два бэкенда:
1. Supabase Vector (PostgreSQL + pgvector) - для production
2. ChromaDB (локально) - для fallback и локальной разработки
"""

import os
import json
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class RAGMemory:
    """Реализация RAG памяти с поддержкой Supabase Vector"""
    
    def __init__(self):
        # Определяем режим работы
        self.use_supabase = os.getenv("USE_SUPABASE_VECTOR", "false").lower() == "true"
        
        if self.use_supabase:
            logger.info("🔄 RAG: Используем Supabase Vector")
            self._init_supabase()
        else:
            logger.info("📁 RAG: Используем ChromaDB (локально)")
            self._init_chromadb()
    
    def _init_supabase(self):
        """Инициализация Supabase + pgvector"""
        try:
            import psycopg2
            from psycopg2.extras import Json
            
            self.conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            self.cursor = self.conn.cursor()
            
            # Проверка наличия расширения vector
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_extension 
                    WHERE extname = 'vector'
                )
            """)
            
            if not self.cursor.fetchone()[0]:
                raise RuntimeError("pgvector расширение не найдено в PostgreSQL")
            
            logger.info("✅ Supabase Vector инициализирован")
            
        except ImportError:
            logger.warning("⚠️ psycopg2 не установлен, переключаемся на ChromaDB")
            self.use_supabase = False
            self._init_chromadb()
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Supabase: {e}")
            logger.warning("⚠️ Переключаемся на ChromaDB fallback")
            self.use_supabase = False
            self._init_chromadb()
    
    def _init_chromadb(self):
        """Инициализация ChromaDB (fallback)"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            chroma_path = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
            Path(chroma_path).mkdir(parents=True, exist_ok=True)
            
            self.chroma_client = chromadb.PersistentClient(
                path=chroma_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            self.collection = self.chroma_client.get_or_create_collection(
                name="rag_embeddings",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info("✅ ChromaDB инициализирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации ChromaDB: {e}")
            raise
    
    def add_embedding(self, text: str, embedding: List[float], 
                     user_id: Optional[str] = None,
                     collection_name: str = "default",
                     metadata: Optional[Dict] = None) -> str:
        """Добавить embedding в память"""
        
        if self.use_supabase:
            return self._supabase_add(text, embedding, user_id, collection_name, metadata)
        else:
            return self._chromadb_add(text, embedding, user_id, metadata)
    
    def _supabase_add(self, text: str, embedding: List[float],
                     user_id: Optional[str],
                     collection_name: str,
                     metadata: Optional[Dict]) -> str:
        """Добавление через Supabase"""
        try:
            from psycopg2.extras import execute_values
            
            query = """
                INSERT INTO rag_embeddings (text, embedding, user_id, collection_name, metadata)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """
            
            self.cursor.execute(query, (
                text,
                json.dumps(embedding),
                user_id,
                collection_name,
                Json(metadata) if metadata else None
            ))
            
            self.conn.commit()
            result = self.cursor.fetchone()
            embed_id = str(result[0]) if result else None
            
            logger.debug(f"✅ Добавлен embedding в Supabase: {embed_id}")
            return embed_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления в Supabase: {e}")
            raise
    
    def _chromadb_add(self, text: str, embedding: List[float],
                     user_id: Optional[str],
                     metadata: Optional[Dict]) -> str:
        """Добавление через ChromaDB"""
        try:
            import uuid
            
            embed_id = str(uuid.uuid4())
            
            self.collection.add(
                ids=[embed_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[{"user_id": user_id, **(metadata or {})}]
            )
            
            logger.debug(f"✅ Добавлен embedding в ChromaDB: {embed_id}")
            return embed_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления в ChromaDB: {e}")
            raise
    
    def search(self, query_embedding: List[float], 
              user_id: Optional[str] = None,
              collection_name: str = "default",
              top_k: int = 5) -> List[Dict]:
        """Поиск по embedding"""
        
        if self.use_supabase:
            return self._supabase_search(query_embedding, user_id, collection_name, top_k)
        else:
            return self._chromadb_search(query_embedding, user_id, top_k)
    
    def _supabase_search(self, query_embedding: List[float],
                        user_id: Optional[str],
                        collection_name: str,
                        top_k: int) -> List[Dict]:
        """Поиск через Supabase с pgvector"""
        try:
            # Построение запроса с фильтрацией по user_id
            filter_clause = ""
            params = [json.dumps(query_embedding), top_k]
            
            if user_id:
                filter_clause = "WHERE user_id = %s AND collection_name = %s"
                params.extend([user_id, collection_name])
            
            query = f"""
                SELECT id, text, embedding, user_id, collection_name, metadata, created_at,
                       (embedding <=> %s) AS distance
                FROM rag_embeddings
                {filter_clause}
                ORDER BY embedding <=> %s
                LIMIT %s
            """
            
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "id": str(row[0]),
                    "text": row[1],
                    "embedding": row[2],
                    "user_id": str(row[3]) if row[3] else None,
                    "collection_name": row[4],
                    "metadata": row[5] if row[5] else {},
                    "created_at": str(row[6]) if row[6] else None,
                    "distance": float(row[7])
                })
            
            logger.debug(f"✅ Найдено {len(results)} результатов в Supabase")
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска в Supabase: {e}")
            raise
    
    def _chromadb_search(self, query_embedding: List[float],
                        user_id: Optional[str],
                        top_k: int) -> List[Dict]:
        """Поиск через ChromaDB"""
        try:
            where_clause = None
            if user_id:
                where_clause = {"user_id": user_id}
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            
            # Преобразуем результаты
            formatted_results = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    formatted_results.append({
                        "id": results["ids"][0][i] if results["ids"] else None,
                        "text": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else None
                    })
            
            logger.debug(f"✅ Найдено {len(formatted_results)} результатов в ChromaDB")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска в ChromaDB: {e}")
            raise
    
    def get_stats(self) -> Dict:
        """Получить статистику памяти"""
        if self.use_supabase:
            return self._supabase_stats()
        else:
            return self._chromadb_stats()
    
    def _supabase_stats(self) -> Dict:
        """Статистика Supabase"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM rag_embeddings")
            total = self.cursor.fetchone()[0]
            
            self.cursor.execute("""
                SELECT COUNT(DISTINCT user_id) FROM rag_embeddings WHERE user_id IS NOT NULL
            """)
            users = self.cursor.fetchone()[0]
            
            return {
                "total_embeddings": total,
                "unique_users": users,
                "backend": "supabase_vector"
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики Supabase: {e}")
            return {"error": str(e), "backend": "supabase_vector"}
    
    def _chromadb_stats(self) -> Dict:
        """Статистика ChromaDB"""
        try:
            count = self.collection.count()
            return {
                "total_embeddings": count,
                "backend": "chromadb"
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики ChromaDB: {e}")
            return {"error": str(e), "backend": "chromadb"}
    
    def close(self):
        """Закрытие соединения"""
        if self.use_supabase and hasattr(self, 'conn'):
            self.conn.close()
            logger.info("✅ Supabase соединение закрыто")
    
    def __del__(self):
        """Очистка при удалении"""
        try:
            self.close()
        except:
            pass


# Singleton instance
_rag_instance = None


def get_rag() -> RAGMemory:
    """Получить экземпляр RAG памяти"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGMemory()
    return _rag_instance


def reset_rag():
    """Сброс экземпляра (для тестирования)"""
    global _rag_instance
    if _rag_instance:
        _rag_instance.close()
    _rag_instance = None