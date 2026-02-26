# Система Памяти

Этот документ описывает систему памяти в PAD+ AI.

## Обзор

Система памяти обеспечивает:

- Хранение и извлечение диалогов
- Управление фактами и знаниями
- Граф знаний для семантических связей
- Корневую память для личности
- Интеграцию с RAG системой

## Архитектура памяти

### Компоненты

1. **MemoryManager** - Центральный менеджер памяти
2. **DialogMemory** - Память диалогов
3. **FactMemory** - Память фактов
4. **KnowledgeGraph** - Граф знаний
5. **RootsMemory** - Корневая память
6. **MemoryOptimizer** - Оптимизатор памяти

### Иерархия памяти

```
Memory System
├── Short-term Memory (Оперативная память)
│   ├── Current Conversation
│   ├── Recent Facts
│   └── Active Context
├── Long-term Memory (Долгосрочная память)
│   ├── Dialog Memory (Диалоги)
│   ├── Fact Memory (Факты)
│   ├── Knowledge Graph (Граф знаний)
│   └── Roots Memory (Корневая память)
└── Working Memory (Рабочая память)
    ├── Active Context
    ├── Current Goals
    └── Relevant Memories
```

## MemoryManager

### Центральный менеджер памяти

```python
class MemoryManager:
    def __init__(self):
        self.dialog_memory = DialogMemory()
        self.fact_memory = FactMemory()
        self.knowledge_graph = KnowledgeGraph()
        self.roots_memory = RootsMemory()
        self.memory_optimizer = MemoryOptimizer()
        self.memory_stats = MemoryStats()
        
    async def store_interaction(self, user_id: str, user_message: str, ai_response: str, context: dict):
        """Сохранение взаимодействия в память"""
        # 1. Сохранение в диалоговую память
        await self.dialog_memory.store_dialog(user_id, user_message, ai_response, context)
        
        # 2. Извлечение и сохранение фактов
        facts = await self.extract_facts(user_message, ai_response)
        for fact in facts:
            await self.fact_memory.add_fact(fact, source="dialog", confidence=0.8)
            
        # 3. Обновление графа знаний
        await self.update_knowledge_graph(user_message, ai_response, context)
        
        # 4. Проверка на важные события для корневой памяти
        if await self.is_significant_event(user_message, ai_response, context):
            await self.roots_memory.add_core_memory(
                f"{user_message} -> {ai_response}",
                emotional_weight=context.get("emotional_weight", 0.5),
                timestamp=datetime.now()
            )
            
        # 5. Оптимизация памяти
        await self.memory_optimizer.optimize_memory()
        
    async def retrieve_context(self, user_id: str, query: str, context_size: int = 5) -> dict:
        """Извлечение контекста из памяти"""
        # 1. Поиск в диалоговой памяти
        dialog_context = await self.dialog_memory.search_dialogs(user_id, query, context_size)
        
        # 2. Поиск в фактах
        fact_context = await self.fact_memory.search_facts(query, context_size)
        
        # 3. Поиск в графе знаний
        kg_context = await self.knowledge_graph.search_entities(query, context_size)
        
        # 4. Интеграция контекста
        integrated_context = self.integrate_memory_context(dialog_context, fact_context, kg_context)
        
        return integrated_context
        
    def integrate_memory_context(self, dialog_context: list, fact_context: list, kg_context: list) -> dict:
        """Интеграция контекста из разных источников памяти"""
        return {
            "dialog_history": dialog_context,
            "relevant_facts": fact_context,
            "knowledge_entities": kg_context,
            "context_score": self.calculate_context_score(dialog_context, fact_context, kg_context)
        }
```

## DialogMemory

### Память диалогов

