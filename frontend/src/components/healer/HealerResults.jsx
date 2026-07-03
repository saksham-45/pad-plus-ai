import React, { useState, useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';

const SEVERITY_CONFIG = {
  critical: { bg: 'bg-red-500', text: 'text-red-400', label: 'Критичные' },
  error: { bg: 'bg-orange-500', text: 'text-orange-400', label: 'Ошибки' },
  warning: { bg: 'bg-yellow-500', text: 'text-yellow-400', label: 'Предупреждения' },
  info: { bg: 'bg-blue-500', text: 'text-blue-400', label: 'Информация' },
};

const MODULE_COLORS = {
  'backend/core': 'from-blue-500 to-blue-700',
  'backend/api': 'from-green-500 to-green-700',
  'frontend': 'from-purple-500 to-purple-700',
  'database': 'from-yellow-500 to-yellow-700',
  'healer': 'from-pink-500 to-pink-700',
  'memory': 'from-cyan-500 to-cyan-700',
  'other': 'from-gray-500 to-gray-700',
};

function detectModule(report) {
  const file = (report.file || report.check || report.name || '').toLowerCase();
  if (file.includes('backend/core') || file.includes('pipeline') || file.includes('xray')) return 'backend/core';
  if (file.includes('backend/api') || file.includes('routes')) return 'backend/api';
  if (file.includes('frontend') || file.includes('jsx') || file.includes('component')) return 'frontend';
  if (file.includes('database') || file.includes('sql') || file.includes('migration')) return 'database';
  if (file.includes('healer') || file.includes('healing')) return 'healer';
  if (file.includes('memory') || file.includes('rag')) return 'memory';
  return 'other';
}

export function HealerResults({ reports = [], onRefresh }) {
  const [expandedModule, setExpandedModule] = useState(null);
  const [expandedReport, setExpandedReport] = useState(null);

  // Группировка по модулям
  const grouped = useMemo(() => {
    const groups = {};
    for (const r of reports) {
      const mod = detectModule(r);
      if (!groups[mod]) groups[mod] = { reports: [], counts: { critical: 0, error: 0, warning: 0, info: 0 } };
      groups[mod].reports.push(r);
      const sev = r.severity || 'info';
      if (groups[mod].counts[sev] !== undefined) groups[mod].counts[sev]++;
    }
    return groups;
  }, [reports]);

  // Суммарная статистика
  const totals = useMemo(() => {
    const t = { critical: 0, error: 0, warning: 0, info: 0 };
    for (const g of Object.values(grouped)) {
      for (const [sev, count] of Object.entries(g.counts)) {
        t[sev] += count;
      }
    }
    return t;
  }, [grouped]);

  const maxSeverityCount = Math.max(...Object.values(totals), 1);

  if (reports.length === 0) {
    return (
      <Card className="w-full bg-gray-900/50 border-gray-700">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg text-white flex items-center gap-2">
            <span>📊</span> Результаты диагностики
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-gray-500 py-8 text-sm">
            Нет отчётов. Запустите цикл диагностики.
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full bg-gray-900/50 border-gray-700">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg text-white flex items-center gap-2">
            <span>📊</span> Результаты диагностики
            <span className="text-xs text-gray-400 font-normal">({reports.length})</span>
          </CardTitle>
          {onRefresh && (
            <button onClick={onRefresh} className="text-xs text-indigo-400 hover:text-indigo-300">
              обновить
            </button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {/* Heatmap by severity */}
        <div className="mb-4">
          <h4 className="text-xs text-gray-400 mb-2 font-semibold uppercase tracking-wide">По severity</h4>
          <div className="grid grid-cols-4 gap-2">
            {Object.entries(SEVERITY_CONFIG).map(([sev, cfg]) => (
              <div key={sev} className="text-center p-2 bg-gray-800/50 rounded-lg">
                <div className={`text-lg font-bold ${cfg.text}`}>{totals[sev]}</div>
                <div className="text-xs text-gray-500">{cfg.label}</div>
              </div>
            ))}
          </div>
          {/* Mini bar chart */}
          <div className="mt-2 flex gap-0.5 h-3 rounded-full overflow-hidden">
            {Object.entries(SEVERITY_CONFIG).map(([sev, cfg]) => (
              <div
                key={sev}
                className={`${cfg.bg} transition-all`}
                style={{ width: `${(totals[sev] / maxSeverityCount) * 100}%`, minWidth: totals[sev] > 0 ? '4px' : '0' }}
              />
            ))}
          </div>
        </div>

        {/* Heatmap by module */}
        <div className="mb-4">
          <h4 className="text-xs text-gray-400 mb-2 font-semibold uppercase tracking-wide">По модулям</h4>
          <div className="space-y-1.5">
            {Object.entries(grouped).map(([mod, g]) => {
              const totalInModule = Object.values(g.counts).reduce((s, c) => s + c, 0);
              const pct = (totalInModule / reports.length) * 100;
              const isExpanded = expandedModule === mod;

              return (
                <div key={mod}>
                  <button
                    onClick={() => setExpandedModule(isExpanded ? null : mod)}
                    className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-gray-800/30 transition-colors text-left"
                  >
                    <div
                      className={`h-2 rounded-full bg-gradient-to-r ${MODULE_COLORS[mod] || MODULE_COLORS.other} transition-all`}
                      style={{ width: `${Math.max(pct, 2)}%` }}
                    />
                    <span className="text-xs text-gray-300 truncate flex-1">{mod}</span>
                    <span className="text-xs text-gray-500">{totalInModule}</span>
                    {Object.entries(g.counts).filter(([, c]) => c > 0).map(([sev, c]) => (
                      <span key={sev} className={`text-[10px] ${SEVERITY_CONFIG[sev]?.text || 'text-gray-400'}`}>
                        {c}{sev[0].toUpperCase()}
                      </span>
                    ))}
                    <span className="text-gray-600 text-xs">{isExpanded ? '▲' : '▼'}</span>
                  </button>
                  {isExpanded && (
                    <div className="ml-4 space-y-1 mt-1 mb-2">
                      {g.reports.slice(0, 10).map((r, i) => {
                        const sev = r.severity || 'info';
                        const cfg = SEVERITY_CONFIG[sev] || SEVERITY_CONFIG.info;
                        const isDetailExpanded = expandedReport === i;
                        return (
                          <div key={i}>
                            <button
                              onClick={() => setExpandedReport(isDetailExpanded ? null : i)}
                              className="w-full flex items-center gap-2 p-1.5 rounded hover:bg-gray-800/20 text-left"
                            >
                              <span className={`w-1.5 h-1.5 rounded-full ${cfg.bg} shrink-0`} />
                              <span className={`text-xs ${cfg.text} shrink-0 uppercase`}>{sev}</span>
                              <span className="text-xs text-gray-400 truncate">
                                {r.check || r.name || r.message || `Проблема ${i + 1}`}
                              </span>
                            </button>
                            {isDetailExpanded && (
                              <div className="ml-4 p-2 bg-gray-800/30 rounded text-xs text-gray-400 space-y-1">
                                {r.file && <div>📁 {r.file}{r.line ? `:${r.line}` : ''}</div>}
                                {r.message && <div>💬 {r.message}</div>}
                                {r.suggestion && <div className="text-indigo-300">💡 {r.suggestion}</div>}
                                {r.details && (
                                  <pre className="text-[10px] text-gray-500 overflow-x-auto mt-1">
                                    {typeof r.details === 'string' ? r.details : JSON.stringify(r.details, null, 2)}
                                  </pre>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                      {g.reports.length > 10 && (
                        <div className="text-[10px] text-gray-600 pl-2">
                          + ещё {g.reports.length - 10}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default HealerResults;