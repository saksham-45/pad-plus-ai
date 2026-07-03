import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { motion, AnimatePresence } from 'framer-motion';
import { apiFetch } from '../../services/api';

export function TraceHistory({ wsTraces = [] }) {
  const [traces, setTraces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTrace, setSelectedTrace] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [page, setPage] = useState(1);
  const perPage = 15;

  // Загружаем историю из API + добавляем live из WebSocket
  useEffect(() => {
    apiFetch('/api/v1/xray/recent?limit=50')
      .then(r => r.ok && r.json())
      .then(data => {
        if (data?.traces) {
          setTraces(data.traces);
        } else if (Array.isArray(data)) {
          setTraces(data);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Добавляем новые трейсы из WebSocket
  useEffect(() => {
    if (wsTraces.length > 0) {
      const latest = wsTraces[wsTraces.length - 1];
      setTraces(prev => {
        const exists = prev.find(t => t.request_id === latest.request_id);
        if (exists) return prev;
        return [latest, ...prev].slice(0, 100);
      });
    }
  }, [wsTraces]);

  // Фильтрация
  const filteredTraces = traces.filter(t => {
    const msg = (t.user_message || '').toLowerCase();
    const q = searchQuery.toLowerCase();
    const statusMatch = filterStatus === 'all' || 
      (filterStatus === 'success' && (t.completed || t.success)) ||
      (filterStatus === 'error' && t.status === 'error');
    return msg.includes(q) && statusMatch;
  });

  const paginatedTraces = filteredTraces.slice(0, page * perPage);

  const formatTime = (ts) => {
    if (!ts) return '';
    try {
      return new Date(ts).toLocaleTimeString('ru-RU');
    } catch {
      return ts;
    }
  };

  const getStatusColor = (trace) => {
    if (trace.status === 'error' || trace.success === false) return 'text-red-400';
    if (trace.completed || trace.success) return 'text-green-400';
    return 'text-yellow-400';
  };

  const getStatusIcon = (trace) => {
    if (trace.status === 'error' || trace.success === false) return '❌';
    if (trace.completed || trace.success) return '✅';
    return '⏳';
  };

  return (
    <Card className="w-full bg-gray-900/50 border-gray-700">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="text-lg text-white flex items-center gap-2">
            <span>📋</span> История трейсов
            <span className="text-xs text-gray-400 font-normal">
              ({filteredTraces.length})
            </span>
          </CardTitle>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="🔍 Поиск по запросу..."
              value={searchQuery}
              onChange={e => { setSearchQuery(e.target.value); setPage(1); }}
              className="px-3 py-1.5 bg-gray-800 border border-gray-600 rounded-lg text-sm text-white placeholder-gray-400 focus:outline-none focus:border-primary w-48"
            />
            <select
              value={filterStatus}
              onChange={e => { setFilterStatus(e.target.value); setPage(1); }}
              className="px-3 py-1.5 bg-gray-800 border border-gray-600 rounded-lg text-sm text-white focus:outline-none focus:border-primary"
            >
              <option value="all">Все</option>
              <option value="success">✅ Успешные</option>
              <option value="error">❌ Ошибки</option>
            </select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="text-center text-gray-400 py-8">Загрузка истории...</div>
        ) : paginatedTraces.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            {searchQuery ? 'Ничего не найдено' : 'История пуста. Отправьте запрос в чат.'}
          </div>
        ) : (
          <>
            <div className="space-y-1 max-h-[400px] overflow-y-auto">
              {paginatedTraces.map((trace, idx) => (
                <motion.div
                  key={trace.request_id || idx}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.02 }}
                  onClick={() => setSelectedTrace(selectedTrace?.request_id === trace.request_id ? null : trace)}
                  className={`
                    flex items-center gap-3 p-2.5 rounded-lg cursor-pointer transition-colors text-sm
                    ${selectedTrace?.request_id === trace.request_id 
                      ? 'bg-gray-700/50 border border-gray-500' 
                      : 'hover:bg-gray-800/50 border border-transparent'}
                  `}
                >
                  <span className="text-base">{getStatusIcon(trace)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-gray-200 truncate">
                      {(trace.user_message || '').slice(0, 60) || 'N/A'}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {trace.strategy && <span className="mr-2">🧠 {trace.strategy}</span>}
                      {trace.total_time_ms && <span>⏱ {Math.round(trace.total_time_ms)}ms</span>}
                      {trace.execution_time_ms && <span>⏱ {Math.round(trace.execution_time_ms)}ms</span>}
                    </div>
                  </div>
                  <div className="text-right text-xs text-gray-500 whitespace-nowrap">
                    <div>{formatTime(trace.start_time || trace.timestamp)}</div>
                    <div className={getStatusColor(trace)}>
                      {trace.completed ? 'завершён' : trace.success ? 'успех' : trace.status || 'в процессе'}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>

            {filteredTraces.length > perPage && (
              <div className="mt-3 text-center">
                <button
                  onClick={() => setPage(p => p + 1)}
                  className="px-4 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
                >
                  Показать ещё ({filteredTraces.length - paginatedTraces.length})
                </button>
              </div>
            )}

            {/* Детальный просмотр трейса */}
            <AnimatePresence>
              {selectedTrace && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-4 p-4 bg-gray-800/50 border border-gray-600 rounded-lg"
                >
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-semibold text-white">
                      Детали трейса
                    </h4>
                    <button
                      onClick={() => setSelectedTrace(null)}
                      className="text-gray-400 hover:text-white text-lg"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <Detail label="Request ID" value={selectedTrace.request_id} />
                    <Detail label="Сообщение" value={(selectedTrace.user_message || '').slice(0, 100)} />
                    <Detail label="Стратегия" value={selectedTrace.strategy || 'N/A'} />
                    <Detail label="Длительность" value={selectedTrace.total_time_ms ? `${Math.round(selectedTrace.total_time_ms)}ms` : 'N/A'} />
                    <Detail label="Статус" value={selectedTrace.completed ? '✅ Завершён' : selectedTrace.success ? '✅ Успех' : '⏳ В процессе'} />
                    {selectedTrace.stage_times && (
                      <Detail label="Фазы" value={JSON.stringify(selectedTrace.stage_times)} isCode />
                    )}
                    {selectedTrace.metadata && (
                      <Detail label="Метаданные" value={JSON.stringify(selectedTrace.metadata, null, 2)} isCode />
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function Detail({ label, value, isCode = false }) {
  return (
    <div>
      <div className="text-gray-500 mb-0.5">{label}</div>
      {isCode ? (
        <pre className="text-gray-200 bg-gray-900/50 p-2 rounded overflow-x-auto text-xs max-h-[200px]">
          {value}
        </pre>
      ) : (
        <div className="text-gray-200 truncate">{value || '—'}</div>
      )}
    </div>
  );
}

export default TraceHistory;