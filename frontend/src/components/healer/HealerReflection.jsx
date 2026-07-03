import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';

export function HealerReflection({ learnings = [], changes = [], onRollback }) {
  const [expandedLearning, setExpandedLearning] = useState(null);
  const [expandedChange, setExpandedChange] = useState(null);

  return (
    <div className="space-y-4">
      {/* Что HEALER узнал */}
      <Card className="w-full bg-gray-900/50 border-gray-700">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg text-white flex items-center gap-2">
            <span>🧠</span> Рефлексия
            <span className="text-xs text-gray-400 font-normal ml-auto">
              Что HEALER узнал нового
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {learnings.length === 0 ? (
            <div className="text-center text-gray-500 py-4 text-sm">
              Пока нет новых знаний. Запустите цикл диагностики.
            </div>
          ) : (
            <div className="space-y-2">
              {learnings.map((l, i) => {
                const isExpanded = expandedLearning === i;
                return (
                  <div key={i}>
                    <button
                      onClick={() => setExpandedLearning(isExpanded ? null : i)}
                      className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-gray-800/30 transition-colors text-left"
                    >
                      <span className="text-base">{l.icon || '💡'}</span>
                      <span className="text-xs text-gray-300 flex-1 truncate">{l.title || l.message}</span>
                      <span className="text-xs text-gray-500">{l.timestamp || ''}</span>
                      <span className="text-gray-600 text-xs">{isExpanded ? '▲' : '▼'}</span>
                    </button>
                    {isExpanded && (
                      <div className="ml-6 p-2 bg-gray-800/30 rounded text-xs text-gray-400 space-y-1">
                        {l.description && <div>{l.description}</div>}
                        {l.pattern && <div className="text-indigo-300">🔄 Паттерн: {l.pattern}</div>}
                        {l.impact && <div className="text-yellow-300">📈 Влияние: {l.impact}</div>}
                        {l.details && (
                          <pre className="text-[10px] text-gray-500 overflow-x-auto mt-1">
                            {typeof l.details === 'string' ? l.details : JSON.stringify(l.details, null, 2)}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* История изменений */}
      <Card className="w-full bg-gray-900/50 border-gray-700">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg text-white flex items-center gap-2">
            <span>📝</span> История изменений
            <span className="text-xs text-gray-400 font-normal ml-auto">
              Внесённые HEALER исправления
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {changes.length === 0 ? (
            <div className="text-center text-gray-500 py-4 text-sm">
              Изменений пока не было.
            </div>
          ) : (
            <div className="space-y-2">
              {changes.map((c, i) => {
                const isExpanded = expandedChange === i;
                const statusColor = c.status === 'applied' ? 'text-green-400' :
                  c.status === 'rolled_back' ? 'text-red-400' : 'text-yellow-400';

                return (
                  <div key={i}>
                    <div className="flex items-center gap-2 p-2 rounded-lg bg-gray-800/20">
                      <span className={`w-2 h-2 rounded-full ${statusColor.replace('text-', 'bg-')}`} />
                      <span className="text-xs text-gray-300 flex-1 truncate">
                        {c.component || c.target || 'Компонент'}
                      </span>
                      <span className={`text-xs ${statusColor}`}>{c.status}</span>
                      <button
                        onClick={() => setExpandedChange(isExpanded ? null : i)}
                        className="text-gray-600 text-xs hover:text-gray-400"
                      >
                        {isExpanded ? '▲' : '▼'}
                      </button>
                    </div>
                    {isExpanded && (
                      <div className="ml-4 p-2 bg-gray-800/20 rounded text-xs text-gray-400 space-y-1">
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <span className="text-gray-500">Было:</span>
                            <div className="text-red-300 font-mono">{c.old_value || c.before || 'N/A'}</div>
                          </div>
                          <div>
                            <span className="text-gray-500">Стало:</span>
                            <div className="text-green-300 font-mono">{c.new_value || c.after || 'N/A'}</div>
                          </div>
                        </div>
                        {c.reason && <div className="text-gray-500 mt-1">Причина: {c.reason}</div>}
                        {c.timestamp && <div className="text-gray-600">{c.timestamp}</div>}
                        {c.status === 'applied' && onRollback && (
                          <button
                            onClick={() => onRollback(c)}
                            className="mt-2 px-3 py-1 bg-red-900/30 hover:bg-red-900/50 rounded text-xs text-red-400 transition-colors"
                          >
                            Откатить
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default HealerReflection;