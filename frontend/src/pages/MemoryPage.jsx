import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { apiFetch } from '../services/api';

const sections = [
  { key: 'episodic', icon: '📝', label: 'Эпизодическая память', color: 'text-blue-400' },
  { key: 'semantic', icon: '🧠', label: 'Семантическая память', color: 'text-purple-400' },
  { key: 'roots', icon: '🌳', label: 'Корневые принципы', color: 'text-green-400' },
  { key: 'rag', icon: '📚', label: 'RAG память', color: 'text-yellow-400' },
  { key: 'persona', icon: '👤', label: 'Личность', color: 'text-pink-400' },
  { key: 'meta_learner', icon: '🎯', label: 'Мета-обучение', color: 'text-cyan-400' },
  { key: 'feedback', icon: '⭐', label: 'Обратная связь', color: 'text-orange-400' },
];

export default function MemoryPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [consolidating, setConsolidating] = useState(false);
  const [consolidationResult, setConsolidationResult] = useState(null);

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/v1/memory/dashboard');
      if (res.ok) setData(await res.json());
    } catch (e) {
      console.error('Memory dashboard error:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchDashboard(); }, []);

  const handleConsolidation = async () => {
    setConsolidating(true);
    setConsolidationResult(null);
    try {
      const res = await apiFetch('/api/v1/memory/consolidation/trigger', { method: 'POST' });
      const result = await res.json();
      setConsolidationResult(result);
    } catch (e) {
      setConsolidationResult({ success: false, error: String(e) });
    } finally {
      setConsolidating(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-screen text-gray-400">Загрузка...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold">🧠 Memory Dashboard</h1>
          <Button onClick={handleConsolidation} loading={consolidating}>
            🔄 Запустить консолидацию
          </Button>
        </div>

        {consolidationResult && (
          <div className={`mb-4 p-3 rounded-lg text-sm ${consolidationResult.success ? 'bg-green-900/30 text-green-400 border border-green-800' : 'bg-red-900/30 text-red-400 border border-red-800'}`}>
            {consolidationResult.success ? '✅ Консолидация запущена' : `❌ Ошибка: ${consolidationResult.error}`}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sections.map(s => {
            const section = data?.[s.key];
            if (!section || section.status === 'unavailable') {
              return (
                <Card key={s.key} className="bg-gray-900/50 border-gray-700">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <span>{s.icon}</span>
                      {s.label}
                      <span className="text-xs text-red-400 ml-auto">offline</span>
                    </CardTitle>
                  </CardHeader>
                </Card>
              );
            }
            const entries = Object.entries(section).filter(([k]) => k !== 'status' && k !== 'error');
            return (
              <Card key={s.key} className="bg-gray-900/50 border-gray-700">
                <CardHeader className="pb-2">
                  <CardTitle className={`text-base flex items-center gap-2 ${s.color}`}>
                    <span>{s.icon}</span>
                    {s.label}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-1">
                    {entries.map(([k, v]) => (
                      <div key={k} className="flex items-center justify-between text-sm">
                        <span className="text-gray-400">{k}</span>
                        <span className="font-medium">
                          {typeof v === 'number' ? v : typeof v === 'string' && v.length > 100 ? v.slice(0, 100) + '...' : String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
