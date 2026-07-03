import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';

export function XRayMeta({ connected, wsStats = {} }) {
  const {
    messagesSent = 0,
    errors = 0,
    reconnects = 0,
    queueSize = 0,
  } = wsStats;

  const metaStats = [
    { label: 'WebSocket', value: connected ? 'Online' : 'Offline', color: connected ? 'green' : 'red' },
    { label: 'Сообщений получено', value: messagesSent, color: 'blue' },
    { label: 'Ошибок X-Ray', value: errors, color: errors > 0 ? 'red' : 'gray' },
    { label: 'Реконнектов', value: reconnects, color: reconnects > 0 ? 'yellow' : 'gray' },
    { label: 'Очередь сообщений', value: queueSize, color: queueSize > 10 ? 'red' : queueSize > 0 ? 'yellow' : 'gray' },
  ];

  return (
    <Card className="w-full bg-gray-900/50 border-gray-700">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg text-white flex items-center gap-2">
          <span>🔍</span> Мета-наблюдаемость
          <span className="text-xs text-gray-400 font-normal ml-auto">
            X-Ray самого себя
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {metaStats.map((stat) => (
            <div key={stat.label} className="p-2.5 bg-gray-800/50 rounded-lg text-center">
              <div className="text-xs text-gray-500 mb-1">{stat.label}</div>
              <div className={`text-sm font-bold ${
                stat.color === 'green' ? 'text-green-400' :
                stat.color === 'red' ? 'text-red-400' :
                stat.color === 'yellow' ? 'text-yellow-400' :
                stat.color === 'blue' ? 'text-blue-400' :
                'text-gray-400'
              }`}>
                {typeof stat.value === 'number' ? stat.value.toLocaleString() : stat.value}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-3 flex items-center gap-2 text-xs text-gray-500">
          <div className={`w-2 h-2 rounded-full ${
            connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
          }`} />
          <span>
            {connected 
              ? 'X-Ray Broadcaster активен' 
              : 'X-Ray Broadcaster не подключён'}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

export default XRayMeta;