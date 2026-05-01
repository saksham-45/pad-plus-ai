import { useState, useEffect } from 'react';

const providerIcons = {
  google: '🔵',
  groq: '⚡',
  openai: '🟢',
  anthropic: '🟠',
  openrouter: '🟣',
  ollama: '🦙',
  gemini: '💎',
  gigachat: '🇷🇺',
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
  fast: ['gemini-2.0-flash', 'llama-3.1-70b-versatile', 'gpt-3.5-turbo', 'mixtral-8x7b-32768'],
  smart: ['gpt-4', 'claude-3-sonnet', 'gemini-1.5-pro', 'llama-3.1-405b'],
  cheap: ['gpt-3.5-turbo', 'gemini-2.0-flash', 'llama-3.1-70b-versatile'],
  free: ['gemini-2.0-flash', 'llama-3.1-70b-versatile'],
};

// Статические модели по провайдерам (если БД не подключена)
const staticModels = [
  { id: 'gemini-2.0-flash', name: 'Google Gemini 2.0 Flash', provider: 'google', providerName: 'Google', icon: '🔵', isDefault: false },
  { id: 'llama-3.1-70b-versatile', name: 'Llama 3.1 70B (Groq)', provider: 'groq', providerName: 'Groq', icon: '⚡', isDefault: false },
  { id: 'gpt-4', name: 'OpenAI GPT-4', provider: 'openai', providerName: 'OpenAI', icon: '🟢', isDefault: false },
  { id: 'gpt-3.5-turbo', name: 'OpenAI GPT-3.5 Turbo', provider: 'openai', providerName: 'OpenAI', icon: '🟢', isDefault: false },
  { id: 'claude-3-5-sonnet', name: 'Anthropic Claude 3.5 Sonnet', provider: 'anthropic', providerName: 'Anthropic', icon: '🟠', isDefault: false },
  { id: 'claude-3-haiku', name: 'Anthropic Claude 3 Haiku', provider: 'anthropic', providerName: 'Anthropic', icon: '🟠', isDefault: false },
];

export function ModelSelector({ value, onChange, keys = [] }) {
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  // Собираем модели из ключей (если БД подключена)
  const dbModels = keys
    .filter(k => k.is_active)
    .map(key => ({
      id: key.model_preference || 'auto',
      name: key.model_preference === 'auto' 
        ? `${key.provider_display_name} (Auto)` 
        : key.model_preference,
      provider: key.provider,
      providerName: key.provider_display_name,
      icon: providerIcons[key.provider] || '🔗',
      isDefault: key.is_default,
      keyId: key.id,
    }))
    .filter((v, i, a) => a.findIndex(t => t.id === v.id) === i);

  // Используем модели из БД или статические (если БД не подключена)
  const availableModels = dbModels.length > 0 ? dbModels : staticModels;

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

      {/* Фильтры */}
      <div className="flex gap-2 overflow-x-auto pb-2">
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