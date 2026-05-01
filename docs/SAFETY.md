# Система Безопасности

Этот документ описывает систему безопасности в PAD+ AI.

## Обзор

Система безопасности обеспечивает:

- Фильтрацию опасного контента
- Контроль этических норм
- Защиту от вредоносных запросов
- Мониторинг безопасности
- Автоматическое реагирование на угрозы

## Архитектура безопасности

### Компоненты

1. **SafetyFilter** - Основной фильтр безопасности
2. **EthicsController** - Контроллер этических норм
3. **ContentModerator** - Модератор контента
4. **ThreatDetector** - Детектор угроз
5. **SafetyMonitor** - Монитор безопасности

### Уровни безопасности

```
Safety System
├── Level 1: Input Filtering (Фильтрация ввода)
│   ├── Content Analysis
│   ├── Intent Classification
│   └── Threat Detection
├── Level 2: Response Control (Контроль ответов)
│   ├── Output Filtering
│   ├── Ethics Validation
│   └── Response Modification
├── Level 3: Behavioral Monitoring (Мониторинг поведения)
│   ├── Pattern Analysis
│   ├── Anomaly Detection
│   └── Risk Assessment
└── Level 4: System Protection (Защита системы)
    ├── Access Control
    ├── Data Protection
    └── Emergency Response
```

## SafetyFilter

### Основной фильтр безопасности

```python
class SafetyFilter:
    def __init__(self):
        self.content_moderator = ContentModerator()
        self.ethics_controller = EthicsController()
        self.threat_detector = ThreatDetector()
        self.safety_rules = self.load_safety_rules()
        self.blocked_patterns = self.load_blocked_patterns()
        
    async def filter_input(self, user_input: str, context: dict) -> SafetyResult:
        """Фильтрация пользовательского ввода"""
        # 1. Анализ контента
        content_analysis = await self.content_moderator.analyze_content(user_input)
        
        # 2. Проверка на угрозы
        threat_analysis = await self.threat_detector.detect_threats(user_input, context)
        
        # 3. Этическая проверка
        ethics_analysis = await self.ethics_controller.validate_ethics(user_input, context)
        
        # 4. Комплексная оценка безопасности
        safety_score = self.calculate_safety_score(content_analysis, threat_analysis, ethics_analysis)
        
        # 5. Принятие решения
        if safety_score < 0.3:  # Высокий риск
            return SafetyResult(
                is_safe=False,
                action="block",
                reason="High risk content detected",
                details={"content_analysis": content_analysis, "threat_analysis": threat_analysis}
            )
        elif safety_score < 0.7:  # Средний риск
            return SafetyResult(
                is_safe=False,
                action="modify",
                reason="Moderate risk content",
                details={"content_analysis": content_analysis, "threat_analysis": threat_analysis}
            )
        else:  # Низкий риск
            return SafetyResult(
                is_safe=True,
                action="allow",
                reason="Content is safe",
                details={"safety_score": safety_score}
            )
            
    def calculate_safety_score(self, content_analysis: dict, threat_analysis: dict, ethics_analysis: dict) -> float:
        """Расчет общего показателя безопасности"""
        # Веса для разных типов анализа
        weights = {
            "content": 0.4,
            "threat": 0.4,
            "ethics": 0.2
        }
        
        # Расчет взвешенного среднего
        content_score = 1.0 - content_analysis.get("risk_score", 0.0)
        threat_score = 1.0 - threat_analysis.get("threat_level", 0.0)
        ethics_score = ethics_analysis.get("ethics_score", 1.0)
        
        safety_score = (
            content_score * weights["content"] +
            threat_score * weights["threat"] +
            ethics_score * weights["ethics"]
        )
        
        return max(0.0, min(1.0, safety_score))
```

### Правила безопасности

