import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';

export function KnowledgeWidget({ knowledge = {} }) {
  const nodes = knowledge?.nodes || 0;
  const edges = knowledge?.edges || 0;
  const avgConfidence = knowledge?.avg_confidence || 0;
  
  return (
    <Card hover className="h-full">
      <CardHeader>
        <CardTitle>
          <span className="text-xl mr-2">🕸️</span>
          Knowledge Graph
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="bg-gray-800/50 rounded-xl p-4">
            <div className="text-2xl font-bold text-purple-500">{nodes}</div>
            <div className="text-xs text-text-secondary mt-1">Nodes</div>
          </div>
          <div className="bg-gray-800/50 rounded-xl p-4">
            <div className="text-2xl font-bold text-cyan-500">{edges}</div>
            <div className="text-xs text-text-secondary mt-1">Edges</div>
          </div>
          <div className="bg-gray-800/50 rounded-xl p-4">
            <div className="text-2xl font-bold text-green-500">{(avgConfidence * 100).toFixed(0)}%</div>
            <div className="text-xs text-text-secondary mt-1">Confidence</div>
          </div>
        </div>
        
        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex justify-between text-xs">
            <span className="text-text-secondary">Graph Density</span>
            <span className="text-text-primary">
              {nodes > 0 ? (edges / (nodes * (nodes - 1) / 2) * 100).toFixed(1) : 0}%
            </span>
          </div>
          <div className="flex justify-between text-xs mt-2">
            <span className="text-text-secondary">Avg Connections</span>
            <span className="text-text-primary">
              {nodes > 0 ? (edges / nodes).toFixed(1) : 0}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default KnowledgeWidget;