import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { motion, AnimatePresence } from 'framer-motion';

const decisionIcons = {
  model_selection: '🤖',
  strategy: '🎯',
  memory_action: '💾',
  confidence_check: '✅',
  fallback: '⚠️',
  reasoning: '🧠',
  response_filter: '🛡️'
};

export function DecisionLog({ decisions = [], maxItems = 15 }) {
  const displayDecisions = decisions.slice(-maxItems);
  
  return (
    <Card className="w-full bg-gray-900/50 border-gray-700 h-full flex flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg text-white">
          🎯 Журнал решений
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden">
        <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2">
          <AnimatePresence mode="popLayout">
            {displayDecisions.map((decision, index) => {
              const icon = decisionIcons[decision.type] || '❓';
              
              return (
                <motion.div
                  key={decision.id || index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="p-2 bg-gray-800/50 rounded-lg border-l-2 border-blue-500 text-sm"
                >
                  <div className="flex items-start gap-2">
                    <span className="text-lg">{icon}</span>
                    <div className="flex-1">
                      <div className="text-white">{decision.description}</div>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-xs text-gray-500">
                          {new Date(decision.timestamp).toLocaleTimeString('ru-RU')}
                        </span>
                        {decision.confidence !== undefined && (
                          <span className={`text-xs ${
                            decision.confidence > 0.7 ? 'text-green-400' : 
                            decision.confidence > 0.4 ? 'text-yellow-400' : 'text-red-400'
                          }`}>
                            {Math.round(decision.confidence * 100)}% уверенности
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
          
          {displayDecisions.length === 0 && (
            <div className="flex items-center justify-center h-24 text-gray-500 text-sm">
              Пока нет принятых решений
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}