```python
def load_safety_rules(self) -> dict:
    """Загрузка правил безопасности"""
    return {
        "prohibited_topics": [
            "насилие", "терроризм", "экстремизм", "пропаганда ненависти",
            "расизм", "дискриминация", "жестокое обращение с животными",
            "суицид", "самоповреждение", "наркотики", "оружие"
        ],
        "restricted_topics": [
            "политика", "религия", "сексуальные отношения", "алкоголь",
            "азартные игры", "финансовые пирамиды"
        ],
        "ethical_principles": [
            "не причинять вред",
            "уважать личные границы",
            "поддерживать честность",
            "способствовать благополучию",
            "избегать предвзятости"
        ],
        "response_guidelines": {
            "refuse_requests": [
                "создание вредоносного кода",
                "обман или манипуляция",
                "нарушение приватности",
                "распространение ложной информации"
            ],
            "redirect_conversations": [
                "суицидальные мысли",
                "наркотическая зависимость",
                "жестокое обращение"
            ]
        }
    }
```

## ContentModerator

### Модератор контента

```python
class ContentModerator:
    def __init__(self):
        self.toxicity_classifier = self.load_toxicity_model()
        self.hate_speech_detector = self.load_hate_speech_model()
        self.violence_detector = self.load_violence_model()
        self.pii_detector = PII_Detector()
        
    async def analyze_content(self, text: str) -> dict:
        """Анализ контента на предмет опасности"""
        analysis = {
            "toxicity_score": 0.0,
            "hate_speech_score": 0.0,
            "violence_score": 0.0,
            "pii_risk": 0.0,
            "overall_risk": 0.0,
            "detected_issues": []
        }
        
        # 1. Проверка токсичности
        analysis["toxicity_score"] = await self.check_toxicity(text)
        
        # 2. Проверка hate speech
        analysis["hate_speech_score"] = await self.check_hate_speech(text)
        
        # 3. Проверка насилия
        analysis["violence_score"] = await self.check_violence(text)
        
        # 4. Проверка персональных данных
        analysis["pii_risk"] = await self.check_pii(text)
        
        # 5. Расчет общего риска
        analysis["overall_risk"] = self.calculate_overall_risk(analysis)
        
        # 6. Сбор проблем
        analysis["detected_issues"] = self.collect_issues(analysis)
        
        return analysis
        
    async def check_toxicity(self, text: str) -> float:
        """Проверка токсичности текста"""
        # Использование предобученной модели
        try:
            result = await self.toxicity_classifier.predict(text)
            return result.get("toxicity", 0.0)
        except Exception as e:
            logger.error(f"Toxicity check failed: {e}")
            return 0.0
            
    async def check_hate_speech(self, text: str) -> float:
        """Проверка hate speech"""
        try:
            result = await self.hate_speech_detector.predict(text)
            return result.get("hate_speech_score", 0.0)
        except Exception as e:
            logger.error(f"Hate speech check failed: {e}")
            return 0.0
```

### Обнаружение персональных данных

```python
class PII_Detector:
    def __init__(self):
        self.pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b',
            "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "address": r'\b\d+\s+[A-Za-z\s]+\b'
        }
        
    async def check_pii(self, text: str) -> float:
        """Проверка наличия персональных данных"""
        pii_risk = 0.0
        detected_pii = []
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                detected_pii.extend(matches)
                pii_risk += 0.2  # Каждый тип PII увеличивает риск
                
        return min(1.0, pii_risk)
```

## EthicsController

### Контроллер этических норм

