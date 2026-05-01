# RAG Система

Этот документ описывает RAG (Retrieval-Augmented Generation) систему в PAD+ AI.

## Обзор

RAG система обеспечивает:

- Поиск по предыдущим диалогам
- Контекстное обучение на основе истории
- Интеграцию с векторными базами данных
- Поддержку нескольких типов памяти (RAG, Facts, Knowledge)

## Архитектура

### Компоненты

1. **RAGSystem** - Основная система поиска
2. **FactsManager** - Управление фактами
3. **KnowledgeGraph** - Граф знаний
4. **RootsMemory** - Корневая память
5. **VectorStore** - Векторное хранилище

### Схема данных

```
RAG System
├── Vector Store (FAISS)
│   ├── User Messages (embeddings)
│   ├── AI Responses (embeddings)
│   └── Metadata
├── Facts Database
│   ├── Verified Facts
│   ├── Sources
│   └── Confidence Scores
├── Knowledge Graph
│   ├── Entities
│   ├── Relationships
│   └── Semantic Links
└── Roots Memory
    ├── Core Memories
    ├── Trauma Events
    └── Personality Seeds
```

## RAGSystem (storage/rag.py)

### Основные функции

```python
class RAGSystem:
    def __init__(self):
        self.embedder = OpenAIEmbeddings()
        self.vector_store = FAISS()
        self.retriever = VectorStoreRetriever()
        self.similarity_threshold = 0.7
        
    async def add_dialog(self, user_message: str, ai_response: str, user_id: str):
        """Добавление диалога в RAG"""
        # Создание векторов
        user_vector = await self.embedder.embed(user_message)
        ai_vector = await self.embedder.embed(ai_response)
        
        # Сохранение в векторное хранилище
        metadata = {
            "user_message": user_message,
            "ai_response": ai_response,
            "user_id": user_id,
            "timestamp": datetime.now(),
            "dialog_id": str(uuid.uuid4())
        }
        
        self.vector_store.add_vectors([user_vector, ai_vector], [metadata, metadata])
        
    async def search(self, query: str, n_results: int = 3, user_id: str = None) -> list:
        """Поиск в RAG"""
        query_vector = await self.embedder.embed(query)
        results = self.retriever.search(query_vector, n_results)
        
        # Фильтрация по пользователю
        if user_id:
            results = [r for r in results if r.metadata.get("user_id") == user_id]
            
        # Фильтрация по порогу схожести
        results = [r for r in results if r.similarity > self.similarity_threshold]
        
        return results
```

### Поиск с контекстом

```python
async def search_with_context(self, query: str, context: dict, n_results: int = 5):
    """Поиск с учетом контекста"""
    # Поиск по основному запросу
    base_results = await self.search(query, n_results * 2)
    
    # Поиск по контексту
    context_results = []
    if "user_id" in context:
        user_results = await self.search_by_user(context["user_id"], n_results)
        context_results.extend(user_results)
        
    if "topic" in context:
        topic_results = await self.search_by_topic(context["topic"], n_results)
        context_results.extend(topic_results)
    
    # Объединение и ранжирование
    all_results = base_results + context_results
    ranked_results = self.rank_results(all_results, query)
    
    return ranked_results[:n_results]
```

## FactsManager (storage/facts.py)

### Управление фактами

```python
class FactsManager:
    def __init__(self):
        self.facts = {}
        self.confidence_threshold = 0.7
        self.fact_sources = {}
        
    async def add_fact(self, fact: str, source: str, confidence: float):
        """Добавление факта"""
        if confidence < self.confidence_threshold:
            return
            
        if fact not in self.facts:
            self.facts[fact] = {
                "source": source,
                "confidence": confidence,
                "timestamp": datetime.now(),
                "verified": False
            }
            self.fact_sources[fact] = [source]
        else:
            # Обновление уверенности
            old_confidence = self.facts[fact]["confidence"]
            new_confidence = (old_confidence + confidence) / 2
            self.facts[fact]["confidence"] = new_confidence
            self.fact_sources[fact].append(source)
            
    def get_fact(self, fact: str) -> dict:
        """Получение факта"""
        return self.facts.get(fact, None)
        
    def search_facts(self, query: str, threshold: float = 0.8) -> list:
        """Поиск фактов по запросу"""
        results = []
        for fact, data in self.facts.items():
            similarity = self.calculate_similarity(query, fact)
            if similarity > threshold:
                results.append({
                    "fact": fact,
                    "data": data,
                    "similarity": similarity
                })
        
        return sorted(results, key=lambda x: x["similarity"], reverse=True)
```

