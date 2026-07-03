import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';

export function HealerHistory({ cycles = [] }) {
  if (cycles.length === 0) {
    return (
      <Card className="w-full bg-gray-900/50 border-gray-700">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg text-white flex items-center gap-2">
            <span>📈</span> История циклов
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-gray-500 py-4 text-sm">
            Циклов пока нет.
          </div>
        </CardContent>
      </Card>
    );
  }

  // Статистика
  const totalCycles = cycles.length;
  const successCycles = cycles.filter(c => c.status === 'success' || c.status === 'ok' || c.status === 'done').length;
  const failedCycles = cycles.filter(c => c.status === 'error' || c.status === 'failed').length;
  const partialCycles = totalCycles - successCycles - failedCycles;
  const totalReports = cycles.reduce((s, c) => s + (c.reports?.length || 0), 0);
  const avgDuration = cycles.length > 0
    ? Math.round(cycles.reduce((s, c) => s + (c.duration_ms || 0), 0) / cycles.length)
    : 0;

  // Данные для графика (последние 20 циклов)
  const chartData = cycles.slice(-20).map(c => ({
    reports: c.reports?.length || 0,
    status: c.status,
  }));
  const maxReports = Math.max(...chartData.map(d => d.reports), 1);

  return (
    <Card className="w-full bg-gray-900/50 border-gray-700">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg text-white flex items-center gap-2">
          <span>📈</span> История циклов
          <span className="text-xs text-gray-400 font-normal">({totalCycles})</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Summary stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <div className="p-3 bg-gray-800/50 rounded-lg">
            <div className="text-xs text-gray-500 mb-0.5">Всего циклов</div>
            <div className="text-lg font-bold text-white">{totalCycles}</div>
          </div>
          <div className="p-3 bg-gray-800/50 rounded-lg">
            <div className="text-xs text-gray-500 mb-0.5">Успешных</div>
            <div className="text-lg font-bold text-green-400">{successCycles}</div>
          </div>
          <div className="p-3 bg-gray-800/50 rounded-lg">
            <div className="text-xs text-gray-500 mb-0.5">Ошибок</div>
            <div className="text-lg font-bold text-red-400">{failedCycles}</div>
          </div>
          <div className="p-3 bg-gray-800/50 rounded-lg">
            <div className="text-xs text-gray-500 mb-0.5">Всего отчётов</div>
            <div className="text-lg font-bold text-purple-400">{totalReports}</div>
          </div>
        </div>

        {/* Успешность */}
        <div className="mb-4">
          <h4 className="text-xs text-gray-400 mb-2 font-semibold uppercase tracking-wide">Успешность</h4>
          <div className="flex h-4 rounded-full overflow-hidden">
            {successCycles > 0 && (
              <div className="bg-green-500 transition-all" style={{ width: `${(successCycles / totalCycles) * 100}%` }} />
            )}
            {partialCycles > 0 && (
              <div className="bg-yellow-500 transition-all" style={{ width: `${(partialCycles / totalCycles) * 100}%` }} />
            )}
            {failedCycles > 0 && (
              <div className="bg-red-500 transition-all" style={{ width: `${(failedCycles / totalCycles) * 100}%` }} />
            )}
          </div>
          <div className="flex justify-between text-[10px] text-gray-500 mt-1">
            <span>✅ {Math.round((successCycles / totalCycles) * 100)}%</span>
            {partialCycles > 0 && <span>⚠️ {Math.round((partialCycles / totalCycles) * 100)}%</span>}
            {failedCycles > 0 && <span>❌ {Math.round((failedCycles / totalCycles) * 100)}%</span>}
          </div>
        </div>

        {/* Mini bar chart: найденные проблемы по циклам */}
        {chartData.length > 0 && (
          <div className="mb-4">
            <h4 className="text-xs text-gray-400 mb-2 font-semibold uppercase tracking-wide">
              Найденные проблемы по циклам (последние {chartData.length})
            </h4>
            <div className="flex items-end gap-1 h-20">
              {chartData.map((d, i) => {
                const h = (d.reports / maxReports) * 100;
                const color = d.status === 'success' || d.status === 'ok' || d.status === 'done'
                  ? 'bg-green-500'
                  : d.status === 'error' || d.status === 'failed'
                  ? 'bg-red-500'
                  : 'bg-yellow-500';
                return (
                  <div key={i} className="flex-1 flex flex-col items-center">
                    <div
                      className={`w-full ${color} rounded-t transition-all`}
                      style={{ height: `${Math.max(h, 2)}%` }}
                      title={`Цикл ${i + 1}: ${d.reports} проблем`}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Список циклов */}
        <div className="space-y-1 max-h-[250px] overflow-y-auto">
          {[...cycles].reverse().map((c, i) => {
            const statusColor = c.status === 'success' || c.status === 'ok' || c.status === 'done'
              ? 'text-green-400'
              : c.status === 'error' || c.status === 'failed'
              ? 'text-red-400'
              : 'text-yellow-400';
            const reportsCount = c.reports?.length || 0;

            return (
              <div key={c.number || i} className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-800/20 text-xs">
                <span className={`w-1.5 h-1.5 rounded-full ${statusColor.replace('text-', 'bg-')}`} />
                <span className="text-gray-400 w-14 shrink-0">#{c.number || i + 1}</span>
                <span className="text-gray-500 flex-1">{c.timestamp || ''}</span>
                <span className={statusColor}>{c.status}</span>
                {reportsCount > 0 && (
                  <span className="text-gray-500">{reportsCount} отчётов</span>
                )}
                {c.duration_ms && (
                  <span className="text-gray-600">{Math.round(c.duration_ms)}ms</span>
                )}
              </div>
            );
          })}
        </div>

        {/* Средняя длительность */}
        {avgDuration > 0 && (
          <div className="mt-3 text-xs text-gray-500">
            Средняя длительность цикла: <span className="text-gray-300 font-mono">{avgDuration}ms</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default HealerHistory;