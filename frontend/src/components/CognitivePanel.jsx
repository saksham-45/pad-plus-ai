import React from 'react';
import './CognitivePanel.css';

/**
 * CognitivePanel — компонент для отображения когнитивных мета-данных
 * 
 * Показывает:
 * - Стратегию обработки
 * - Уверенность системы
 * - Использование памяти (RAG, факты, эпизоды)
 * - Статус верификации (TruthLoop)
 * - Время выполнения
 * - Эмоциональное состояние
 */
const CognitivePanel = ({ 
  cognitive, 
  memory, 
  emotion, 
  truth, 
  xray, 
  meta,
  execution_time_ms 
}) => {
  // Определяем стратегию из xray или cognitive
  const strategy = xray?.strategy || cognitive?.strategy || 'unknown';
  const strategyDescription = xray?.strategy_description || getStrategyDescription(strategy);
  
  // Уверенность
  const confidence = cognitive?.confidence || 0;
  const confidencePercent = Math.round(confidence * 100);
  
  // Health score
  const healthScore = cognitive?.health_score || 0;
  const healthPercent = Math.round(healthScore * 100);
  
  // Время выполнения
  const execTime = execution_time_ms || cognitive?.execution_time_ms || 0;
  
  // Интенд
  const intent = meta?.intent || 'unknown';
  
  // Статус верификации
  const truthStatus = truth?.status || 'unknown';
  const truthConfidence = truth?.confidence || 0;
  
  // Использование памяти
  const memoryUsage = xray?.memory_usage || {
    rag: memory?.rag_used || false,
    facts: (memory?.facts_used || 0) > 0,
    episodic: memory?.episode_id ? true : false,
    procedure: memory?.procedure_used ? true : false
  };
  
  // Эмоции
  const emotionStyle = emotion?.style || {};
  const tone = emotionStyle.tone || 'neutral';
  const verbosity = emotionStyle.verbosity || 'moderate';
  
  // Источники
  const sources = memory?.sources || {};
  const ragCount = sources.rag?.count || 0;
  const factsCount = sources.facts?.count || 0;
  const episodicCount = sources.episodic?.count || 0;
  
  return (
    <div className="cognitive-panel">
      <div className="cognitive-panel-header">
        <h4>🧠 Когнитивные метрики</h4>
      </div>
      
      <div className="cognitive-panel-content">
        {/* Стратегия */}
        <div className="metric-row">
          <span className="metric-label">Стратегия:</span>
          <span className="metric-value strategy-value">
            {strategyDescription}
          </span>
        </div>
        
        {/* Уверенность */}
        <div className="metric-row">
          <span className="metric-label">Уверенность:</span>
          <div className="confidence-bar-container">
            <div 
              className="confidence-bar-fill" 
              style={{ width: `${confidencePercent}%` }}
            />
          </div>
          <span className="metric-value">{confidencePercent}%</span>
        </div>
        
        {/* Health Score */}
        <div className="metric-row">
          <span className="metric-label">Здоровье системы:</span>
          <div className="health-bar-container">
            <div 
              className="health-bar-fill" 
              style={{ width: `${healthPercent}%` }}
            />
          </div>
          <span className="metric-value">{healthPercent}%</span>
        </div>
        
        {/* Интент */}
        <div className="metric-row">
          <span className="metric-label">Намерение:</span>
          <span className="metric-value intent-value">{translateIntent(intent)}</span>
        </div>
        
        {/* Верификация */}
        {truth && (
          <div className="metric-row">
            <span className="metric-label">Верификация:</span>
            <span className={`truth-status ${truthStatus}`}>
              {translateTruthStatus(truthStatus)}
            </span>
            <span className="metric-value small">
              ({Math.round(truthConfidence * 100)}%)
            </span>
          </div>
        )}
        
        {/* Использование памяти */}
        <div className="memory-section">
          <div className="metric-label">Память:</div>
          <div className="memory-indicators">
            {memoryUsage.rag && (
              <span className="memory-badge rag">
                📚 RAG: {ragCount} ист.
              </span>
            )}
            {memoryUsage.facts && (
              <span className="memory-badge facts">
                📝 Факты: {factsCount}
              </span>
            )}
            {memoryUsage.episodic && (
              <span className="memory-badge episodic">
                📜 Эпизоды: {episodicCount}
              </span>
            )}
            {memoryUsage.procedure && (
              <span className="memory-badge procedure">
                🔧 Процедура
              </span>
            )}
          </div>
        </div>
        
        {/* Эмоции */}
        <div className="metric-row">
          <span className="metric-label">Тон:</span>
          <span className="metric-value tone-value">{translateTone(tone)}</span>
        </div>
        
        {/* Время выполнения */}
        <div className="metric-row">
          <span className="metric-label">Время:</span>
          <span className="metric-value time-value">{Math.round(execTime)}ms</span>
        </div>
      </div>
    </div>
  );
};

// Вспомогательные функции
function getStrategyDescription(strategy) {
  const descriptions = {
    'simple': 'Прямая генерация',
    'retrieval': 'Поиск и синтез',
    'reasoning': 'Логический анализ',
    'creative': 'Творческая генерация',
    'analytical': 'Аналитическая обработка'
  };
  return descriptions[strategy] || strategy;
}

function translateIntent(intent) {
  const translations = {
    'chat_general': 'Общение',
    'question_factual': 'Фактологический вопрос',
    'question_philosophical': 'Философский вопрос',
    'task_creative': 'Творческая задача',
    'task_analytical': 'Аналитическая задача',
    'memory_query': 'Запрос к памяти'
  };
  return translations[intent] || intent;
}

function translateTruthStatus(status) {
  const translations = {
    'verified': '✅ Проверено',
    'partial': '⚠️ Частично',
    'unverified': '❌ Не проверено'
  };
  return translations[status] || status;
}

function translateTone(tone) {
  const translations = {
    'friendly': 'Дружелюбный',
    'serious': 'Серьёзный',
    'neutral': 'Нейтральный',
    'confident': 'Уверенный',
    'uncertain': 'Осторожный'
  };
  return translations[tone] || tone;
}

export default CognitivePanel;