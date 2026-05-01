import React, { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { motion, AnimatePresence } from 'framer-motion';

const thoughtIcons = {
  safety_check: '🛡️',
  intent_classification: '🎯',
  memory_search: '🔍',
  fact_retrieval: '📝',
  episode_recall: '📜',
  procedure_application: '🔧',
  emotion_update: '😊',
  strategy_decision: '🧠',
  model_selection: '🤖',
  claim_extraction: '📋',
  claim_verification: '✅',
  memory_storage: '💾',
  persona_adjustment: '👤',
  event_emission: '📡'
};

const thoughtColors = {
  safety_check: 'border-blue-500 bg-blue-500/10',
  intent_classification: 'border-cyan-500 bg-cyan-500/10',
  memory_search: 'border-green-500 bg-green-500/10',
  fact_retrieval: 'border-emerald-500 bg-emerald-500/10',
  episode_recall: 'border-teal-500 bg-teal-500/10',
  procedure_application: 'border-yellow-500 bg-yellow-500/10',
  emotion_update: 'border-pink-500 bg-pink-500/10',
  strategy_decision: 'border-purple-500 bg-purple-500/10',
  model_selection: 'border-orange-500 bg-orange-500/10',
  claim_extraction: 'border-indigo-500 bg-indigo-500/10',
  claim_verification: 'border-red-500 bg-red-500/10',
  memory_storage: 'border-violet-500 bg-violet-500/10',
  persona_adjustment: 'border-rose-500 bg-rose-500/10',
  event_emission: 'border-amber-500 bg-amber-500/10'
};

const confidenceColors = (confidence) => {
  if (confidence >= 0.8) return 'text-green-400';
  if (confidence >= 0.6) return 'text-yellow-400';
  if (confidence >= 0.4) return 'text-orange-400';
  return 'text-red-400';
};

const thoughtVariants = {
  hidden: { opacity: 0, x: -20, height: 0 },
  visible: { 
    opacity: 1, 
    x: 0, 
    height: 'auto',
    transition: { type: 'spring', stiffness: 300, damping: 30 }
  },
  exit: { 
    opacity: 0, 
    x: -20, 
    height: 0,
    transition: { duration: 0.2 }
  }
};

export function ThoughtStream({ 
  thoughts = [], 
  maxThoughts = 20,
  filter = null,
  autoScroll = true 
}) {
  const [displayedThoughts, setDisplayedThoughts] = useState([]);
  const scrollRef = useRef(null);

  useEffect(() => {
    // Фильтрация мыслей
    let filtered = thoughts;
    if (filter) {
      filtered = thoughts.filter(t => t.type === filter);
    }
    
    // Ограничение количества
    const limited = filtered.slice(-maxThoughts);
    setDisplayedThoughts(limited);
  }, [thoughts, filter, maxThoughts]);

  useEffect(() => {
    // Автопрокрутка
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [displayedThoughts, autoScroll]);

  const formatTime = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('ru-RU', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit',
        fractionDigits: 2
      });
    } catch {
      return '';
    }
  };

  const getConfidenceBar = (confidence) => {
    const width = Math.round(confidence * 100);
    const colorClass = confidenceColors(confidence);
    
    return (
      <div className="flex items-center gap-2 mt-1">
        <div className="flex-1 h-1 bg-gray-700 rounded-full overflow-hidden">
          <motion.div 
            className={`h-full ${colorClass.replace('text-', 'bg-')}`}
            initial={{ width: 0 }}
            animate={{ width: `${width}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
        <span className={`text-xs ${colorClass} whitespace-nowrap`}>
          {Math.round(confidence * 100)}%
        </span>
      </div>
    );
  };

  return (
    <Card className="w-full bg-gray-900/50 border-gray-700 h-full flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg text-white">
            🧠 Поток мыслей
          </CardTitle>
          <span className="text-xs text-gray-400">
            {displayedThoughts.length} мыслей
          </span>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden flex flex-col">
        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto space-y-2 pr-2 scrollbar-thin scrollbar-thumb-gray-600"
        >
          <AnimatePresence mode="popLayout">
            {displayedThoughts.map((thought, index) => {
              const icon = thoughtIcons[thought.type] || '💭';
              const colorClass = thoughtColors[thought.type] || 'border-gray-500 bg-gray-500/10';
              
              return (
                <motion.div
                  key={thought.id || index}
                  variants={thoughtVariants}
                  initial="hidden"
                  animate="visible"
                  exit="exit"
                  layout
                  className={`
                    p-3 rounded-lg border-l-4 bg-gray-800/50
                    ${colorClass}
                    hover:bg-gray-800 transition-colors
                  `}
                >
                  <div className="flex items-start gap-2">
                    <span className="text-lg flex-shrink-0">{icon}</span>
                    
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-white break-words">
                        {thought.content}
                      </div>
                      
                      <div className="flex items-center justify-between mt-2">
                        <span className="text-xs text-gray-500">
                          {formatTime(thought.timestamp)}
                        </span>
                        
                        {thought.confidence !== undefined && (
                          <div className="flex items-center gap-1">
                            {getConfidenceBar(thought.confidence)}
                          </div>
                        )}
                      </div>

                      {/* Sources */}
                      {thought.sources && thought.sources.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {thought.sources.map((source, i) => (
                            <span 
                              key={i}
                              className="text-xs px-2 py-0.5 bg-gray-700 text-gray-300 rounded"
                            >
                              {source}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Metadata */}
                      {thought.metadata && Object.keys(thought.metadata).length > 0 && (
                        <details className="mt-2">
                          <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300">
                            Детали
                          </summary>
                          <div className="mt-1 p-2 bg-gray-900 rounded text-xs text-gray-400">
                            {Object.entries(thought.metadata).map(([key, value]) => (
                              <div key={key} className="flex justify-between py-0.5">
                                <span>{key}:</span>
                                <span className="text-gray-300">
                                  {typeof value === 'boolean' 
                                    ? (value ? '✅' : '❌') 
                                    : typeof value === 'object'
                                    ? JSON.stringify(value)
                                    : value}
                                </span>
                              </div>
                            ))}
                          </div>
                        </details>
                      )}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>

          {displayedThoughts.length === 0 && (
            <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
              Пока нет мыслей. Отправьте запрос для начала.
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default ThoughtStream;