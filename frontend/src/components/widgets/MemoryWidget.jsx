import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';

const memoryTypes = [
  { key: 'rag', label: 'RAG Memory', icon: '🧠', color: 'bg-purple-500', field: 'total_dialogs' },
  { key: 'episodic', label: 'Episodic', icon: '📹', color: 'bg-blue-500', field: 'total_episodes' },
  { key: 'semantic', label: 'Semantic', icon: '📚', color: 'bg-green-500', field: 'total_knowledge' },
  { key: 'fact', label: 'Facts', icon: '💡', color: 'bg-yellow-500', field: 'total_facts' },
  { key: 'roots', label: 'Roots', icon: '🌱', color: 'bg-orange-500', field: 'total_roots' },
];

function MemoryCard({ label, count, icon, color, max }) {
  const percentage = max ? (count / max) * 100 : 0;
  
  return (
    <div className="bg-gray-800/50 rounded-xl p-4 border border-border">
      <div className="flex items-center gap-3 mb-3">
        <span className="text-2xl">{icon}</span>
        <div>
          <div className="text-2xl font-bold text-text-primary">{count?.toLocaleString() || 0}</div>
          <div className="text-xs text-text-secondary">{label}</div>
        </div>
      </div>
      <div className="h-1 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${Math.min(percentage, 100)}%` }} />
      </div>
    </div>
  );
}

export function MemoryWidget({ memory = {} }) {
  // Получаем данные из API для каждого типа памяти
  const stats = {};
  
  memoryTypes.forEach(type => {
    const memoryData = memory[type.key] || {};
    const field = type.field;
    stats[type.key] = memoryData[field] || 0;
  });
  
  const maxCount = Math.max(...Object.values(stats), 1);
  
  return (
    <Card hover className="h-full">
      <CardHeader>
        <CardTitle>
          <span className="text-xl mr-2">💾</span>
          Memory Stats
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3">
          {memoryTypes.map((type) => (
            <MemoryCard
              key={type.key}
              label={type.label}
              count={stats[type.key]}
              icon={type.icon}
              color={type.color}
              max={maxCount}
            />
          ))}
        </div>
        
        {memory.rag?.topic_distribution && (
          <div className="mt-4">
            <div className="text-xs text-text-secondary mb-2">Topic Distribution</div>
            <div className="flex flex-wrap gap-1">
              {Object.entries(memory.rag.topic_distribution).slice(0, 6).map(([topic, count]) => (
                <span
                  key={topic}
                  className="px-2 py-1 bg-gray-800 rounded text-xs text-text-muted"
                >
                  {topic}: {count}
                </span>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default MemoryWidget;