```python
class EthicsController:
    def __init__(self):
        self.ethical_principles = self.load_ethical_principles()
        self.bias_detector = BiasDetector()
        self.fairness_checker = FairnessChecker()
        
    async def validate_ethics(self, text: str, context: dict) -> dict:
        """Этическая валидация текста"""
        ethics_result = {
            "ethics_score": 1.0,
            "bias_score": 0.0,
            "fairness_score": 1.0,
            "ethical_issues": [],
            "principles_violated": []
        }
        
        # 1. Проверка на предвзятость
        bias_result = await self.bias_detector.detect_bias(text, context)
        ethics_result["bias_score"] = bias_result["bias_score"]
        
        # 2. Проверка на справедливость
        fairness_result = await self.fairness_checker.check_fairness(text, context)
        ethics_result["fairness_score"] = fairness_result["fairness_score"]
        
        # 3. Проверка этических принципов
        principle_violations = await self.check_ethical_principles(text, context)
        ethics_result["principles_violated"] = principle_violations
        
        # 4. Расчет общего этического балла
        ethics_result["ethics_score"] = self.calculate_ethics_score(ethics_result)
        
        # 5. Сбор этических проблем
        ethics_result["ethical_issues"] = self.collect_ethical_issues(ethics_result)
        
        return ethics_result
        
    async def check_ethical_principles(self, text: str, context: dict) -> list:
        """Проверка нарушения этических принципов"""
        violations = []
        
        # Проверка принципа "не причинять вред"
        if await self.check_harm_principle(text):
            violations.append("harm_principle_violation")
            
        # Проверка принципа "честность"
        if await self.check_honesty_principle(text, context):
            violations.append("honesty_principle_violation")
            
        # Проверка принципа "уважение"
        if await self.check_respect_principle(text):
            violations.append("respect_principle_violation")
            
        return violations
        
    async def check_harm_principle(self, text: str) -> bool:
        """Проверка принципа "не причинять вред"""
        harmful_keywords = [
            "убить", "покончить с собой", "навредить", "обмануть",
            "вред", "опасность", "опасно", "вредный"
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in harmful_keywords)
```

### Детектор предвзятости

```python
class BiasDetector:
    def __init__(self):
        self.bias_keywords = {
            "gender_bias": ["мужчина", "женщина", "парень", "девушка"],
            "racial_bias": ["раса", "национальность", "этнический"],
            "age_bias": ["старый", "молодой", "возраст"],
            "disability_bias": ["инвалид", "больной", "немощный"]
        }
        
    async def detect_bias(self, text: str, context: dict) -> dict:
        """Обнаружение предвзятости в тексте"""
        bias_analysis = {
            "bias_score": 0.0,
            "bias_types": [],
            "biased_terms": [],
            "context_analysis": {}
        }
        
        text_lower = text.lower()
        
        for bias_type, keywords in self.bias_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    bias_analysis["bias_types"].append(bias_type)
                    bias_analysis["biased_terms"].append(keyword)
                    bias_analysis["bias_score"] += 0.1
                    
        # Нормализация балла
        bias_analysis["bias_score"] = min(1.0, bias_analysis["bias_score"])
        
        return bias_analysis
```

## ThreatDetector

### Детектор угроз

```python
class ThreatDetector:
    def __init__(self):
        self.threat_patterns = self.load_threat_patterns()
        self.malicious_intent_classifier = self.load_malicious_intent_model()
        
    def load_threat_patterns(self) -> dict:
        """Загрузка паттернов угроз"""
        return {
            "malware_creation": [
                "создай вирус", "напиши троян", "сделай вредоносный код",
                "создать malware", "написать ransomware"
            ],
            "phishing": [
                "создай фишинг", "напиши фишинговое письмо",
                "сделай фишинговую страницу"
            ],
            "data_theft": [
                "украсть данные", "взломать базу данных",
                "получить доступ без разрешения"
            ],
            "social_engineering": [
                "обмануть", "манипулировать", "ввести в заблуждение"
            ]
        }
        
    async def detect_threats(self, text: str, context: dict) -> dict:
        """Обнаружение угроз в тексте"""
        threat_analysis = {
            "threat_level": 0.0,
            "threat_types": [],
            "malicious_score": 0.0,
            "suspicious_patterns": []
        }
        
        # 1. Проверка по паттернам
        for threat_type, patterns in self.threat_patterns.items():
            for pattern in patterns:
                if pattern in text.lower():
                    threat_analysis["threat_types"].append(threat_type)
                    threat_analysis["suspicious_patterns"].append(pattern)
                    threat_analysis["threat_level"] += 0.3
                    
        # 2. Проверка на злонамеренные намерения
        malicious_score = await self.check_malicious_intent(text, context)
        threat_analysis["malicious_score"] = malicious_score
        threat_analysis["threat_level"] += malicious_score * 0.5
        
        # 3. Нормализация уровня угрозы
        threat_analysis["threat_level"] = min(1.0, threat_analysis["threat_level"])
        
        return threat_analysis
        
    async def check_malicious_intent(self, text: str, context: dict) -> float:
        """Проверка на злонамеренные намерения"""
        try:
            result = await self.malicious_intent_classifier.predict(text)
            return result.get("malicious_score", 0.0)
        except Exception as e:
            logger.error(f"Malicious intent check failed: {e}")
            return 0.0
```

