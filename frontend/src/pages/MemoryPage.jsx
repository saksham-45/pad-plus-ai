import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { apiFetch } from '../services/api';

const labels = {
  total_episodes: 'Всего эпизодов',
  total_relations: 'Связей',
  avg_significance: 'Ср. значимость',
  topics: 'Темы',
  total_knowledge: 'Всего знаний',
  concepts: 'Концепции',
  procedures: 'Процедуры',
  avg_confidence: 'Уверенность',
  total_principles: 'Всего принципов',
  by_category: 'По категориям',
  immutable_count: 'Неизменяемых',
  preview: 'Превью',
  total_dialogs: 'Всего диалогов',
  traits: 'Черты',
  users_known: 'Пользователей',
  total_interactions: 'Взаимодействий',
  total_decisions: 'Всего решений',
  total_success: 'Успешных',
  overall_success_rate: 'Успешность',
  strategies_count: 'Стратегий',
  total_feedback: 'Всего отзывов',
  positive: 'Положительных',
  negative: 'Отрицательных',
  satisfaction_rate: 'Удовлетворённость',
};

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
                    {entries.map(([k, v]) => {
                      let display;
                      if (typeof v === 'number') {
                        display = v.toLocaleString();
                      } else if (typeof v === 'string') {
                        display = v.length > 150 ? v.slice(0, 150) + '...' : v;
                      } else if (Array.isArray(v)) {
                        const joined = v.join(', ');
                        display = joined.length > 150 ? joined.slice(0, 150) + '...' : (joined || '[]');
                      } else if (typeof v === 'object' && v !== null) {
                        display = JSON.stringify(v).slice(0, 150);
                      } else {
                        display = String(v);
                      }
                      return (
                        <div key={k} className="flex items-center justify-between text-sm">
                          <span className="text-gray-400">{labels[k] || k}</span>
                          <span className="font-medium text-right ml-2 max-w-[60%] truncate" title={typeof v === 'string' ? v : JSON.stringify(v)}>
                            {display}
                          </span>
                        </div>
                      );
                    })}
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