```python
class DialogMemory:
    def __init__(self):
        self.dialogs = []
        self.user_dialogs = defaultdict(list)
        self.dialog_embeddings = {}
        self.max_dialogs_per_user = 1000
        
    async def store_dialog(self, user_id: str, user_message: str, ai_response: str, context: dict):
        """Сохранение диалога"""
        # Создание embedding
        dialog_text = f"{user_message} {ai_response}"
        embedding = await self.create_embedding(dialog_text)
        
        # Создание записи диалога
        dialog = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "user_message": user_message,
            "ai_response": ai_response,
            "timestamp": datetime.now(),
            "context": context,
            "embedding": embedding,
            "metadata": {
                "message_length": len(dialog_text),
                "complexity": self.calculate_complexity(dialog_text),
                "emotional_valence": context.get("emotional_valence", 0.0)
            }
        }
        
        # Сохранение диалога
        self.dialogs.append(dialog)
        self.user_dialogs[user_id].append(dialog)
        self.dialog_embeddings[dialog["id"]] = embedding
        
        # Ограничение размера памяти
        if len(self.user_dialogs[user_id]) > self.max_dialogs_per_user:
            oldest_dialog = self.user_dialogs[user_id].pop(0)
            if oldest_dialog["id"] in self.dialog_embeddings:
                del self.dialog_embeddings[oldest_dialog["id"]]
                
    async def search_dialogs(self, user_id: str, query: str, top_k: int = 5) -> list:
        """Поиск диалогов по запросу"""
        # Создание embedding запроса
        query_embedding = await self.create_embedding(query)
        
        # Поиск по диалогам пользователя
        user_dialogs = self.user_dialogs.get(user_id, [])
        
        if not user_dialogs:
            return []
            
        # Расчет схожести
        similarities = []
        for dialog in user_dialogs:
            dialog_embedding = self.dialog_embeddings.get(dialog["id"])
            if dialog_embedding:
                similarity = self.calculate_similarity(query_embedding, dialog_embedding)
                similarities.append((dialog, similarity))
                
        # Сортировка по схожести
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Возврат топ-K результатов
        return [dialog for dialog, score in similarities[:top_k]]
        
    def calculate_complexity(self, text: str) -> float:
        """Расчет сложности текста"""
        # Анализ сложности на основе различных метрик
        word_count = len(text.split())
        sentence_count = len(sent_tokenize(text))
        avg_sentence_length = word_count / max(1, sentence_count)
        
        # Расчет индекса сложности
        complexity = min(1.0, (avg_sentence_length / 20) + (word_count / 1000))
        
        return complexity
```

### Embedding диалогов

```python
async def create_embedding(self, text: str) -> list:
    """Создание embedding для текста"""
    # Использование OpenAI embeddings
    try:
        response = await openai.Embedding.acreate(
            model="text-embedding-ada-002",
            input=text
        )
        return response['data'][0]['embedding']
    except Exception as e:
        logger.error(f"Failed to create embedding: {e}")
        return []
        
def calculate_similarity(self, vec1: list, vec2: list) -> float:
    """Расчет косинусной схожести между векторами"""
    if not vec1 or not vec2:
        return 0.0
        
    # Расчет косинусного расстояния
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
        
    return dot_product / (magnitude1 * magnitude2)
```

## FactMemory

### Память фактов

```python
class FactMemory:
    def __init__(self):
        self.facts = {}
        self.fact_sources = defaultdict(list)
        self.fact_confidence = {}
        self.fact_categories = defaultdict(list)
        
    async def add_fact(self, fact: str, source: str, confidence: float, category: str = None):
        """Добавление факта"""
        fact_id = self.generate_fact_id(fact)
        
        if fact_id not in self.facts:
            # Новый факт
            self.facts[fact_id] = {
                "text": fact,
                "source": source,
                "confidence": confidence,
                "timestamp": datetime.now(),
                "category": category or self.categorize_fact(fact)
            }
            self.fact_confidence[fact_id] = confidence
        else:
            # Обновление существующего факта
            old_confidence = self.fact_confidence[fact_id]
            new_confidence = self.update_fact_confidence(old_confidence, confidence)
            self.fact_confidence[fact_id] = new_confidence
            self.facts[fact_id]["timestamp"] = datetime.now()
            
        # Добавление источника
        self.fact_sources[fact_id].append({
            "source": source,
            "confidence": confidence,
            "timestamp": datetime.now()
        })
        
        # Добавление в категорию
        if category:
            self.fact_categories[category].append(fact_id)
            
    def update_fact_confidence(self, old_confidence: float, new_confidence: float) -> float:
        """Обновление уверенности в факте"""
        # Взвешенное среднее
        weight_old = len(self.fact_sources[self.generate_fact_id("")]) - 1
        weight_new = 1
        
        total_weight = weight_old + weight_new
        updated_confidence = ((old_confidence * weight_old) + (new_confidence * weight_new)) / total_weight
        
        return updated_confidence
        
    async def search_facts(self, query: str, top_k: int = 5, min_confidence: float = 0.5) -> list:
        """Поиск фактов по запросу"""
        # Поиск по тексту фактов
        relevant_facts = []
        
        for fact_id, fact_data in self.facts.items():
            if fact_data["confidence"] >= min_confidence:
                # Расчет релевантности
                relevance = self.calculate_fact_relevance(query, fact_data["text"])
                
                if relevance > 0.3:  # Порог релевантности
                    relevant_facts.append({
                        "fact": fact_data["text"],
                        "confidence": fact_data["confidence"],
                        "relevance": relevance,
                        "sources": self.fact_sources[fact_id]
                    })
                    
        # Сортировка по релевантности и уверенности
        relevant_facts.sort(key=lambda x: (x["relevance"], x["confidence"]), reverse=True)
        
        return relevant_facts[:top_k]
```

