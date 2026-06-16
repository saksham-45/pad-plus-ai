import { useState, useEffect } from 'react';

const MODES = [
  { id: 'monitor', label: 'Мониторинг', desc: 'Только наблюдение, без изменений' },
  { id: 'suggest', label: 'Рекомендации', desc: 'Диагностика + предложения по исправлению' },
  { id: 'auto', label: 'Авто', desc: 'Полный цикл: диагностика → исправление → проверка' },
];

const SEVERITY_COLORS = {
  info: { bg: 'bg-blue-500', text: 'text-blue-400' },
  warning: { bg: 'bg-yellow-500', text: 'text-yellow-400' },
  error: { bg: 'bg-orange-500', text: 'text-orange-400' },
  critical: { bg: 'bg-red-500', text: 'text-red-400' },
};

function StatusBadge({ status }) {
  const colors = {
    running: 'bg-green-500',
    idle: 'bg-gray-500',
    error: 'bg-red-500',
    processing: 'bg-yellow-500 animate-pulse',
    warning: 'bg-yellow-500',
  };
  return (
    <span className={`inline-block w-2.5 h-2.5 rounded-full ${colors[status] || 'bg-gray-500'}`} />
  );
}

function CycleCard({ cycle }) {
  const statusColor = cycle.status === 'success' || cycle.status === 'ok' ? 'text-green-400' :
    cycle.status === 'error' ? 'text-red-400' : 'text-blue-400';

  return (
    <div className="p-3 bg-gray-800/50 rounded-lg border border-gray-700/50">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-mono ${statusColor}`}>
            Cycle #{cycle.number}
          </span>
          <StatusBadge status={cycle.status} />
        </div>
        <span className="text-xs text-gray-500">{cycle.timestamp}</span>
      </div>
      {cycle.reports && cycle.reports.length > 0 && (
        <div className="space-y-1 mt-2">
          {cycle.reports.slice(0, 5).map((r, i) => {
            const sev = r.severity || (r.passed ? 'info' : 'error');
            const c = SEVERITY_COLORS[sev] || SEVERITY_COLORS.info;
            return (
              <div key={i} className="flex items-center gap-2 text-xs group relative">
                <span className={`w-1.5 h-1.5 rounded-full ${c.bg} shrink-0`} />
                <span className="text-gray-400 truncate">{r.check || r.name || r.message || 'Check ' + (i + 1)}</span>
                <span className={`${c.text} ml-auto shrink-0 text-[10px] uppercase`}>{sev}</span>
              </div>
            );
          })}
          {cycle.reports.length > 5 && (
            <div className="text-xs text-gray-600 mt-1">
              +{cycle.reports.length - 5} more
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EventRow({ event }) {
  const typeColors = {
    diag_started: 'text-blue-400',
    diag_completed: 'text-green-400',
    cycle_complete: 'text-purple-400',
    auto_cycle_start: 'text-cyan-400',
    auto_cycle_complete: 'text-cyan-300',
    error: 'text-red-400',
    info: 'text-gray-400',
  };

  const shortType = event.type?.replace('healer_bridge_', '');
  const color = typeColors[shortType] || 'text-gray-400';

  return (
    <div className="flex items-start gap-3 py-2 border-b border-gray-800/50 last:border-0">
      <div className={`w-2 h-2 mt-1.5 rounded-full shrink-0 ${color.replace('text-', 'bg-')} bg-opacity-60`} />
      <div className="flex-1 min-w-0">
        <div className={`text-xs font-mono ${color}`}>
          {event.type}
        </div>
        {event.data && (
          <div className="text-xs text-gray-500 truncate mt-0.5 max-w-[400px]">
            {JSON.stringify(event.data).slice(0, 120)}
          </div>
        )}
      </div>
      <div className="text-xs text-gray-600 shrink-0">{event.timestamp}</div>
    </div>
  );
}

function ReportDetail({ report }) {
  const sev = report.severity || 'info';
  const c = SEVERITY_COLORS[sev] || SEVERITY_COLORS.info;
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-700/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 p-3 hover:bg-gray-800/30 transition-colors text-left"
      >
        <span className={`w-2 h-2 rounded-full ${c.bg} shrink-0`} />
        <span className={`text-xs font-medium ${c.text} shrink-0 uppercase`}>{sev}</span>
        <span className="text-sm text-gray-300 flex-1 truncate">
          {report.check || report.name || report.message || 'Без названия'}
        </span>
        <span className="text-gray-500 text-xs">{expanded ? '▲' : '▼'}</span>
      </button>
      {expanded && (
        <div className="px-3 pb-3 space-y-2 text-xs text-gray-400 border-t border-gray-700/50 pt-2">
          {report.file && <div><span className="text-gray-500">Файл:</span> {report.file}</div>}
          {report.line && <div><span className="text-gray-500">Строка:</span> {report.line}</div>}
          {report.message && <div><span className="text-gray-500">Сообщение:</span> {report.message}</div>}
          {report.suggestion && <div><span className="text-gray-500">Рекомендация:</span> {report.suggestion}</div>}
          {report.duration_ms != null && (
            <div><span className="text-gray-500">Длительность:</span> {report.duration_ms}ms</div>
          )}
          {report.details && (
            <div>
              <span className="text-gray-500">Детали:</span>
              <pre className="mt-1 p-2 bg-gray-900/50 rounded text-[10px] overflow-x-auto">
                {typeof report.details === 'string' ? report.details : JSON.stringify(report.details, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function HealerTracePanel({
  cycles = [],
  events = [],
  status = 'idle',
  mode = 'monitor',
  bridgeConnected = false,
  onStartCycle,
  onModeChange,
  activeSessions = 0,

  // Auto-cycle props
  autoCycleEnabled = false,
  autoCycleRunning = false,
  autoCycleInterval = 300,
  onAutoCycleToggle,
  onAutoCycleIntervalChange,

  // Reports props
  latestReports = [],
  onRefreshReports,
}) {
  const [intervalInput, setIntervalInput] = useState(String(autoCycleInterval));
  const [showAllReports, setShowAllReports] = useState(false);

  useEffect(() => {
    setIntervalInput(String(autoCycleInterval));
  }, [autoCycleInterval]);

  const sortedReports = [...latestReports].sort((a, b) => {
    const order = { critical: 0, error: 1, warning: 2, info: 3 };
    return (order[a.severity] ?? 99) - (order[b.severity] ?? 99);
  });

  const handleIntervalSave = () => {
    const val = parseInt(intervalInput, 10);
    if (val >= 30) onAutoCycleIntervalChange?.(val);
  };

  return (
    <div className="space-y-6">
      {/* Status Bar */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="p-3 bg-gray-900/50 border border-gray-700 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Статус</div>
          <div className="flex items-center gap-2">
            <StatusBadge status={status} />
            <span className="text-sm font-medium text-white">{status}</span>
          </div>
        </div>
        <div className="p-3 bg-gray-900/50 border border-gray-700 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Режим</div>
          <div className="text-sm font-medium text-white capitalize">{mode}</div>
        </div>
        <div className="p-3 bg-gray-900/50 border border-gray-700 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Циклов</div>
          <div className="text-sm font-medium text-white">{cycles.length}</div>
        </div>
        <div className="p-3 bg-gray-900/50 border border-gray-700 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Событий</div>
          <div className="text-sm font-medium text-white">{events.length}</div>
        </div>
        <div className="p-3 bg-gray-900/50 border border-gray-700 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">WebSocket</div>
          <div className={`text-sm font-medium ${bridgeConnected ? 'text-green-400' : 'text-red-400'}`}>
            {bridgeConnected ? 'Online' : 'Offline'}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={onStartCycle}
          disabled={status === 'running' || status === 'processing'}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg text-sm text-white transition-colors"
        >
          {status === 'running' || status === 'processing' ? 'Выполняется...' : 'Запустить цикл'}
        </button>
      </div>

      {/* Mode Selector (3-way) */}
      <div>
        <h3 className="text-sm text-gray-400 mb-3 font-medium">Режим работы HEALER</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {MODES.map((m) => {
            const active = mode === m.id;
            return (
              <button
                key={m.id}
                onClick={() => onModeChange?.(m.id)}
                className={`p-3 rounded-lg border text-left transition-all ${
                  active
                    ? 'bg-indigo-900/30 border-indigo-500/50 shadow-lg shadow-indigo-500/10'
                    : 'bg-gray-800/30 border-gray-700/50 hover:border-gray-600'
                }`}
              >
                <div className={`text-sm font-medium mb-1 ${active ? 'text-indigo-300' : 'text-gray-300'}`}>
                  {active && <span className="mr-1">▶</span>}
                  {m.label}
                </div>
                <div className="text-[11px] text-gray-500">{m.desc}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Auto-cycle Config */}
      <div>
        <h3 className="text-sm text-gray-400 mb-3 font-medium">Автоматические циклы</h3>
        <div className="p-4 bg-gray-900/30 border border-gray-800 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-300">Автоциклы</span>
              <span className={`text-xs ${autoCycleRunning ? 'text-green-400' : 'text-gray-500'}`}>
                {autoCycleRunning ? '(выполняется...)' : ''}
              </span>
            </div>
            <button
              onClick={() => onAutoCycleToggle?.(!autoCycleEnabled)}
              className={`relative w-10 h-5 rounded-full transition-colors ${
                autoCycleEnabled ? 'bg-indigo-600' : 'bg-gray-700'
              }`}
            >
              <span
                className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                  autoCycleEnabled ? 'translate-x-5' : ''
                }`}
              />
            </button>
          </div>
          {autoCycleEnabled && (
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-500 shrink-0">Интервал (сек):</span>
              <input
                type="number"
                min="30"
                max="86400"
                value={intervalInput}
                onChange={(e) => setIntervalInput(e.target.value)}
                className="w-20 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-sm text-white text-center"
              />
              <button
                onClick={handleIntervalSave}
                className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs text-gray-300 transition-colors"
              >
                Применить
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Latest Reports */}
      {sortedReports.length > 0 && (
        <div>
          <h3 className="text-sm text-gray-400 mb-3 font-medium">
            Отчёты диагностики
            <span className="text-gray-600 ml-2">({sortedReports.length})</span>
            {onRefreshReports && (
              <button
                onClick={onRefreshReports}
                className="ml-2 text-[10px] text-indigo-400 hover:text-indigo-300"
              >
                обновить
              </button>
            )}
          </h3>
          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {(showAllReports ? sortedReports : sortedReports.slice(0, 10)).map((r, i) => (
              <ReportDetail key={i} report={r} />
            ))}
            {sortedReports.length > 10 && (
              <button
                onClick={() => setShowAllReports(!showAllReports)}
                className="w-full py-2 text-xs text-indigo-400 hover:text-indigo-300 bg-gray-900/20 border border-dashed border-gray-700/50 rounded-lg"
              >
                {showAllReports ? 'Свернуть' : `Показать все (${sortedReports.length}) »`}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Cycles */}
      {cycles.length > 0 && (
        <div>
          <h3 className="text-sm text-gray-400 mb-3 font-medium">Циклы диагностики</h3>
          <div className="space-y-2 max-h-[300px] overflow-y-auto">
            {[...cycles].reverse().map((cycle, i) => (
              <CycleCard key={cycle.number || i} cycle={cycle} />
            ))}
          </div>
        </div>
      )}

      {/* Events */}
      <div>
        <h3 className="text-sm text-gray-400 mb-3 font-medium">Поток событий</h3>
        <div className="bg-gray-900/30 border border-gray-800 rounded-lg p-3 max-h-[400px] overflow-y-auto">
          {events.length === 0 ? (
            <div className="text-center text-gray-600 text-sm py-8">
              Ожидание событий HEALER...
            </div>
          ) : (
            [...events].reverse().slice(0, 100).map((event, i) => (
              <EventRow key={event.id || i} event={event} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default HealerTracePanel;
