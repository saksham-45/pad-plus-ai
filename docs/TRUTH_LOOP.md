# Truth Loop Система

Этот документ описывает систему Truth Loop в PAD+ AI.

## Обзор

Truth Loop система обеспечивает:

- Верификацию фактов в ответах ИИ
- Проверку достоверности источников
- Обнаружение и исправление ошибок
- Поддержание высокой точности ответов
- Обучение на основе обратной связи

## Архитектура Truth Loop

### Компоненты

1. **TruthVerifier** - Центральный верификатор
2. **FactChecker** - Проверка фактов
3. **SourceVerifier** - Проверка источников
4. **CrossValidator** - Кросс-валидация
5. **TruthMemory** - Память истины

### Процесс верификации

```
User Query → LLM Response → Truth Loop → Verified Response
     ↓              ↓              ↓              ↓
  Context    →   Claims    →   Verification  →  Corrections
     ↓              ↓              ↓              ↓
  RAG Search  →  Fact Check  →  Source Check  →  Final Output
```

## TruthVerifier (llm/truth.py)

### Центральный верификатор

```python
class TruthVerifier:
    def __init__(self):
        self.fact_checker = FactChecker()
        self.source_verifier = SourceVerifier()
        self.cross_validator = CrossValidator()
        self.truth_memory = TruthMemory()
        self.confidence_threshold = 0.8
        self.max_iterations = 3
        
    async def verify_response(self, response: str, context: dict) -> VerificationResult:
        """Комплексная верификация ответа"""
        # 1. Извлечение утверждений
        claims = await self.extract_claims(response)
        
        # 2. Проверка каждого утверждения
        verified_claims = []
        for claim in claims:
            verification = await self.verify_claim(claim, context)
            
            if verification.confidence > self.confidence_threshold:
                # Утверждение подтверждено
                verified_claims.append(claim.text)
            else:
                # Запрос на уточнение или замена
                clarification = await self.get_clarification(claim, context)
                verified_claims.append(clarification)
                
        # 3. Реконструкция ответа
        verified_response = self.reconstruct_response(verified_claims, response)
        
        # 4. Сохранение в память истины
        await self.truth_memory.store_verification(response, verified_response, claims)
        
        return VerificationResult(
            original_response=response,
            verified_response=verified_response,
            confidence=self.calculate_overall_confidence(claims),
            claims=claims
        )
        
    async def extract_claims(self, text: str) -> list:
        """Извлечение утверждений из текста"""
        # Использование NLP для анализа предложений
        claims = []
        sentences = sent_tokenize(text)
        
        for sentence in sentences:
            if self.is_claim(sentence):
                claim = Claim(
                    text=sentence,
                    type=self.classify_claim_type(sentence),
                    confidence=0.0,
                    sources=[]
                )
                claims.append(claim)
                
        return claims
        
    def is_claim(self, sentence: str) -> bool:
        """Проверка, является ли предложение утверждением"""
        # Фильтрация вопросов, восклицаний, просьб
        if sentence.endswith('?') or sentence.endswith('!'):
            return False
            
        # Проверка на наличие утверждений
        claim_indicators = [
            "это", "является", "представляет", "означает",
            "говорит", "утверждает", "считает", "знает"
        ]
        
        sentence_lower = sentence.lower()
        return any(indicator in sentence_lower for indicator in claim_indicators)
```

## FactChecker

### Проверка фактов

```python
class FactChecker:
    def __init__(self):
        self.fact_database = {}
        self.external_apis = []
        self.confidence_weights = {
            "database": 0.8,
            "external_api": 0.7,
            "cross_reference": 0.9
        }
        
    async def check(self, claim: str) -> FactCheckResult:
        """Проверка факта"""
        # 1. Поиск в базе данных
        db_result = await self.check_in_database(claim)
        
        # 2. Проверка через внешние API
        api_result = await self.check_via_api(claim)
        
        # 3. Кросс-проверка
        cross_result = await self.cross_check(claim)
        
        # 4. Расчет общего доверия
        overall_confidence = self.calculate_confidence(db_result, api_result, cross_result)
        
        return FactCheckResult(
            claim=claim,
            is_true=db_result.is_true or api_result.is_true or cross_result.is_true,
            confidence=overall_confidence,
            sources=db_result.sources + api_result.sources + cross_result.sources,
            explanation=self.generate_explanation(db_result, api_result, cross_result)
        )
        
    async def check_in_database(self, claim: str) -> FactCheckResult:
        """Проверка в базе данных фактов"""
        # Поиск похожих утверждений
        similar_claims = self.find_similar_claims(claim)
        
        if similar_claims:
            # Возврат результата из базы данных
            best_match = max(similar_claims, key=lambda x: x.similarity)
            return FactCheckResult(
                claim=claim,
                is_true=best_match.is_true,
                confidence=best_match.confidence,
                sources=best_match.sources,
                explanation=f"Found in database with {best_match.similarity:.2f} similarity"
            )
        else:
            return FactCheckResult(
                claim=claim,
                is_true=False,
                confidence=0.0,
                sources=[],
                explanation="Not found in fact database"
            )
```

