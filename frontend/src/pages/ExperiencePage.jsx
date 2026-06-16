import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { apiFetch } from '../services/api';

const TYPE_LABELS = {
  new_knowledge: 'Новое знание',
  contradiction: 'Противоречие',
  praise: 'Похвала',
  criticism: 'Критика',
  exploration: 'Исследование',
  error_recovery: 'Восстановление',
  repetition: 'Повтор',
};

const TYPE_COLORS = {
  new_knowledge: 'text-blue-400',
  contradiction: 'text-red-400',
  praise: 'text-green-400',
  criticism: 'text-orange-400',
  exploration: 'text-purple-400',
  error_recovery: 'text-yellow-400',
  repetition: 'text-gray-400',
};

export default function ExperiencePage() {
  const [experiences, setExperiences] = useState(null);
  const [deltas, setDeltas] = useState(null);
  const [activeSection, setActiveSection] = useState('stats');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiFetch('/api/v1/admin/experiences?limit=50'),
      apiFetch('/api/v1/admin/persona/deltas'),
    ]).then(async ([expRes, delRes]) => {
      if (expRes.ok) setExperiences(await expRes.json());
      if (delRes.ok) setDeltas(await delRes.json());
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-text-secondary">Загрузка...</div>
      </div>
    );
  }

  const stats = experiences || {};
  const typeDist = stats.type_distribution || {};
  const total = stats.total || 0;
  const avgSig = stats.avg_significance || 0;
  const records = stats.records || [];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-text-primary">Опыт системы</h2>

      {/* Навигация по секциям */}
      <div className="flex gap-2 border-b border-border pb-2">
        {[
          { id: 'stats', label: 'Статистика' },
          { id: 'records', label: 'Записи' },
          { id: 'deltas', label: 'Коэффициенты' },
        ].map(s => (
          <button
            key={s.id}
            onClick={() => setActiveSection(s.id)}
            className={`px-4 py-2 rounded-lg text-sm transition-colors ${
              activeSection === s.id
                ? 'bg-primary text-white'
                : 'text-text-secondary hover:text-text-primary hover:bg-gray-800'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Статистика */}
      {activeSection === 'stats' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent>
              <div className="text-3xl font-bold text-text-primary">{total}</div>
              <div className="text-sm text-text-secondary mt-1">Всего записей</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <div className="text-3xl font-bold text-blue-400">{avgSig.toFixed(3)}</div>
              <div className="text-sm text-text-secondary mt-1">Средняя significance</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <div className="text-3xl font-bold text-green-400">{Object.keys(typeDist).length}</div>
              <div className="text-sm text-text-secondary mt-1">Типов взаимодействий</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <div className="text-3xl font-bold text-purple-400">{Math.round(total / (avgSig || 0.01))}</div>
              <div className="text-sm text-text-secondary mt-1">Оценка влияния</div>
            </CardContent>
          </Card>

          {/* Распределение по типам */}
          <Card className="md:col-span-2 lg:col-span-4">
            <CardHeader><CardTitle>Распределение по типам</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-2">
                {Object.entries(typeDist)
                  .sort((a, b) => b[1] - a[1])
                  .map(([type, count]) => {
                    const pct = total > 0 ? (count / total * 100) : 0;
                    const barWidth = Math.max(pct * 2, 2);
                    return (
                      <div key={type} className="flex items-center gap-4">
                        <span className={`w-36 text-sm font-medium ${TYPE_COLORS[type] || 'text-text-primary'}`}>
                          {TYPE_LABELS[type] || type}
                        </span>
                        <div className="flex-1 h-5 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary/60 rounded-full transition-all duration-500"
                            style={{ width: `${barWidth}%` }}
                          />
                        </div>
                        <span className="w-16 text-right text-sm text-text-secondary">{count}</span>
                        <span className="w-12 text-right text-xs text-text-secondary">{pct.toFixed(0)}%</span>
                      </div>
                    );
                  })}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Записи опыта */}
      {activeSection === 'records' && (
        <Card>
          <CardHeader><CardTitle>Последние записи ({records.length})</CardTitle></CardHeader>
          <CardContent>
            {records.length === 0 ? (
              <div className="text-text-secondary text-center py-8">Нет записей опыта</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-text-secondary">
                      <th className="text-left py-2 pr-4">Тип</th>
                      <th className="text-left py-2 pr-4">Significance</th>
                      <th className="text-left py-2 pr-4">Пользователь</th>
                      <th className="text-left py-2 pr-4">Ответ AI</th>
                      <th className="text-left py-2 pr-4">Дельта</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map((r, i) => (
                      <tr key={i} className="border-b border-border/50 hover:bg-gray-800/30">
                        <td className={`py-2 pr-4 font-medium ${TYPE_COLORS[r.interaction_type] || ''}`}>
                          {TYPE_LABELS[r.interaction_type] || r.interaction_type}
                        </td>
                        <td className="py-2 pr-4">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            r.significance >= 0.7 ? 'bg-red-900/50 text-red-300' :
                            r.significance >= 0.4 ? 'bg-yellow-900/50 text-yellow-300' :
                            'bg-gray-800 text-gray-300'
                          }`}>
                            {r.significance?.toFixed(2)}
                          </span>
                        </td>
                        <td className="py-2 pr-4 max-w-[200px] truncate text-text-secondary">
                          {r.user_message}
                        </td>
                        <td className="py-2 pr-4 max-w-[200px] truncate text-text-secondary">
                          {r.ai_response}
                        </td>
                        <td className="py-2 pr-4 text-text-secondary text-xs max-w-[200px] truncate">
                          {r.delta}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Коэффициенты дельт */}
      {activeSection === 'deltas' && deltas && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[
            { key: 'emotion', title: 'Эмоции (EmotionUpdatePhase)', color: 'text-pink-400' },
            { key: 'impulse', title: 'Импульс (ImpulseUpdatePhase)', color: 'text-cyan-400' },
            { key: 'persona_system', title: 'Персона системы (PersonaEvolutionPhase)', color: 'text-amber-400' },
            { key: 'persona_user_style', title: 'Стиль пользователя (PersonaEvolutionPhase)', color: 'text-emerald-400' },
          ].map(section => (
            <Card key={section.key}>
              <CardHeader>
                <CardTitle className={section.color}>{section.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(deltas[section.key]?.deltas || {}).map(([type, changes]) => (
                    <div key={type} className="flex items-start gap-2 text-sm">
                      <span className={`w-28 shrink-0 font-medium ${TYPE_COLORS[type] || ''}`}>
                        {TYPE_LABELS[type] || type}
                      </span>
                      <span className="text-text-secondary">
                        {Array.isArray(changes)
                          ? changes.map(([t, d]) => `${t}${d > 0 ? '+' : ''}${d}`).join(', ')
                          : typeof changes === 'object'
                            ? Object.entries(changes).map(([t, d]) => `${t}${d > 0 ? '+' : ''}${d}`).join(', ')
                            : String(changes)
                        }
                      </span>
                    </div>
                  ))}
                </div>
                {deltas[section.key]?.note && (
                  <p className="text-xs text-text-secondary mt-3 italic">{deltas[section.key].note}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}


