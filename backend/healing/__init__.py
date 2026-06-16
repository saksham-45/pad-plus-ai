"""
🧬 Self-Healing Module для PAD+ AI

Основан на архитектурных принципах HEALER, адаптированных под runtime:
- Мониторинг pipeline через подписку на TraceCollector
- 5 детекторов проблем (BaseDetector ABC)
- Config-driven remediation (без AST)
- Замкнутый MetaLearner
"""