### Внешние API проверки

```python
async def check_via_api(self, claim: str) -> FactCheckResult:
    """Проверка через внешние API"""
    results = []
    
    for api in self.external_apis:
        try:
            result = await api.check_fact(claim)
            results.append(result)
        except Exception as e:
            logger.error(f"API check failed: {e}")
            
    # Агрегация результатов
    if results:
        true_results = [r for r in results if r.is_true]
        confidence = len(true_results) / len(results)
        
        return FactCheckResult(
            claim=claim,
            is_true=confidence > 0.5,
            confidence=confidence,
            sources=[r.source for r in results],
            explanation=f"API check: {len(true_results)}/{len(results)} confirmed"
        )
    else:
        return FactCheckResult(
            claim=claim,
            is_true=False,
            confidence=0.0,
            sources=[],
            explanation="No API results available"
        )
```

## SourceVerifier

### Проверка источников

```python
class SourceVerifier:
    def __init__(self):
        self.trusted_sources = self.load_trusted_sources()
        self.source_reputation = {}
        self.source_cache = {}
        
    def load_trusted_sources(self) -> set:
        """Загрузка списка доверенных источников"""
        return {
            "wikipedia.org",
            "gov.ru",
            "edu.ru",
            "nih.gov",
            "who.int",
            "un.org"
        }
        
    async def verify(self, claim: str, sources: list) -> SourceVerificationResult:
        """Проверка достоверности источников"""
        verification_results = []
        
        for source in sources:
            result = await self.verify_source(source, claim)
            verification_results.append(result)
            
        # Агрегация результатов
        overall_trust = self.calculate_source_trust(verification_results)
        
        return SourceVerificationResult(
            claim=claim,
            sources=sources,
            overall_trust=overall_trust,
            detailed_results=verification_results
        )
        
    async def verify_source(self, source: str, claim: str) -> SourceResult:
        """Проверка конкретного источника"""
        # Проверка в кэше
        cache_key = f"{source}:{claim}"
        if cache_key in self.source_cache:
            return self.source_cache[cache_key]
            
        # Проверка репутации источника
        reputation = self.get_source_reputation(source)
        
        # Проверка актуальности информации
        freshness = await self.check_source_freshness(source)
        
        # Проверка авторитетности
        authority = self.check_source_authority(source)
        
        # Расчет общего доверия
        trust_score = (reputation * 0.4) + (freshness * 0.3) + (authority * 0.3)
        
        result = SourceResult(
            source=source,
            trust_score=trust_score,
            reputation=reputation,
            freshness=freshness,
            authority=authority,
            is_trusted=trust_score > 0.7
        )
        
        # Сохранение в кэш
        self.source_cache[cache_key] = result
        
        return result
```

### Репутация источников

```python
def get_source_reputation(self, source: str) -> float:
    """Получение репутации источника"""
    if source in self.trusted_sources:
        return 0.9
        
    # Проверка по домену
    domain = self.extract_domain(source)
    
    if domain in self.source_reputation:
        return self.source_reputation[domain]
        
    # Расчет репутации на основе различных факторов
    reputation = self.calculate_domain_reputation(domain)
    self.source_reputation[domain] = reputation
    
    return reputation
    
def calculate_domain_reputation(self, domain: str) -> float:
    """Расчет репутации домена"""
    # Факторы репутации
    factors = {
        "domain_age": self.get_domain_age_score(domain),
        "ssl_certificate": self.get_ssl_score(domain),
        "content_quality": self.get_content_quality_score(domain),
        "user_ratings": self.get_user_rating_score(domain)
    }
    
    # Взвешенное среднее
    weights = {"domain_age": 0.2, "ssl_certificate": 0.2, "content_quality": 0.4, "user_ratings": 0.2}
    
    reputation = sum(factors[factor] * weights[factor] for factor in factors)
    
    return max(0.0, min(1.0, reputation))
```