### Верификация фактов

```python
async def verify_fact(self, fact: str, sources: list) -> bool:
    """Верификация факта по нескольким источникам"""
    if fact not in self.facts:
        return False
        
    # Проверка количества источников
    fact_sources = self.fact_sources.get(fact, [])
    if len(fact_sources) < 2:
        return False
        
    # Проверка достоверности источников
    reliable_sources = [s for s in fact_sources if self.is_reliable_source(s)]
    
    # Факт считается верифицированным если есть минимум 2 надежных источника
    if len(reliable_sources) >= 2:
        self.facts[fact]["verified"] = True
        return True
        
    return False
```

## KnowledgeGraph (storage/knowledge.py)

### Граф знаний

```python
class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.Graph()
        self.entities = {}
        self.relationships = {}
        
    def add_entity(self, entity_id: str, entity_data: dict):
        """Добавление сущности"""
        self.graph.add_node(entity_id, **entity_data)
        self.entities[entity_id] = entity_data
        
    def add_relationship(self, entity1: str, entity2: str, relationship: str, weight: float = 1.0):
        """Добавление связи"""
        self.graph.add_edge(entity1, entity2, relationship=relationship, weight=weight)
        self.relationships[(entity1, entity2)] = relationship
        
    def search_entities(self, query: str, top_k: int = 5) -> list:
        """Поиск сущностей"""
        results = []
        for entity_id, entity_data in self.entities.items():
            similarity = self.calculate_entity_similarity(query, entity_data)
            if similarity > 0.5:
                results.append({
                    "entity_id": entity_id,
                    "data": entity_data,
                    "similarity": similarity
                })
        
        return sorted(results, key=lambda x: x["similarity"], reverse=True)[:top_k]
        
    def get_related_entities(self, entity_id: str, depth: int = 2) -> list:
        """Получение связанных сущностей"""
        if entity_id not in self.graph:
            return []
            
        neighbors = list(nx.single_source_shortest_path_length(
            self.graph, entity_id, cutoff=depth
        ).keys())
        
        return [self.entities[n] for n in neighbors if n != entity_id]
```

### Семантический анализ

```python
def extract_entities(self, text: str) -> list:
    """Извлечение сущностей из текста"""
    # Использование spaCy или другого NLP инструмента
    doc = self.nlp(text)
    entities = []
    
    for ent in doc.ents:
        entities.append({
            "text": ent.text,
            "label": ent.label_,
            "start": ent.start_char,
            "end": ent.end_char
        })
    
    return entities
    
def extract_relationships(self, text: str) -> list:
    """Извлечение отношений из текста"""
    # Анализ зависимостей
    doc = self.nlp(text)
    relationships = []
    
    for token in doc:
        if token.dep_ in ["nsubj", "dobj", "pobj"]:
            relationships.append({
                "subject": token.head.text,
                "relation": token.dep_,
                "object": token.text
            })
    
    return relationships
```

## RootsMemory (storage/roots.py)

### Корневая память

```python
class RootsMemory:
    def __init__(self):
        self.core_memories = []
        self.trauma_events = []
        self.personality_seeds = []
        
    def add_core_memory(self, memory: str, emotional_weight: float, timestamp: datetime):
        """Добавление ядерной памяти"""
        self.core_memories.append({
            "memory": memory,
            "emotional_weight": emotional_weight,
            "timestamp": timestamp,
            "id": str(uuid.uuid4())
        })
        
    def add_trauma_event(self, event: str, impact: float, coping_mechanism: str):
        """Добавление травматического события"""
        self.trauma_events.append({
            "event": event,
            "impact": impact,
            "coping_mechanism": coping_mechanism,
            "timestamp": datetime.now()
        })
        
    def add_personality_seed(self, trait: str, strength: float, origin: str):
        """Добавление семени личности"""
        self.personality_seeds.append({
            "trait": trait,
            "strength": strength,
            "origin": origin,
            "timestamp": datetime.now()
        })
        
    def get_core_memories(self, limit: int = 10) -> list:
        """Получение ядерных воспоминаний"""
        return sorted(self.core_memories, key=lambda x: x["emotional_weight"], reverse=True)[:limit]
```