### Категоризация фактов

```python
def categorize_fact(self, fact: str) -> str:
    """Категоризация факта"""
    fact_lower = fact.lower()
    
    # Определение категории на основе ключевых слов
    if any(keyword in fact_lower for keyword in ["кто", "что", "где", "когда"]):
        return "definition"
    elif any(keyword in fact_lower for keyword in ["почему", "потому что", "причина"]):
        return "explanation"
    elif any(keyword in fact_lower for keyword in ["как", "способ", "метод"]):
        return "procedure"
    elif any(keyword in fact_lower for keyword in ["число", "количество", "размер"]):
        return "quantitative"
    elif any(keyword in fact_lower for keyword in ["хорошо", "плохо", "лучше", "хуже"]):
        return "evaluation"
    else:
        return "general"
        
def calculate_fact_relevance(self, query: str, fact: str) -> float:
    """Расчет релевантности факта к запросу"""
    # Простая TF-IDF подобная метрика
    query_words = set(query.lower().split())
    fact_words = set(fact.lower().split())
    
    # Пересечение слов
    common_words = query_words.intersection(fact_words)
    
    # Расчет релевантности
    if not query_words:
        return 0.0
        
    relevance = len(common_words) / len(query_words)
    
    return relevance
```

## KnowledgeGraph

### Граф знаний

```python
class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.Graph()
        self.entities = {}
        self.relationships = {}
        self.entity_embeddings = {}
        
    async def add_entity(self, entity_id: str, entity_data: dict):
        """Добавление сущности в граф"""
        self.graph.add_node(entity_id, **entity_data)
        self.entities[entity_id] = entity_data
        
        # Создание embedding для сущности
        entity_text = self.create_entity_text(entity_data)
        embedding = await self.create_embedding(entity_text)
        self.entity_embeddings[entity_id] = embedding
        
    async def add_relationship(self, entity1_id: str, entity2_id: str, relationship: str, weight: float = 1.0):
        """Добавление связи между сущностями"""
        if entity1_id in self.entities and entity2_id in self.entities:
            self.graph.add_edge(entity1_id, entity2_id, 
                              relationship=relationship, 
                              weight=weight)
            
            # Сохранение информации о связи
            relationship_id = f"{entity1_id}-{entity2_id}-{relationship}"
            self.relationships[relationship_id] = {
                "entity1": entity1_id,
                "entity2": entity2_id,
                "relationship": relationship,
                "weight": weight,
                "timestamp": datetime.now()
            }
            
    async def search_entities(self, query: str, top_k: int = 5) -> list:
        """Поиск сущностей по запросу"""
        query_embedding = await self.create_embedding(query)
        
        # Поиск по схожести embedding
        similarities = []
        for entity_id, embedding in self.entity_embeddings.items():
            similarity = self.calculate_similarity(query_embedding, embedding)
            similarities.append((entity_id, similarity))
            
        # Сортировка по схожести
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Возврат топ-K результатов
        results = []
        for entity_id, similarity in similarities[:top_k]:
            entity_data = self.entities[entity_id]
            results.append({
                "entity_id": entity_id,
                "entity_data": entity_data,
                "similarity": similarity
            })
            
        return results
        
    def create_entity_text(self, entity_data: dict) -> str:
        """Создание текстового представления сущности"""
        text_parts = []
        
        for key, value in entity_data.items():
            if isinstance(value, (str, int, float)):
                text_parts.append(f"{key}: {value}")
                
        return " ".join(text_parts)
```

