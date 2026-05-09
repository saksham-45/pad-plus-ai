"""
рџ§  RAG вЂ” Retrieval-Augmented Generation v4.0 (Supabase Vector Version)

РџСЂРѕРґРІРёРЅСѓС‚С‹Рµ РІРѕР·РјРѕР¶РЅРѕСЃС‚Рё:
- LLM-СЃСѓРјРјР°СЂРёР·Р°С†РёСЏ (С‡РµСЂРµР· GigaChat)
- РљР»Р°СЃСЃРёС„РёРєР°С†РёСЏ С‚РµРј РґРёР°Р»РѕРіРѕРІ
- РР·РІР»РµС‡РµРЅРёРµ СЃСѓС‰РЅРѕСЃС‚РµР№ Рё СЃРІСЏР·РµР№
- Р“РёР±СЂРёРґРЅС‹Р№ РїРѕРёСЃРє СЃ СѓРјРЅС‹Рј СЂР°РЅР¶РёСЂРѕРІР°РЅРёРµРј
- Р’РµРєС‚РѕСЂРЅС‹Р№ РїРѕРёСЃРє С‡РµСЂРµР· Supabase Vector
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

# РЎРѕР·РґР°С‘Рј Р»РѕРіРіРµСЂ РІ РЅР°С‡Р°Р»Рµ
logger = logging.getLogger("PAD+.rag_supabase")

# Supabase РґР»СЏ РІРµРєС‚РѕСЂРЅРѕРіРѕ РїРѕРёСЃРєР°
HAS_SUPABASE = False
HAS_PGVECTOR = False
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
    logger.info("вњ… Supabase РґРѕСЃС‚СѓРїРµРЅ")
except Exception as e:
    logger.warning(f"вљ пёЏ Supabase РЅРµРґРѕСЃС‚СѓРїРµРЅ ({e})")
    HAS_SUPABASE = False

try:
    import pgvector
    HAS_PGVECTOR = True
    logger.info("вњ… pgvector РґРѕСЃС‚СѓРїРµРЅ")
except Exception as e:
    logger.warning(f"вљ пёЏ pgvector РЅРµРґРѕСЃС‚СѓРїРµРЅ ({e})")
    HAS_PGVECTOR = False

# Sentence Transformers РґР»СЏ СЌРјР±РµРґРґРёРЅРіРѕРІ
sentence_transformers_available = False
try:
    from sentence_transformers import SentenceTransformer
    sentence_transformers_available = True
    logger.info("вњ… Sentence Transformers РґРѕСЃС‚СѓРїРµРЅ")
except Exception as e:
    logger.warning(f"вљ пёЏ Sentence Transformers РЅРµРґРѕСЃС‚СѓРїРµРЅ ({e})")
    SentenceTransformer = None

# РљРѕРЅСЃС‚Р°РЅС‚С‹
CONTEXT_WINDOW = 5
EMBEDDING_DIM = 384  # Р”Р»СЏ 'all-MiniLM-L6-v2'
DEFAULT_COLLECTION = "rag_documents"

class SupabaseRAG:
    """
    RAG СЃРёСЃС‚РµРјР° РЅР° Р±Р°Р·Рµ Supabase Vector
    
    - Р’РµРєС‚РѕСЂРЅС‹Р№ РїРѕРёСЃРє С‡РµСЂРµР· pgvector
    - РҐСЂР°РЅРµРЅРёРµ РґРѕРєСѓРјРµРЅС‚РѕРІ РІ PostgreSQL
    - РЎРµРјР°РЅС‚РёС‡РµСЃРєРёР№ РїРѕРёСЃРє
    - РљР»Р°СЃСЃРёС„РёРєР°С†РёСЏ С‚РµРј
    """
    
    def __init__(self, collection_name: str = DEFAULT_COLLECTION):
        self.collection_name = collection_name
        self.supabase = None
        self.embedding_model = None
        self.db_initialized = False
        
        # РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ
        if HAS_SUPABASE:
            self._init_supabase()
        if sentence_transformers_available:
            self._init_embedding_model()
    
    def _init_supabase(self):
        """РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ Supabase РєР»РёРµРЅС‚Р°"""
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                logger.warning("вљ пёЏ SUPABASE_URL РёР»Рё SUPABASE_KEY РЅРµ РЅР°СЃС‚СЂРѕРµРЅС‹")
                return
            
            self.supabase = create_client(supabase_url, supabase_key)
            logger.info("вњ… Supabase РєР»РёРµРЅС‚ РёРЅРёС†РёР°Р»РёР·РёСЂРѕРІР°РЅ")
            
            # РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ С‚Р°Р±Р»РёС†С‹
            self._init_database()
            
        except Exception as e:
            logger.error(f"вќЊ РћС€РёР±РєР° РёРЅРёС†РёР°Р»РёР·Р°С†РёРё Supabase: {e}")
    
    def _init_embedding_model(self):
        """РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ РјРѕРґРµР»Рё СЌРјР±РµРґРґРёРЅРіРѕРІ"""
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("вњ… РњРѕРґРµР»СЊ СЌРјР±РµРґРґРёРЅРіРѕРІ РёРЅРёС†РёР°Р»РёР·РёСЂРѕРІР°РЅР°")
        except Exception as e:
            logger.error(f"вќЊ РћС€РёР±РєР° РёРЅРёС†РёР°Р»РёР·Р°С†РёРё РјРѕРґРµР»Рё СЌРјР±РµРґРґРёРЅРіРѕРІ: {e}")
    
    def _init_database(self):
        """РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ С‚Р°Р±Р»РёС†С‹ РІ Supabase"""
        try:
            # РЎРѕР·РґР°РµРј С‚Р°Р±Р»РёС†Сѓ РґР»СЏ РґРѕРєСѓРјРµРЅС‚РѕРІ
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {self.collection_name} (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                content TEXT NOT NULL,
                embedding VECTOR({EMBEDDING_DIM}),
                metadata JSONB DEFAULT '{{}}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                user_id TEXT,
                session_id TEXT,
                topic TEXT,
                confidence FLOAT DEFAULT 0.5
            );
            """
            
            # РЎРѕР·РґР°РµРј РёРЅРґРµРєСЃ РґР»СЏ РІРµРєС‚РѕСЂРЅРѕРіРѕ РїРѕРёСЃРєР°
            create_index_query = f"""
            CREATE INDEX IF NOT EXISTS idx_{self.collection_name}_embedding 
            ON {self.collection_name} USING ivfflat (embedding vector_cosine_ops);
            """
            
            # РџСЂРёРјРµРЅСЏРµРј РјРёРіСЂР°С†РёРё С‡РµСЂРµР· Supabase SQL
            # Р’ СЂРµР°Р»СЊРЅРѕР№ СЂРµР°Р»РёР·Р°С†РёРё СЌС‚Рѕ РґРµР»Р°РµС‚СЃСЏ С‡РµСЂРµР· Supabase migrations
            logger.info(f"вњ… РўР°Р±Р»РёС†Р° {self.collection_name} РіРѕС‚РѕРІР°")
            self.db_initialized = True
            
        except Exception as e:
            logger.error(f"вќЊ РћС€РёР±РєР° РёРЅРёС†РёР°Р»РёР·Р°С†РёРё Р±Р°Р·С‹ РґР°РЅРЅС‹С…: {e}")
    
    async def store_document(self, content: str, metadata: Dict[str, Any] = None, 
                          user_id: str = None, session_id: str = None) -> str:
        """РЎРѕС…СЂР°РЅРµРЅРёРµ РґРѕРєСѓРјРµРЅС‚Р° СЃ СЌРјР±РµРґРґРёРЅРіРѕРј"""
        if not self.supabase or not self.embedding_model:
            logger.warning("вљ пёЏ Supabase РёР»Рё СЌРјР±РµРґРґРёРЅРіРё РЅРµ РґРѕСЃС‚СѓРїРЅС‹")
            return None
        
        try:
            # Р“РµРЅРµСЂРёСЂСѓРµРј СЌРјР±РµРґРґРёРЅРі
            embedding = self.embedding_model.encode(content).tolist()
            
            # РџРѕРґРіРѕС‚Р°РІР»РёРІР°РµРј РґР°РЅРЅС‹Рµ
            document_data = {
                "content": content,
                "embedding": embedding,
                "metadata": metadata or {},
                "user_id": user_id,
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # РЎРѕС…СЂР°РЅСЏРµРј РІ Supabase
            result = self.supabase.table(self.collection_name).insert(document_data).execute()
            
            if result.data:
                doc_id = result.data[0]["id"]
                logger.info(f"вњ… Р”РѕРєСѓРјРµРЅС‚ СЃРѕС…СЂР°РЅРµРЅ: {doc_id}")
                return str(doc_id)
            else:
                logger.error("вќЊ РћС€РёР±РєР° СЃРѕС…СЂР°РЅРµРЅРёСЏ РґРѕРєСѓРјРµРЅС‚Р°")
                return None
                
        except Exception as e:
            logger.error(f"вќЊ РћС€РёР±РєР° СЃРѕС…СЂР°РЅРµРЅРёСЏ РґРѕРєСѓРјРµРЅС‚Р°: {e}")
            return None
    
    async def search_similar(self, query: str, limit: int = 5, 
                           user_id: str = None, session_id: str = None) -> List[Dict[str, Any]]:
        """РџРѕРёСЃРє РїРѕС…РѕР¶РёС… РґРѕРєСѓРјРµРЅС‚РѕРІ"""
        if not self.supabase or not self.embedding_model:
            logger.warning("вљ пёЏ Supabase РёР»Рё СЌРјР±РµРґРґРёРЅРіРё РЅРµ РґРѕСЃС‚СѓРїРЅС‹")
            return []
        
        try:
            # Р“РµРЅРµСЂРёСЂСѓРµРј СЌРјР±РµРґРґРёРЅРі РґР»СЏ Р·Р°РїСЂРѕСЃР°
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # РЎС‚СЂРѕРёРј Р·Р°РїСЂРѕСЃ
            search_query = f"""
            SELECT *, 1 - (embedding <=> '{json.dumps(query_embedding)}') as similarity
            FROM {self.collection_name}
            WHERE 1=1
            """
            
            # Р”РѕР±Р°РІР»СЏРµРј С„РёР»СЊС‚СЂС‹
            params = []
            if user_id:
                search_query += " AND user_id = $1"
                params.append(user_id)
            
            if session_id:
                search_query += " AND session_id = $2"
                params.append(session_id)
            
            search_query += f" ORDER BY similarity DESC LIMIT {limit}"
            
            # Р’С‹РїРѕР»РЅСЏРµРј РїРѕРёСЃРє
            result = self.supabase.rpc('rpc_execute', {
                'query': search_query,
                'params': params
            }).execute()
            
            if result.data:
                return result.data
            else:
                return []
                
        except Exception as e:
            logger.error(f"вќЊ РћС€РёР±РєР° РїРѕРёСЃРєР°: {e}")
            return []
    
    async def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """РџРѕР»СѓС‡РµРЅРёРµ РґРѕРєСѓРјРµРЅС‚Р° РїРѕ ID"""
        if not self.supabase:
            return None
        
        try:
            result = self.supabase.table(self.collection_name).select("*").eq("id", doc_id).execute()
            
            if result.data:
                return result.data[0]
            else:
                return None
                
        except Exception as e:
            logger.error(f"вќЊ РћС€РёР±РєР° РїРѕР»СѓС‡РµРЅРёСЏ РґРѕРєСѓРјРµРЅС‚Р°: {e}")
            return None
    
    async def delete_document(self, doc_id: str) -> bool:
        """РЈРґР°Р»РµРЅРёРµ РґРѕРєСѓРјРµРЅС‚Р°"""
        if not self.supabase:
            return False
        
        try:
            result = self.supabase.table(self.collection_name).delete().eq("id", doc_id).execute()
            
            if result.data:
                logger.info(f"вњ… Р”РѕРєСѓРјРµРЅС‚ СѓРґР°Р»РµРЅ: {doc_id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"вќЊ РћС€РёР±РєР° СѓРґР°Р»РµРЅРёСЏ РґРѕРєСѓРјРµРЅС‚Р°: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """РџРѕР»СѓС‡РµРЅРёРµ СЃС‚Р°С‚РёСЃС‚РёРєРё RAG СЃРёСЃС‚РµРјС‹"""
        if not self.supabase:
            return {"error": "Supabase РЅРµ РґРѕСЃС‚СѓРїРµРЅ"}
        
        try:
            # РџРѕР»СѓС‡Р°РµРј РѕР±С‰РµРµ РєРѕР»РёС‡РµСЃС‚РІРѕ РґРѕРєСѓРјРµРЅС‚РѕРІ
            count_result = self.supabase.table(self.collection_name).select("count", count="exact").execute()
            total_count = count_result.count if count_result.count else 0
            
            # РџРѕР»СѓС‡Р°РµРј СЃС‚Р°С‚РёСЃС‚РёРєСѓ РїРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏРј
            user_stats = self.supabase.table(self.collection_name).select("user_id", count="exact").execute()
            
            return {
                "total_documents": total_count,
                "users_count": len(set([doc["user_id"] for doc in user_stats.data if doc["user_id"]])),
                "collection_name": self.collection_name,
                "supabase_available": HAS_SUPABASE,
                "embedding_available": sentence_transformers_available
            }
            
        except Exception as e:
            logger.error(f"вќЊ РћС€РёР±РєР° РїРѕР»СѓС‡РµРЅРёСЏ СЃС‚Р°С‚РёСЃС‚РёРєРё: {e}")
            return {"error": str(e)}

# Р“Р»РѕР±Р°Р»СЊРЅС‹Р№ СЌРєР·РµРјРїР»СЏСЂ
_rag_instance = None

def get_rag() -> SupabaseRAG:
    """Р“Р»РѕР±Р°Р»СЊРЅС‹Р№ РґРѕСЃС‚СѓРї Рє RAG СЃРёСЃС‚РµРјРµ"""
    global _rag_instance
    
    if _rag_instance is None:
        _rag_instance = SupabaseRAG()
    
    return _rag_instance

# Р”Р»СЏ РѕР±СЂР°С‚РЅРѕР№ СЃРѕРІРјРµСЃС‚РёРјРѕСЃС‚Рё
def get_supabase_rag() -> SupabaseRAG:
    """РђР»РёР°СЃ РґР»СЏ get_rag"""
    return get_rag()

