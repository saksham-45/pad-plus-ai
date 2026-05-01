import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { useEffect, useRef } from 'react';

const logColors = {
  INFO: 'text-green-500',
  WARNING: 'text-yellow-500',
  ERROR: 'text-red-500',
  DEBUG: 'text-blue-500',
  default: 'text-text-muted',
};

function getLogLevel(message) {
  const upper = message.toUpperCase();
  if (upper.includes('ERROR')) return 'ERROR';
  if (upper.includes('WARN')) return 'WARNING';
  if (upper.includes('DEBUG')) return 'DEBUG';
  if (upper.includes('INFO')) return 'INFO';
  return 'default';
}

export function LogsWidget({ logs = [] }) {
  const scrollRef = useRef(null);
  
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);
  
  // Генерируем демо логи если их нет
  const displayLogs = logs.length > 0 ? logs : Array.from({ length: 15 }, (_, i) => ({
    id: i,
    timestamp: new Date(Date.now() - (15 - i) * 1000).toISOString(),
    type: 'event',
    message: `[event] processing step ${i}`,
    source: 'pipeline',
  }));
  
  return (
    <Card hover className="h-full">
      <CardHeader>
        <CardTitle>System Logs</CardTitle>
      </CardHeader>
      <CardContent>
        <div
          ref={scrollRef}
          className="h-48 overflow-y-auto font-mono text-xs space-y-1"
        >
          {displayLogs.map((log) => {
            const level = getLogLevel(log.message);
            const colorClass = logColors[level] || logColors.default;
            
            return (
              <div
                key={log.id || Math.random()}
                className="flex gap-2 text-text-muted hover:bg-gray-800/50 rounded px-1 py-0.5"
              >
                <span className="text-text-secondary flex-shrink-0">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className={`${colorClass} flex-shrink-0`}>
                  [{log.type || 'INFO'}]
                </span>
                <span className="truncate">{log.message}</span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export default LogsWidget;