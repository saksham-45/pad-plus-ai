import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { apiFetch } from '../services/api';

export default function KnowledgePage() {
  const [stats, setStats] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [graph, setGraph] = useState(null);

  useEffect(() => {
    apiFetch('/api/v1/knowledge/stats').then(r => r.ok && r.json().then(setStats)).catch(() => {});
    apiFetch('/api/v1/knowledge/graph?limit=30').then(r => r.ok && r.json().then(setGraph)).catch(() => {});
  }, []);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await apiFetch(`/api/v1/knowledge/search?q=${encodeURIComponent(searchQuery)}&limit=20`);
      if (res.ok) setResults((await res.json()).concepts || []);
    } catch (e) {
      console.error('Knowledge search error:', e);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-2xl font-semibold mb-6">🔗 Граф знаний</h1>

        {stats && (
          <div className="grid grid-cols-3 gap-4 mb-6">
            <Card className="bg-gray-900/50 border-gray-700">
              <CardContent className="p-4">
                <p className="text-xs text-gray-400">Концепции</p>
                <p className="text-2xl font-bold text-blue-400">{stats.total_entities || stats.entities || 0}</p>
              </CardContent>
            </Card>
            <Card className="bg-gray-900/50 border-gray-700">
              <CardContent className="p-4">
                <p className="text-xs text-gray-400">Связи</p>
                <p className="text-2xl font-bold text-purple-400">{stats.total_relations || stats.relations || 0}</p>
              </CardContent>
            </Card>
            <Card className="bg-gray-900/50 border-gray-700">
              <CardContent className="p-4">
                <p className="text-xs text-gray-400">Графы</p>
                <p className="text-2xl font-bold text-green-400">{stats.graphs_count || stats.graphs || 0}</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Search */}
        <div className="flex gap-2 mb-6">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Поиск концепций..."
            className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
          />
          <Button onClick={handleSearch} loading={searching}>🔍 Поиск</Button>
        </div>

        {/* Results */}
        {results.length > 0 && (
          <Card className="bg-gray-900/50 border-gray-700 mb-6">
            <CardHeader><CardTitle>Найдено концепций: {results.length}</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {results.map((c, i) => (
                  <div key={c.id || i} className="p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                    <div className="font-medium text-blue-400">{c.name}</div>
                    <div className="text-xs text-gray-400 mt-1">{c.type || c.concept_type}</div>
                    {c.description && <div className="text-xs text-gray-500 mt-1">{c.description.slice(0, 100)}</div>}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Simple graph visualization */}
        {graph?.nodes?.length > 0 && (
          <Card className="bg-gray-900/50 border-gray-700">
            <CardHeader><CardTitle>Граф ({graph.nodes.length} узлов)</CardTitle></CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {graph.nodes.map((n, i) => (
                  <span key={n.id || i} className="px-3 py-1 bg-blue-900/30 border border-blue-800 rounded-full text-xs text-blue-300">
                    {n.name}
                  </span>
                ))}
              </div>
              {graph.edges?.length > 0 && (
                <div className="mt-4 text-xs text-gray-500">
                  {graph.edges.length} связей между узлами
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
