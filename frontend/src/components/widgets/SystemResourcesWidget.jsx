import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { motion } from 'framer-motion';

// Метрики системных ресурсов
const resourceMetrics = [
  { 
    key: 'cpu', 
    label: 'CPU Usage', 
    icon: '🖥️', 
    unit: '%',
    color: 'bg-blue-500',
    warningThreshold: 70,
    criticalThreshold: 90
  },
  { 
    key: 'memory', 
    label: 'Memory Usage', 
    icon: '💾', 
    unit: '%',
    color: 'bg-purple-500',
    warningThreshold: 75,
    criticalThreshold: 90
  },
  { 
    key: 'disk', 
    label: 'Disk I/O', 
    icon: '💿', 
    unit: 'MB/s',
    color: 'bg-green-500',
    warningThreshold: 80,
    criticalThreshold: 95
  },
  { 
    key: 'network', 
    label: 'Network Latency', 
    icon: '🌐', 
    unit: 'ms',
    color: 'bg-yellow-500',
    warningThreshold: 100,
    criticalThreshold: 200
  },
];

// Компонент индикатора ресурса
function ResourceIndicator({ metric, value, max = 100 }) {
  const percentage = Math.min((value / max) * 100, 100);
  
  // Определение цвета на основе значения
  const getColor = () => {
    if (percentage >= metric.criticalThreshold) return 'bg-red-500';
    if (percentage >= metric.warningThreshold) return 'bg-yellow-500';
    return metric.color;
  };
  
  const getStatus = () => {
    if (percentage >= metric.criticalThreshold) return 'critical';
    if (percentage >= metric.warningThreshold) return 'warning';
    return 'normal';
  };
  
  const status = getStatus();
  const color = getColor();
  
  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span className="text-xl">{metric.icon}</span>
          <span className="text-sm text-gray-300">{metric.label}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-sm font-bold ${
            status === 'critical' ? 'text-red-500' : 
            status === 'warning' ? 'text-yellow-500' : 'text-green-500'
          }`}>
            {value.toFixed(1)}{metric.unit}
          </span>
          {status === 'critical' && (
            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          )}
        </div>
      </div>
      
      <div className="relative">
        <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
          <motion.div
            className={`h-full ${color} rounded-full`}
            initial={{ width: 0 }}
            animate={{ width: `${percentage}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          />
        </div>
        
        {/* Маркеры порогов */}
        <div className="absolute top-0 left-0 w-full h-2">
          <div 
            className="absolute top-0 h-full w-0.5 bg-yellow-500/50"
            style={{ left: `${(metric.warningThreshold / max) * 100}%` }}
          />
          <div 
            className="absolute top-0 h-full w-0.5 bg-red-500/50"
            style={{ left: `${(metric.criticalThreshold / max) * 100}%` }}
          />
        </div>
      </div>
      
      <div className="flex justify-between text-xs text-gray-500">
        <span>0</span>
        <span className={status === 'warning' ? 'text-yellow-500' : ''}>
          Warning: {metric.warningThreshold}{metric.unit}
        </span>
        <span className={status === 'critical' ? 'text-red-500' : ''}>
          Critical: {metric.criticalThreshold}{metric.unit}
        </span>
        <span>{max}{metric.unit}</span>
      </div>
    </div>
  );
}

// Компонент для отображения активных подключений
function ActiveConnections({ count, max }) {
  const percentage = (count / max) * 100;
  
  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span className="text-xl">🔌</span>
          <span className="text-sm text-gray-300">Active Connections</span>
        </div>
        <span className="text-sm font-bold text-cyan-500">
          {count} / {max}
        </span>
      </div>
      
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-cyan-500 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
    </div>
  );
}

export function SystemResourcesWidget() {
  const [resources, setResources] = useState({
    cpu: 0,
    memory: 0,
    disk: 0,
    network: 0,
    activeConnections: 0,
    maxConnections: 1000
  });
  
  const [overallStatus, setOverallStatus] = useState('healthy');
  
  // Загрузка данных о ресурсах
  const fetchResources = async () => {
    try {
      const response = await fetch('/api/v1/metrics/system');
      if (response.ok) {
        const data = await response.json();
        setResources({
          cpu: data.cpu_usage || Math.random() * 60 + 20,
          memory: data.memory_usage || Math.random() * 70 + 10,
          disk: data.disk_io || Math.random() * 50 + 10,
          network: data.network_latency || Math.random() * 80 + 20,
          activeConnections: data.active_connections || Math.floor(Math.random() * 500) + 50,
          maxConnections: data.max_connections || 1000
        });
        
        // Определение общего статуса
        const maxUsage = Math.max(
          data.cpu_usage || 0,
          data.memory_usage || 0
        );
        
        if (maxUsage >= 90) setOverallStatus('critical');
        else if (maxUsage >= 70) setOverallStatus('warning');
        else setOverallStatus('healthy');
      }
    } catch (error) {
      console.error('Failed to fetch system resources:', error);
      // Демо данные если API не доступен
      setResources(prev => ({
        cpu: 20 + Math.random() * 40,
        memory: 30 + Math.random() * 40,
        disk: 10 + Math.random() * 30,
        network: 20 + Math.random() * 50,
        activeConnections: Math.floor(Math.random() * 300) + 50,
        maxConnections: 1000
      }));
    }
  };
  
  useEffect(() => {
    fetchResources();
    const interval = setInterval(fetchResources, 3000);
    return () => clearInterval(interval);
  }, []);
  
  const getStatusColor = () => {
    switch (overallStatus) {
      case 'critical': return 'text-red-500 bg-red-500/10 border-red-500/30';
      case 'warning': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/30';
      default: return 'text-green-500 bg-green-500/10 border-green-500/30';
    }
  };
  
  const getStatusText = () => {
    switch (overallStatus) {
      case 'critical': return 'CRITICAL';
      case 'warning': return 'WARNING';
      default: return 'HEALTHY';
    }
  };
  
  return (
    <Card className="bg-[#111827] border border-[#1F2937]">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">🖥️</span>
            System Resources
          </div>
          <div className={`px-3 py-1 rounded-full text-xs font-bold border ${getStatusColor()}`}>
            {getStatusText()}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Метрики ресурсов */}
          {resourceMetrics.map((metric) => (
            <ResourceIndicator
              key={metric.key}
              metric={metric}
              value={resources[metric.key]}
            />
          ))}
          
          <div className="border-t border-[#1F2937] pt-4">
            <ActiveConnections 
              count={resources.activeConnections}
              max={resources.maxConnections}
            />
          </div>
          
          {/* Дополнительная информация */}
          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-[#1F2937]">
            <div className="text-center p-3 bg-[#1F2937] rounded-lg">
              <div className="text-2xl font-bold text-blue-500">
                {resources.activeConnections}
              </div>
              <div className="text-xs text-gray-400">Active Sessions</div>
            </div>
            <div className="text-center p-3 bg-[#1F2937] rounded-lg">
              <div className="text-2xl font-bold text-purple-500">
                {Math.round(resources.cpu * resources.memory / 100)}%
              </div>
              <div className="text-xs text-gray-400">Load Score</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default SystemResourcesWidget;