## CrossValidator

### Кросс-валидация

```python
class CrossValidator:
    def __init__(self):
        self.cross_reference_sources = []
        self.validation_cache = {}
        
    async def validate(self, claim: str, context: dict) -> CrossValidationResult:
        """Кросс-валидация утверждения"""
        # 1. Поиск в RAG системе
        rag_results = await self.search_rag(claim)
        
        # 2. Поиск в графе знаний
        kg_results = await self.search_knowledge_graph(claim)
        
        # 3. Поиск в фактах
        fact_results = await self.search_facts(claim)
        
        # 4. Сравнение результатов
        consistency = self.compare_results(rag_results, kg_results, fact_results)
        
        # 5. Расчет достоверности
        confidence = self.calculate_cross_confidence(consistency, rag_results, kg_results, fact_results)
        
        return CrossValidationResult(
            claim=claim,
            consistency=consistency,
            confidence=confidence,
            sources=rag_results + kg_results + fact_results
        )
        
    def compare_results(self, rag_results: list, kg_results: list, fact_results: list) -> float:
        """Сравнение результатов из разных источников"""
        # Анализ согласованности
        agreements = 0
        total_comparisons = 0
        
        # Сравнение RAG и Knowledge Graph
        for rag_result in rag_results:
            for kg_result in kg_results:
                if self.results_agree(rag_result, kg_result):
                    agreements += 1
                total_comparisons += 1
                
        # Сравнение RAG и Facts
        for rag_result in rag_results:
            for fact_result in fact_results:
                if self.results_agree(rag_result, fact_result):
                    agreements += 1
                total_comparisons += 1
                
        # Сравнение Knowledge Graph и Facts
        for kg_result in kg_results:
            for fact_result in fact_results:
                if self.results_agree(kg_result, fact_result):
                    agreements += 1
                total_comparisons += 1
                
        return agreements / max(1, total_comparisons) if total_comparisons > 0 else 0.0
```

### Сравнение результатов

```python
def results_agree(self, result1: dict, result2: dict) -> bool:
    """Проверка согласованности двух результатов"""
    # Сравнение по ключевым аспектам
    key_aspects = ["entity", "relationship", "value", "timestamp"]
    
    agreements = 0
    total_aspects = 0
    
    for aspect in key_aspects:
        if aspect in result1 and aspect in result2:
            total_aspects += 1
            if self.aspect_values_match(result1[aspect], result2[aspect]):
                agreements += 1
                
    agreement_ratio = agreements / max(1, total_aspects)
    
    return agreement_ratio > 0.7  # 70% совпадение считается согласием
    
def aspect_values_match(self, value1: any, value2: any) -> bool:
    """Проверка совпадения значений аспекта"""
    if isinstance(value1, str) and isinstance(value2, str):
        # Сравнение строк с учетом синонимов
        return self.strings_match(value1, value2)
    elif isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
        # Сравнение чисел с погрешностью
        return abs(value1 - value2) / max(abs(value1), abs(value2)) < 0.1
    elif isinstance(value1, datetime) and isinstance(value2, datetime):
        # Сравнение дат с погрешностью
        return abs((value1 - value2).days) < 7
    else:
        return value1 == value2
```

## TruthMemory

### Память истины