## SafetyMonitor

### Монитор безопасности

```python
class SafetyMonitor:
    def __init__(self):
        self.safety_logs = []
        self.risk_thresholds = self.load_risk_thresholds()
        self.alert_system = AlertSystem()
        
    async def monitor_safety(self, safety_result: SafetyResult, context: dict):
        """Мониторинг безопасности системы"""
        # 1. Логирование результата
        self.log_safety_event(safety_result, context)
        
        # 2. Анализ рисков
        risk_level = self.assess_risk_level(safety_result)
        
        # 3. Проверка на аномалии
        if await self.detect_anomalies(safety_result, context):
            await self.trigger_anomaly_alert(safety_result, context)
            
        # 4. Проверка порогов безопасности
        if risk_level > self.risk_thresholds["high"]:
            await self.trigger_high_risk_alert(safety_result, context)
            
        # 5. Обновление статистики безопасности
        await self.update_safety_statistics(safety_result)
        
    def log_safety_event(self, safety_result: SafetyResult, context: dict):
        """Логирование события безопасности"""
        event = {
            "timestamp": datetime.now(),
            "user_id": context.get("user_id"),
            "action": safety_result.action,
            "reason": safety_result.reason,
            "safety_score": safety_result.details.get("safety_score", 0.0),
            "detected_issues": safety_result.details.get("detected_issues", [])
        }
        
        self.safety_logs.append(event)
        
        # Ограничение размера логов
        if len(self.safety_logs) > 10000:
            self.safety_logs.pop(0)
            
    async def detect_anomalies(self, safety_result: SafetyResult, context: dict) -> bool:
        """Обнаружение аномалий в поведении"""
        # Анализ частоты нарушений
        recent_violations = [
            log for log in self.safety_logs[-100:] 
            if log["action"] in ["block", "modify"]
        ]
        
        violation_rate = len(recent_violations) / 100
        
        # Проверка аномальной активности
        if violation_rate > 0.3:  # Более 30% нарушений
            return True
            
        # Проверка аномальных запросов
        if safety_result.action == "block" and context.get("request_frequency", 0) > 10:
            return True
            
        return False
```

### Система оповещений

```python
class AlertSystem:
    def __init__(self):
        self.alert_handlers = []
        self.alert_thresholds = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.8
        }
        
    async def trigger_alert(self, alert_type: str, message: str, context: dict):
        """Триггер оповещения"""
        alert = {
            "type": alert_type,
            "message": message,
            "timestamp": datetime.now(),
            "context": context
        }
        
        # Отправка оповещения всем обработчикам
        for handler in self.alert_handlers:
            try:
                await handler.handle_alert(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
                
    async def handle_safety_violation(self, safety_result: SafetyResult, context: dict):
        """Обработка нарушения безопасности"""
        if safety_result.action == "block":
            await self.trigger_alert(
                "security_violation",
                f"Blocked high-risk content: {safety_result.reason}",
                context
            )
        elif safety_result.action == "modify":
            await self.trigger_alert(
                "content_modification",
                f"Modified moderate-risk content: {safety_result.reason}",
                context
            )
```

## Future улучшения

### Планы развития

1. **Advanced Threat Detection**
   - Deep learning for threat detection
   - Behavioral pattern analysis
   - Real-time threat assessment

2. **Ethical AI Enhancement**
   - Advanced bias detection
   - Fairness optimization
   - Ethical decision making

3. **Privacy Protection**
   - Differential privacy
   - Data anonymization
   - Privacy-preserving ML

4. **Security Automation**
   - Automated response systems
   - Threat intelligence integration
   - Security orchestration

5. **Compliance Management**
   - Regulatory compliance checking
   - Audit trail management
   - Policy enforcement automation