### Семантический анализ

```python
async def extract_entities_from_text(self, text: str) -> list:
    """Извлечение сущностей из текста"""
    # Использование spaCy для извлечения сущностей
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
    
async def extract_relationships_from_text(self, text: str) -> list:
    """Извлечение отношений из текста"""
    # Анализ зависимостей для извлечения отношений
    doc = self.nlp(text)
    
    relationships = []
    for token in doc:
        if token.dep_ in ["nsubj", "dobj", "pobj", "attr"]:
            relationships.append({
                "subject": token.head.text,
                "relation": token.dep_,
                "object": token.text,
                "confidence": self.calculate_relationship_confidence(token)
            })
            
    return relationships
    
def calculate_relationship_confidence(self, token) -> float:
    """Расчет уверенности в отношении"""
    # Простая метрика на основе позиции в предложении
    position_score = 1.0 - (token.i / len(token.doc))
    
    # Метрика на основе типа зависимости
    dep_scores = {
        "nsubj": 0.9,
        "dobj": 0.8,
        "pobj": 0.7,
        "attr": 0.6
    }
    
    dep_score = dep_scores.get(token.dep_, 0.5)
    
    return (position_score + dep_score) / 2
```

## RootsMemory

### Корневая память

```python
class RootsMemory:
    def __init__(self):
        self.core_memories = []
        self.trauma_events = []
        self.personality_seeds = []
        self.memory_strength = {}
        
    def add_core_memory(self, memory: str, emotional_weight: float, timestamp: datetime):
        """Добавление ядерной памяти"""
        memory_id = str(uuid.uuid4())
        
        core_memory = {
            "id": memory_id,
            "memory": memory,
            "emotional_weight": emotional_weight,
            "timestamp": timestamp,
            "access_count": 0,
            "last_accessed": timestamp
        }
        
        self.core_memories.append(core_memory)
        self.memory_strength[memory_id] = emotional_weight
        
        # Ограничение размера ядерной памяти
        if len(self.core_memories) > 100:
            # Удаление самой слабой памяти
            weakest_memory = min(self.core_memories, key=lambda x: self.memory_strength[x["id"]])
            self.core_memories.remove(weakest_memory)
            del self.memory_strength[weakest_memory["id"]]
            
    def add_trauma_event(self, event: str, impact: float, coping_mechanism: str):
        """Добавление травматического события"""
        trauma_event = {
            "event": event,
            "impact": impact,
            "coping_mechanism": coping_mechanism,
            "timestamp": datetime.now(),
            "processed": False
        }
        
        self.trauma_events.append(trauma_event)
        
    def add_personality_seed(self, trait: str, strength: float, origin: str):
        """Добавление семени личности"""
        personality_seed = {
            "trait": trait,
            "strength": strength,
            "origin": origin,
            "timestamp": datetime.now(),
            "evolved": False
        }
        
        self.personality_seeds.append(personality_seed)
        
    def get_core_memories(self, limit: int = 10) -> list:
        """Получение ядерных воспоминаний"""
        # Сортировка по силе памяти
        sorted_memories = sorted(self.core_memories, 
                               key=lambda x: self.memory_strength[x["id"]], 
                               reverse=True)
        
        return sorted_memories[:limit]
```

### Влияние на личность

