import { useState, useEffect } from 'react';
import { apiFetch } from '../services/api';

const providerIcons = {
  google: '🔵',
  groq: '⚡',
  openai: '🟢',
  anthropic: '🟠',
  openrouter: '🟣',
  ollama: '🦙',
  gemini: '💎',
  gigachat: '🇷🇺',
  mistral: '🌫️',
  cohere: '🟣',
  deepseek: '🔍',
  xai: '🧮',
  azure: '🔵',
  together: '🤝',
  fireworks: '🎆',
  nvidia: '🟩',
};

const modelFilters = [
  { id: 'all', label: 'Все' },
  { id: 'fast', label: '⚡ Быстрые' },
  { id: 'smart', label: '🧠 Умные' },
  { id: 'cheap', label: '💰 Дешёвые' },
  { id: 'free', label: '🆓 Бесплатные' },
];

// Категории моделей
const modelCategories = {
  fast: ['gemini-2.0-flash', 'llama-3.1-70b-versatile', 'gpt-4o-mini', 'mixtral-8x7b-32768'],
  smart: ['gpt-4o', 'claude-3-5-sonnet', 'gemini-1.5-pro', 'llama-3.3-70b'],
  cheap: ['gpt-4o-mini', 'gemini-2.0-flash', 'llama-3.1-8b-instant'],
  free: ['gemini-2.0-flash', 'llama-3.1-70b-versatile', 'llama-3.1-8b-instant'],
};

// Fallback модели (если API недоступен)
const fallbackModels = [
  { id: 'gemini-2.0-flash', name: 'Google Gemini 2.0 Flash', provider: 'google', providerName: 'Google', icon: '🔵' },
  { id: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B (Groq)', provider: 'groq', providerName: 'Groq', icon: '⚡' },
  { id: 'gpt-4o', name: 'OpenAI GPT-4o', provider: 'openai', providerName: 'OpenAI', icon: '🟢' },
  { id: 'gpt-4o-mini', name: 'OpenAI GPT-4o Mini', provider: 'openai', providerName: 'OpenAI', icon: '🟢' },
  { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', provider: 'anthropic', providerName: 'Anthropic', icon: '🟠' },
  { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku', provider: 'anthropic', providerName: 'Anthropic', icon: '🟠' },
];

export function ModelSelector({ value, onChange, keys = [] }) {
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [apiModels, setApiModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(false);

  // Загрузка всех моделей через API
  useEffect(() => {
    loadAllModels();
  }, []);

  const loadAllModels = async (forceRefresh = false) => {
    setModelsLoading(true);
    try {
      const url = forceRefresh ? '/api/v1/models?refresh=true' : '/api/v1/models';
      const response = await apiFetch(url);
      if (response.ok) {
        const data = await response.json();
        const models = (data.models || []).map(m => ({
          id: m.id || m.name,
          name: m.name || m.id,
          provider: m.provider || m.id?.split('/')[0] || 'unknown',
          providerName: m.provider || m.id?.split('/')[0] || 'Unknown',
          icon: providerIcons[m.provider || m.id?.split('/')[0]] || '🔗',
        }));
        if (models.length > 0) {
          setApiModels(models);
        }
      }
    } catch (error) {
      console.error('Failed to load models:', error);
    } finally {
      setModelsLoading(false);
    }
  };

  // Собираем модели из ключей (если БД подключена)
  const dbModels = keys
    .filter(k => k.is_active)
    .map(key => {
      const modelPref = key.model_preference || 'auto';
      // Исправляем формат: если модель начинается с provider/ (например, openrouter/auto),
      // используем её как есть. Если просто 'auto' или имя модели — добавляем provider/
      let modelId = modelPref;
      if (modelPref === 'auto') {
        modelId = `${key.provider}/auto`;
      } else if (!modelPref.includes('/')) {
        modelId = `${key.provider}/${modelPref}`;
      }
      
      return {
        id: modelId,
        name: modelPref === 'auto' 
          ? `${key.provider_display_name} (Auto)` 
          : modelPref,
        provider: key.provider,
        providerName: key.provider_display_name,
        icon: providerIcons[key.provider] || '🔗',
        isDefault: key.is_default,
        keyId: key.id,
      };
    })
    .filter((v, i, a) => a.findIndex(t => t.id === v.id) === i);

  // Приоритет: ключи пользователя → API → пустой список
  const hasActiveKeys = keys.some(k => k.is_active);
  const availableModels = dbModels.length > 0 ? dbModels : (apiModels.length > 0 ? apiModels : (hasActiveKeys ? fallbackModels : []));

  // Фильтруем модели
  const filteredModels = availableModels.filter(model => {
    if (filter === 'all') return true;
    if (filter === 'free') {
      return modelCategories.free.some(m => model.id.includes(m) || model.name.includes(m));
    }
    return modelCategories[filter]?.some(m => model.id.includes(m) || model.name.includes(m));
  }).filter(model => 
    model.name.toLowerCase().includes(search.toLowerCase()) ||
    model.providerName.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-3">
      {/* Поиск */}
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Поиск модели..."
        className="w-full px-3 py-2 bg-gray-800 border border-border rounded-lg text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
      />

      {/* Фильтры + обновление */}
      <div className="flex gap-2 overflow-x-auto pb-2 items-center">
        {modelFilters.map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`px-3 py-1 rounded-full text-xs whitespace-nowrap transition-colors ${
              filter === f.id
                ? 'bg-primary text-white'
                : 'bg-gray-800 text-text-secondary hover:text-text-primary'
            }`}
          >
            {f.label}
          </button>
        ))}
        <button
          onClick={() => loadAllModels(true)}
          disabled={modelsLoading}
          className="px-3 py-1 rounded-full text-xs whitespace-nowrap text-primary hover:text-primary/80 disabled:opacity-50 ml-auto"
          title="Обновить список моделей"
        >
          {modelsLoading ? '⏳' : '🔄'}
        </button>
      </div>

      {/* Список моделей */}
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {filteredModels.length === 0 ? (
          <div className="text-center text-text-muted py-4 text-sm">
            Нет доступных моделей. Добавьте API ключи в настройках.
          </div>
        ) : (
          filteredModels.map(model => (
            <button
              key={`${model.keyId}-${model.id}`}
              onClick={() => onChange && onChange(model)}
              className={`w-full p-3 rounded-lg border text-left transition-all flex items-center gap-3 ${
                value?.keyId === model.keyId
                  ? 'border-primary bg-primary/10'
                  : 'border-border hover:border-primary/50 hover:bg-gray-800/50'
              }`}
            >
              <span className="text-xl">{model.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-text-primary truncate">
                  {model.name}
                </div>
                <div className="text-xs text-text-secondary">
                  {model.providerName}
                  {model.isDefault && (
                    <span className="ml-2 text-primary">• По умолчанию</span>
                  )}
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}

export default ModelSelector;