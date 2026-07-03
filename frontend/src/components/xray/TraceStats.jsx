import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { apiFetch } from '../../services/api';

export function TraceStats() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('24h');

  useEffect(() => {
    setLoading(true);
    apiFetch('/api/v1/xray/stats')
      .then(r => r.ok && r.json())
      .then(data => setStats(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [period]);

  if (loading) {
    return (
      <Card className="w-full bg-gray-900/50 border-gray-700">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg text-white flex items-center gap-2">
            <span>📊</span> Статистика
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-gray-400 py-4 text-sm">Загрузка...</div>
        </CardContent>
      </Card>
    );
  }

  if (!stats) {
    return (
      <Card className="w-full bg-gray-900/50 border-gray-700">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg text-white flex items-center gap-2">
            <span>📊</span> Статистика
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-gray-500 py-4 text-sm">Нет данных</div>
        </CardContent>
      </Card>
    );
  }

  const tc = stats.trace_collector || {};
  const broadcaster = stats.broadcaster || {};
  const visualizer = stats.thought_visualizer || {};
  const recorder = stats.history_recorder || {};

  // Статистика по стадиям
  const stageStats = tc.stage_stats || {};
  const stageEntries = Object.entries(stageStats).sort((a, b) => a[0].localeCompare(b[0]));

  return (
    <Card className="w-full bg-gray-900/50 border-gray-700">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg text-white flex items-center gap-2">
            <span>📊</span> Статистика X-Ray
          </CardTitle>
          <select
            value={period}
            onChange={e => setPeriod(e.target.value)}
            className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-xs text-white"
          >
            <option value="1h">1 час</option>
            <option value="24h">24 часа</option>
            <option value="7d">7 дней</option>
          </select>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <StatBox label="Сессий всего" value={tc.total_sessions || 0} color="blue" />
          <StatBox label="Активных" value={tc.active_sessions || 0} color="cyan" />
          <StatBox label="Завершённых" value={tc.completed_sessions || 0} color="green" />
          <StatBox label="Ошибок в фазах" value={Object.values(stageStats).reduce((s, st) => s + (st.errors || 0), 0)} color="red" />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <StatBox label="Сообщ. отправлено" value={broadcaster.total_messages_sent || 0} color="purple" />
          <StatBox label="Подключений WS" value={broadcaster.total_connections || 0} color="pink" />
          <StatBox label="Активных WS" value={broadcaster.active_connections || 0} color="green" />
          <StatBox label="Трейсов в истории" value={recorder.recent_count || 0} color="yellow" />
        </div>

        {/* Статистика по стадиям */}
        {stageEntries.length > 0 && (
          <div>
            <h4 className="text-xs text-gray-400 mb-2 font-semibold uppercase tracking-wide">
              Длительность по фазам
            </h4>
            <div className="space-y-1.5">
              {stageEntries.map(([stage, st]) => {
                const avg = st.avg_duration_ms || st.total_duration_ms / (st.count || 1);
                const maxVal = Math.max(...stageEntries.map(([, s]) => s.avg_duration_ms || s.total_duration_ms / (s.count || 1)), 1);
                const pct = (avg / maxVal) * 100;

                return (
                  <div key={stage} className="flex items-center gap-2 text-xs">
                    <span className="w-20 text-gray-400 truncate">{stage}</span>
                    <div className="flex-1 h-4 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all"
                        style={{ width: `${Math.max(pct, 2)}%` }}
                      />
                    </div>
                    <span className="w-16 text-right text-gray-300 font-mono">
                      {Math.round(avg)}ms
                    </span>
                    <span className="w-8 text-right text-gray-500">
                      {st.count}x
                    </span>
                    {st.errors > 0 && (
                      <span className="w-4 text-right text-red-400" title={`${st.errors} ошибок`}>
                        ❌{st.errors}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Использование моделей */}
        {recorder.model_usage && Object.keys(recorder.model_usage).length > 0 && (
          <div className="mt-4">
            <h4 className="text-xs text-gray-400 mb-2 font-semibold uppercase tracking-wide">
              Использование моделей
            </h4>
            <div className="flex flex-wrap gap-2">
              {Object.entries(recorder.model_usage).map(([model, count]) => (
                <span key={model} className="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-300">
                  {model}: {count}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Общее время */}
        {recorder.avg_latency_ms > 0 && (
          <div className="mt-4 pt-3 border-t border-gray-700 text-xs text-gray-400">
            Средняя задержка: <span className="text-gray-200 font-mono">{Math.round(recorder.avg_latency_ms)}ms</span>
            {' · '}
            Всего ошибок: <span className="text-red-400 font-mono">{recorder.total_errors || 0}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function StatBox({ label, value, color = 'blue' }) {
  const colorClasses = {
    blue: 'text-blue-400', cyan: 'text-cyan-400', green: 'text-green-400',
    red: 'text-red-400', purple: 'text-purple-400', pink: 'text-pink-400',
    yellow: 'text-yellow-400', gray: 'text-gray-400'
  };

  return (
    <div className="p-3 bg-gray-800/50 rounded-lg">
      <div className="text-xs text-gray-500 mb-0.5">{label}</div>
      <div className={`text-lg font-bold ${colorClasses[color]}`}>{value}</div>
    </div>
  );
}

export default TraceStats;