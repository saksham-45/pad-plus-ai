import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { motion, AnimatePresence } from 'framer-motion';

const pipelineStages = [
  { 
    id: 'safety', 
    label: 'Safety', 
    icon: '🛡️', 
    color: 'bg-blue-600',
    description: 'Проверка безопасности'
  },
  { 
    id: 'intent', 
    label: 'Intent', 
    icon: '🎯', 
    color: 'bg-cyan-600',
    description: 'Классификация намерения'
  },
  { 
    id: 'retrieve', 
    label: 'Retrieve', 
    icon: '🔍', 
    color: 'bg-green-600',
    description: 'Поиск в памяти'
  },
  { 
    id: 'persona', 
    label: 'Persona', 
    icon: '👤', 
    color: 'bg-yellow-600',
    description: 'Контекст личности'
  },
  { 
    id: 'generate', 
    label: 'Generate', 
    icon: '🤖', 
    color: 'bg-orange-600',
    description: 'Генерация ответа'
  },
  { 
    id: 'verify', 
    label: 'Verify', 
    icon: '✅', 
    color: 'bg-red-600',
    description: 'Верификация'
  },
  { 
    id: 'remember', 
    label: 'Remember', 
    icon: '💾', 
    color: 'bg-purple-600',
    description: 'Сохранение'
  },
  { 
    id: 'emit', 
    label: 'Emit', 
    icon: '📡', 
    color: 'bg-pink-600',
    description: 'События'
  }
];

const stageVariants = {
  idle: { 
    scale: 1, 
    opacity: 0.5,
    boxShadow: '0 0 0 0 rgba(0,0,0,0)'
  },
  active: { 
    scale: 1.15, 
    opacity: 1,
    boxShadow: '0 0 20px currentColor'
  },
  completed: { 
    scale: 1, 
    opacity: 0.8,
    boxShadow: '0 0 10px currentColor'
  },
  error: { 
    scale: 1, 
    opacity: 0.6,
    boxShadow: '0 0 15px rgba(239,68,68,0.5)',
    borderColor: 'rgb(239,68,68)'
  }
};

const connectorVariants = {
  idle: { opacity: 0.3, pathLength: 0 },
  active: { opacity: 1, pathLength: 1 },
  completed: { opacity: 0.7, pathLength: 1 }
};

export function XRayPipeline({ 
  activeStage = null, 
  completedStages = [], 
  stageData = {},
  status = 'idle',
  error = null
}) {
  const [hoveredStage, setHoveredStage] = useState(null);

  const getStageStatus = (stageId) => {
    if (error && stageId === activeStage) return 'error';
    if (activeStage === stageId) return 'active';
    if (completedStages.includes(stageId)) return 'completed';
    return 'idle';
  };

  const getConnectorStatus = (index) => {
    if (completedStages.length > index + 1) return 'completed';
    if (activeStage && pipelineStages.findIndex(s => s.id === activeStage) > index) 
      return 'active';
    return 'idle';
  };

  return (
    <Card className="w-full bg-gray-900/50 border-gray-700">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg text-white">
            🔬 X-Ray Pipeline
          </CardTitle>
          {status !== 'idle' && (
            <span className={`text-xs px-2 py-1 rounded ${
              status === 'processing' 
                ? 'bg-blue-600/20 text-blue-400' 
                : status === 'success'
                ? 'bg-green-600/20 text-green-400'
                : 'bg-red-600/20 text-red-400'
            }`}>
              {status === 'processing' && '⚡ Processing'}
              {status === 'success' && '✅ Complete'}
              {status === 'error' && '❌ Error'}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {/* Pipeline Flow */}
        <div className="flex items-center justify-between gap-1 overflow-x-auto pb-4">
          {pipelineStages.map((stage, index) => {
            const stageStatus = getStageStatus(stage.id);
            const connectorStatus = getConnectorStatus(index);
            const isHovered = hoveredStage === stage.id;
            const data = stageData[stage.id];

            return (
              <div 
                key={stage.id} 
                className="flex items-center flex-1 min-w-0"
              >
                {/* Stage Node */}
                <div className="relative">
                  <motion.div
                    className={`
                      relative flex items-center justify-center 
                      w-12 h-12 rounded-xl text-xl font-bold
                      transition-colors cursor-pointer
                      ${stage.color}
                      ${stageStatus === 'active' ? 'ring-2 ring-white ring-offset-2 ring-offset-gray-900' : ''}
                    `}
                    variants={stageVariants}
                    animate={stageStatus}
                    initial="idle"
                    onHoverStart={() => setHoveredStage(stage.id)}
                    onHoverEnd={() => setHoveredStage(null)}
                    style={{ color: stageStatus === 'error' ? '#ef4444' : 'inherit' }}
                  >
                    <span className="text-lg">{stage.icon}</span>
                    
                    {/* Duration badge */}
                    {data?.duration_ms && (
                      <span className="absolute -bottom-4 text-xs text-gray-400 whitespace-nowrap">
                        {data.duration_ms}ms
                      </span>
                    )}
                  </motion.div>

                  {/* Tooltip */}
                  <AnimatePresence>
                    {isHovered && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                        className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 
                                   px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg 
                                   text-xs text-white whitespace-nowrap z-10"
                      >
                        <div className="font-semibold mb-1">
                          {stage.label}
                        </div>
                        <div className="text-gray-400">
                          {stage.description}
                        </div>
                        {data && Object.keys(data).length > 0 && (
                          <div className="mt-2 pt-2 border-t border-gray-600">
                            {Object.entries(data).map(([key, value]) => (
                              <div key={key} className="text-gray-300">
                                {key}: {typeof value === 'boolean' 
                                  ? (value ? '✅' : '❌') 
                                  : value}
                              </div>
                            ))}
                          </div>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Connector */}
                {index < pipelineStages.length - 1 && (
                  <motion.div
                    className={`flex-1 h-1 mx-1 rounded ${
                      connectorStatus === 'completed' 
                        ? 'bg-gradient-to-r from-gray-600 to-primary'
                        : connectorStatus === 'active'
                        ? 'bg-gradient-to-r from-gray-600 to-primary animate-pulse'
                        : 'bg-gray-700'
                    }`}
                    variants={connectorVariants}
                    animate={connectorStatus}
                    initial="idle"
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Error Display */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 p-3 bg-red-900/30 border border-red-800 rounded-lg"
          >
            <div className="flex items-center gap-2 text-red-400 text-sm">
              <span>❌</span>
              <span>{error}</span>
            </div>
          </motion.div>
        )}

        {/* Request Info */}
        {stageData.request_id && (
          <div className="mt-4 text-xs text-gray-500">
            Request ID: <code className="text-gray-400">{stageData.request_id}</code>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default XRayPipeline;