```python
class TruthMemory:
    def __init__(self):
        self.verification_history = []
        self.corrected_claims = {}
        self.learning_data = []
        
    async def store_verification(self, original: str, verified: str, claims: list):
        """Сохранение результатов верификации"""
        verification_record = {
            "timestamp": datetime.now(),
            "original": original,
            "verified": verified,
            "claims": claims,
            "corrections": self.extract_corrections(original, verified)
        }
        
        self.verification_history.append(verification_record)
        
        # Обновление памяти исправленных утверждений
        for claim in claims:
            if claim.text != claim.original_text:
                self.corrected_claims[claim.original_text] = claim.text
                
        # Сохранение для обучения
        self.learning_data.append({
            "input": original,
            "output": verified,
            "claims": claims
        })
        
    def extract_corrections(self, original: str, verified: str) -> list:
        """Извлечение исправлений"""
        corrections = []
        
        # Сравнение оригинального и проверенного текста
        original_sentences = sent_tokenize(original)
        verified_sentences = sent_tokenize(verified)
        
        for orig_sent, ver_sent in zip(original_sentences, verified_sentences):
            if orig_sent != ver_sent:
                corrections.append({
                    "original": orig_sent,
                    "corrected": ver_sent,
                    "type": self.classify_correction_type(orig_sent, ver_sent)
                })
                
        return corrections
        
    def classify_correction_type(self, original: str, corrected: str) -> str:
        """Классификация типа исправления"""
        if "не знаю" in corrected.lower():
            return "unknown"
        elif "уточнение" in corrected.lower():
            return "clarification"
        elif "исправление" in corrected.lower():
            return "correction"
        elif "обновлено" in corrected.lower():
            return "update"
        else:
            return "general"
```

### Обучение на основе Truth Loop

```python
def learn_from_corrections(self):
    """Обучение на основе исправлений"""
    if not self.learning_data:
        return
        
    # Анализ типичных ошибок
    error_patterns = self.analyze_error_patterns()
    
    # Обновление моделей
    self.update_fact_checking_models(error_patterns)
    self.update_source_verification_models(error_patterns)
    self.update_cross_validation_models(error_patterns)
    
    # Очистка данных обучения
    self.learning_data = []
    
def analyze_error_patterns(self) -> dict:
    """Анализ типичных ошибок"""
    patterns = {
        "frequent_mistakes": [],
        "source_issues": [],
        "context_misunderstandings": []
    }
    
    for record in self.verification_history[-100:]:  # Последние 100 записей
        corrections = record["corrections"]
        
        for correction in corrections:
            if "не знаю" in correction["corrected"].lower():
                patterns["frequent_mistakes"].append(correction["original"])
            elif "источник" in correction["corrected"].lower():
                patterns["source_issues"].append(correction["original"])
                
    return patterns
```

## Интеграция с пайплайном

### Truth Loop в обработке запросов

```python
class Pipeline:
    async def process_with_truth_loop(self, prompt: str, context: dict):
        """Обработка запроса с Truth Loop"""
        # 1. Генерация ответа
        response = await self.generator.generate(prompt, context)
        
        # 2. Truth Loop верификация
        verification_result = await self.truth_verifier.verify_response(response, context)
        
        # 3. Обработка результатов
        if verification_result.confidence < 0.8:
            # Низкая уверенность - запрос уточнения
            clarification = await self.handle_low_confidence(verification_result, prompt, context)
            return clarification
        else:
            # Высокая уверенность - возврат проверенного ответа
            return verification_result.verified_response
            
    async def handle_low_confidence(self, verification_result: VerificationResult, prompt: str, context: dict) -> str:
        """Обработка низкой уверенности"""
        # 1. Поиск в RAG для дополнительного контекста
        rag_context = await self.rag_system.search(prompt, n_results=5)
        
        # 2. Повторная генерация с дополнительным контекстом
        enhanced_context = {**context, "rag_context": rag_context}
        enhanced_response = await self.generator.generate(prompt, enhanced_context)
        
        # 3. Повторная верификация
        enhanced_verification = await self.truth_verifier.verify_response(enhanced_response, enhanced_context)
        
        if enhanced_verification.confidence > 0.8:
            return enhanced_verification.verified_response
        else:
            # Все еще низкая уверенность - честный ответ
            return "Я не уверен в точности этого ответа. Пожалуйста, проверьте информацию из надежных источников."
```

## Future улучшения

### Планы развития

1. **Advanced Fact Checking**
   - Интеграция с научными базами данных
   - Проверка через блокчейн
   - Real-time fact checking

2. **Source Intelligence**
   - Анализ скрытых предвзятостей
   - Обнаружение фейковых новостей
   - Проверка через экспертов

3. **Predictive Verification**
   - Прогнозирование достоверности
   - Предиктивная проверка
   - Проактивное выявление ошибок

4. **Multi-modal Verification**
   - Проверка через изображения
   - Аудио-фактчекинг
   - Видео-верификация

5. **Community Verification**
   - Коллективная проверка
   - Crowd-sourced fact checking
   - Community feedback integration