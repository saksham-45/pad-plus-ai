import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { motion } from 'framer-motion';

const healthMetrics = [
  { key: 'reflection_score', label: 'Reflection', icon: '🧠' },
  { key: 'learning_rate', label: 'Learning', icon: '📚' },
  { key: 'adaptation_score', label: 'Adaptation', icon: '🔄' },
  { key: 'memory_health', label: 'Memory', icon: '💾' },
  { key: 'coherence', label: 'Coherence', icon: '🔗' },
  { key: 'response_quality', label: 'Quality', icon: '⭐' },
  { key: 'safety_compliance', label: 'Safety', icon: '🛡️' },
  { key: 'emotional_balance', label: 'Balance', icon: '⚖️' },
];

function HealthIndicator({ label, value, icon }) {
  const percentage = (value || 0) * 100;
  const color = percentage >= 70 ? 'bg-green-500' : percentage >= 40 ? 'bg-yellow-500' : 'bg-red-500';
  
  return (
    <div className="flex items-center gap-3">
      <span className="text-xl">{icon}</span>
      <div className="flex-1">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-text-secondary">{label}</span>
          <span className="text-text-primary font-medium">{(value || 0).toFixed(2)}</span>
        </div>
        <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <motion.div
            className={`h-full ${color} rounded-full`}
            initial={{ width: 0 }}
            animate={{ width: `${percentage}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>
    </div>
  );
}

export function HealthWidget({ health = {} }) {
  const metrics = health?.metrics || {};
  const overall = health?.overall_score || 0;
  const status = health?.status || 'unknown';
  
  const statusColors = {
    excellent: 'text-green-500',
    good: 'text-green-500',
    fair: 'text-yellow-500',
    poor: 'text-orange-500',
    critical: 'text-red-500',
  };
  
  return (
    <Card hover className="h-full">
      <CardHeader>
        <CardTitle>
          <span className="text-xl mr-2">🏥</span>
          Health Monitor
          <span className={`ml-2 text-sm ${statusColors[status] || 'text-text-muted'}`}>
            ({status})
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mb-4 text-center">
          <div className="text-3xl font-bold text-text-primary">{overall.toFixed(2)}</div>
          <div className="text-xs text-text-secondary">Overall Score</div>
        </div>
        
        <div className="space-y-3">
          {healthMetrics.map((metric) => (
            <HealthIndicator
              key={metric.key}
              label={metric.label}
              value={metrics[metric.key]?.value || 0}
              icon={metric.icon}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default HealthWidget;