```python
def get_personality_influence(self) -> dict:
    """Получение влияния корневой памяти на личность"""
    influence = {
        "communication_style": "neutral",
        "decision_making": "rational",
        "emotional_response": "balanced",
        "risk_tolerance": "medium",
        "trust_level": "medium"
    }
    
    # Анализ ядерных воспоминаний
    for memory in self.core_memories:
        emotional_weight = memory["emotional_weight"]
        
        if emotional_weight > 0.8:
            # Сильные эмоциональные воспоминания
            if "конфликт" in memory["memory"].lower() or "спор" in memory["memory"].lower():
                influence["communication_style"] = "defensive"
                influence["trust_level"] = "low"
            elif "успех" in memory["memory"].lower() or "победа" in memory["memory"].lower():
                influence["risk_tolerance"] = "high"
                influence["decision_making"] = "intuitive"
                
    # Анализ травматических событий
    for trauma in self.trauma_events:
        if trauma["impact"] > 0.7 and not trauma["processed"]:
            influence["emotional_response"] = "guarded"
            influence["trust_level"] = "very_low"
            influence["risk_tolerance"] = "very_low"
            
    # Анализ семян личности
    for seed in self.personality_seeds:
        if seed["strength"] > 0.6:
            if seed["trait"] == "любопытство":
                influence["communication_style"] = "inquisitive"
            elif seed["trait"] == "осторожность":
                influence["risk_tolerance"] = "low"
                
    return influence
```

## MemoryOptimizer

### Оптимизатор памяти

```python
class MemoryOptimizer:
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.memory_limits = {
            "dialog_memory": 10000,
            "fact_memory": 5000,
            "knowledge_graph": 2000
        }
        
    async def optimize_memory(self):
        """Оптимизация памяти"""
        # 1. Очистка устаревших диалогов
        await self.optimize_dialog_memory()
        
        # 2. Консолидация фактов
        await self.optimize_fact_memory()
        
        # 3. Оптимизация графа знаний
        await self.optimize_knowledge_graph()
        
        # 4. Архивирование старых данных
        await self.archive_old_data()
        
    async def optimize_dialog_memory(self):
        """Оптимизация диалоговой памяти"""
        # Удаление диалогов старше 6 месяцев
        cutoff_date = datetime.now() - timedelta(days=180)
        
        dialogs_to_remove = []
        for dialog in self.memory_manager.dialog_memory.dialogs:
            if dialog["timestamp"] < cutoff_date:
                dialogs_to_remove.append(dialog)
                
        # Удаление
        for dialog in dialogs_to_remove:
            self.memory_manager.dialog_memory.dialogs.remove(dialog)
            if dialog["user_id"] in self.memory_manager.dialog_memory.user_dialogs:
                if dialog in self.memory_manager.dialog_memory.user_dialogs[dialog["user_id"]]:
                    self.memory_manager.dialog_memory.user_dialogs[dialog["user_id"]].remove(dialog)
                    
    async def optimize_fact_memory(self):
        """Оптимизация памяти фактов"""
        # Консолидация дублирующихся фактов
        fact_groups = defaultdict(list)
        
        for fact_id, fact_data in self.memory_manager.fact_memory.facts.items():
            fact_text = fact_data["text"].lower().strip()
            fact_groups[fact_text].append(fact_id)
            
        # Объединение дубликатов
        for fact_text, fact_ids in fact_groups.items():
            if len(fact_ids) > 1:
                # Выбор факта с наивысшей уверенностью
                best_fact_id = max(fact_ids, 
                                 key=lambda x: self.memory_manager.fact_memory.fact_confidence[x])
                
                # Удаление остальных
                for fact_id in fact_ids:
                    if fact_id != best_fact_id:
                        del self.memory_manager.fact_memory.facts[fact_id]
                        del self.memory_manager.fact_memory.fact_confidence[fact_id]
```

## Future улучшения

### Планы развития

1. **Advanced Memory Retrieval**
   - Multi-modal memory retrieval
   - Context-aware memory access
   - Memory fusion techniques

2. **Memory Consolidation**
   - Automatic memory consolidation
   - Long-term memory optimization
   - Memory decay modeling

3. **Memory Security**
   - Encrypted memory storage
   - Access control for memories
   - Privacy-preserving memory access

4. **Memory Analytics**
   - Memory usage analytics
   - Memory performance monitoring
   - Memory health indicators

5. **Memory Evolution**
   - Adaptive memory management
   - Self-optimizing memory systems
   - Memory capacity expansion