### Влияние на поведение

```python
def get_personality_influence(self) -> dict:
    """Получение влияния личности на поведение"""
    influence = {
        "communication_style": "neutral",
        "decision_making": "rational",
        "emotional_response": "balanced",
        "risk_tolerance": "medium"
    }
    
    # Анализ ядерных воспоминаний
    for memory in self.core_memories:
        if memory["emotional_weight"] > 0.8:
            # Сильные эмоциональные воспоминания влияют на стиль общения
            influence["communication_style"] = "emotional"
            
    # Анализ травматических событий
    for trauma in self.trauma_events:
        if trauma["impact"] > 0.7:
            # Высокий уровень травмы влияет на принятие решений
            influence["decision_making"] = "cautious"
            influence["risk_tolerance"] = "low"
            
    return influence
```

## Интеграция с пайплайном

### Использование в обработке запросов

```python
class Pipeline:
    async def process_chat(self, prompt: str, user_id: str, session_id: str):
        # 1. Поиск в RAG
        rag_context = await self.rag_system.search_with_context(
            prompt, {"user_id": user_id}, n_results=3
        )
        
        # 2. Поиск фактов
        fact_context = await self.facts_manager.search_facts(prompt)
        
        # 3. Поиск в графе знаний
        knowledge_context = await self.knowledge_graph.search_entities(prompt)
        
        # 4. Получение влияния корневой памяти
        roots_influence = self.roots_memory.get_personality_influence()
        
        # 5. Объединение контекста
        full_context = {
            "rag": rag_context,
            "facts": fact_context,
            "knowledge": knowledge_context,
            "roots": roots_influence
        }
        
        # 6. Генерация ответа с учетом контекста
        response = await self.generator.generate(prompt, full_context)
        
        return response
```

## API эндпоинты

### Поиск в RAG

```python
@app.post("/api/v1/rag/search")
async def rag_search(request: RAGSearchRequest):
    """Поиск в RAG системе"""
    results = await rag_system.search(
        query=request.query,
        n_results=request.n_results,
        user_id=request.user_id
    )
    
    return {
        "results": [
            {
                "user_message": r.metadata["user_message"],
                "ai_response": r.metadata["ai_response"],
                "similarity": r.similarity,
                "timestamp": r.metadata["timestamp"]
            }
            for r in results
        ]
    }
```

### Управление фактами

```python
@app.post("/api/v1/facts/add")
async def add_fact(request: FactRequest):
    """Добавление факта"""
    await facts_manager.add_fact(
        fact=request.fact,
        source=request.source,
        confidence=request.confidence
    )
    
    return {"message": "Fact added successfully"}

@app.get("/api/v1/facts/search")
async def search_facts(query: str):
    """Поиск фактов"""
    results = facts_manager.search_facts(query)
    return {"facts": results}
```

## Производительность

### Оптимизации

- Кэширование векторных эмбеддингов
- Индексация векторного хранилища
- Пагинация результатов
- Асинхронная обработка

### Мониторинг

```python
class RAGMetrics:
    def __init__(self):
        self.search_count = 0
        self.avg_response_time = 0.0
        self.hit_rate = 0.0
        
    def record_search(self, response_time: float, found_results: bool):
        """Запись метрик поиска"""
        self.search_count += 1
        self.avg_response_time = (
            (self.avg_response_time * (self.search_count - 1)) + response_time
        ) / self.search_count
        
        if found_results:
            self.hit_rate = (
                (self.hit_rate * (self.search_count - 1)) + 1
            ) / self.search_count
```

## Безопасность

### Защита данных

- Шифрование чувствительных данных
- Ограничение доступа к памяти
- Аудит операций с памятью
- Удаление устаревших данных

### Приватность

- Разделение памяти по пользователям
- Возможность удаления данных пользователя
- Анонимизация метаданных
- Соблюдение GDPR требований

## Future улучшения

- Мультимодальные векторы (текст + изображения)
- Динамическое обновление векторов
- Адаптивные пороги схожести
- Интеграция с внешними знаниями
- Обучение на основе обратной связи
- Автоматическая классификация памяти