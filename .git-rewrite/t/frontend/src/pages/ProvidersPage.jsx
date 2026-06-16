import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import {
  getCachedModels,
  cacheModels,
  getCacheStatus,
  getAvailableModels,
  formatModelInfo,
  clearAllCache
} from '../services/modelCache';

const clearCache = (providerId) => {
  // Clear cache for specific provider
  try {
    localStorage.removeItem(`models_${providerId}`);
    localStorage.removeItem(`models_${providerId}_timestamp`);
  } catch {}
};

// Полный список провайдеров LiteLLM (с массивами моделей)
const litellmProviders = [
  { id: 'openai', name: 'OpenAI', models: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 'gpt-4o'], latency: 'Low', cost: 'High', type: 'API Key' },
  { id: 'google', name: 'Google Gemini', models: ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'], latency: 'Low', cost: 'Medium', type: 'API Key' },
  { id: 'anthropic', name: 'Anthropic Claude', models: ['claude-3-5-sonnet', 'claude-3-haiku', 'claude-3-opus'], latency: 'Medium', cost: 'High', type: 'API Key' },
  { id: 'groq', name: 'Groq', models: ['llama-3.1-70b-versatile', 'mixtral-8x7b-32768', 'gemma2-9b-it'], latency: 'Ultra', cost: 'Low', type: 'API Key' },
  { id: 'openrouter', name: 'OpenRouter', models: ['openrouter/auto', 'openai/gpt-4', 'google/gemini-2.0-flash', 'anthropic/claude-3-sonnet', 'meta-llama/llama-3-70b-instruct'], latency: 'Medium', cost: 'Medium', type: 'API Key' },
  { id: 'azure', name: 'Azure OpenAI', models: ['gpt-4', 'gpt-35-turbo'], latency: 'Low', cost: 'High', type: 'API Key' },
  { id: 'cohere', name: 'Cohere', models: ['command-r-plus', 'command-r', 'command'], latency: 'Medium', cost: 'Medium', type: 'API Key' },
  { id: 'huggingface', name: 'HuggingFace', models: ['mistralai/Mistral-7B', 'meta-llama/Llama-2-70b'], latency: 'Medium', cost: 'Free', type: 'API Key' },
  { id: 'together', name: 'Together AI', models: ['meta-llama/Llama-3-70b', 'mistralai/Mixtral-8x7B'], latency: 'Medium', cost: 'Medium', type: 'API Key' },
  { id: 'anyscale', name: 'Anyscale', models: ['meta-llama/Llama-2-70b', 'mistralai/Mistral-7B'], latency: 'Medium', cost: 'Medium', type: 'API Key' },
  { id: 'deepinfra', name: 'DeepInfra', models: ['mistralai/Mistral-7B', 'meta-llama/Llama-2-70b'], latency: 'Medium', cost: 'Free', type: 'API Key' },
  { id: 'replicate', name: 'Replicate', models: ['meta/llama-2-70b', 'mistralai/mistral-7b'], latency: 'High', cost: 'Medium', type: 'API Key' },
  { id: 'ollama', name: 'Ollama (Local)', models: ['llama2', 'mistral', 'codellama'], latency: 'None', cost: 'Free', type: 'Local' },
  { id: 'deepseek', name: 'DeepSeek', models: ['deepseek-chat', 'deepseek-coder'], latency: 'Medium', cost: 'Free', type: 'API Key' },
  { id: 'xai', name: 'xAI Grok', models: ['grok-beta'], latency: 'Medium', cost: 'High', type: 'API Key' },
  { id: 'mistral', name: 'Mistral AI', models: ['mistral-large', 'mistral-medium', 'open-mistral-7b'], latency: 'Low', cost: 'Medium', type: 'API Key' },
  { id: 'nvidia', name: 'NVIDIA NIM', models: ['meta/llama3-70b-instruct', 'mistralai/mistral-large'], latency: 'Low', cost: 'High', type: 'API Key' },
  { id: 'fireworks', name: 'Fireworks', models: ['accounts/fireworks/models/llama-v3-70b-instruct'], latency: 'Medium', cost: 'Free', type: 'API Key' },
  { id: 'gigachat', name: 'GigaChat', models: ['GigaChat', 'GigaChat-Pro'], latency: 'Low', cost: 'Medium', type: 'OAuth' },
  { id: 'yandex', name: 'YandexGPT', models: ['yandexgpt-lite'], latency: 'Low', cost: 'Medium', type: 'API Key' },
];

// Все доступные провайдеры (для отображения)
const allProviders = [
  { id: 'openai', name: 'OpenAI', icon: '🟢', models: 4, latency: 'Low', cost: 'High', type: 'API Key' },
  { id: 'google', name: 'Google Gemini', icon: '🔮', models: 3, latency: 'Low', cost: 'Medium', type: 'API Key' },
  { id: 'anthropic', name: 'Anthropic Claude', icon: '🧠', models: 3, latency: 'Medium', cost: 'High', type: 'API Key' },
  { id: 'groq', name: 'Groq', icon: '⚡', models: 3, latency: 'Ultra', cost: 'Low', type: 'API Key' },
  { id: 'openrouter', name: 'OpenRouter', icon: '🌐', models: 5, latency: 'Medium', cost: 'Medium', type: 'API Key' },
  { id: 'azure', name: 'Azure OpenAI', icon: '🔵', models: 2, latency: 'Low', cost: 'High', type: 'API Key' },
  { id: 'cohere', name: 'Cohere', icon: '🟣', models: 3, latency: 'Medium', cost: 'Medium', type: 'API Key' },
  { id: 'huggingface', name: 'HuggingFace', icon: '🤗', models: 2, latency: 'Medium', cost: 'Free', type: 'API Key' },
  { id: 'together', name: 'Together AI', icon: '🤝', models: 2, latency: 'Medium', cost: 'Medium', type: 'API Key' },
  { id: 'anyscale', name: 'Anyscale', icon: '🔷', models: 2, latency: 'Medium', cost: 'Medium', type: 'API Key' },
  { id: 'deepinfra', name: 'DeepInfra', icon: '🏗️', models: 2, latency: 'Medium', cost: 'Free', type: 'API Key' },
  { id: 'replicate', name: 'Replicate', icon: '🔄', models: 2, latency: 'High', cost: 'Medium', type: 'API Key' },
  { id: 'ollama', name: 'Ollama (Local)', icon: '🦙', models: 3, latency: 'None', cost: 'Free', type: 'Local' },
  { id: 'deepseek', name: 'DeepSeek', icon: '🔍', models: 2, latency: 'Medium', cost: 'Free', type: 'API Key' },
  { id: 'xai', name: 'xAI Grok', icon: '🧮', models: 1, latency: 'Medium', cost: 'High', type: 'API Key' },
  { id: 'mistral', name: 'Mistral AI', icon: '🌫️', models: 3, latency: 'Low', cost: 'Medium', type: 'API Key' },
  { id: 'nvidia', name: 'NVIDIA NIM', icon: '🟩', models: 2, latency: 'Low', cost: 'High', type: 'API Key' },
  { id: 'fireworks', name: 'Fireworks', icon: '🎆', models: 1, latency: 'Medium', cost: 'Free', type: 'API Key' },
  { id: 'gigachat', name: 'GigaChat', icon: '🇷🇺', models: 2, latency: 'Low', cost: 'Medium', type: 'OAuth' },
  { id: 'yandex', name: 'YandexGPT', icon: '🟡', models: 1, latency: 'Low', cost: 'Medium', type: 'API Key' },
];

// Быстрый старт шаги
const quickStartSteps = [
  {
    step: 1,
    title: 'Connect Provider',
    description: 'Click "Connect" on any available provider. Enter your API key (or OAuth credentials for GigaChat).',
  },
  {
    step: 2,
    title: 'Set Default',
    description: 'Check "Set as default" when adding a key, or click "Manage" on a connected provider to change.',
  },
  {
    step: 3,
    title: 'Use in Chat',
    description: 'Go to Chat tab. Your default model will be used automatically for all requests.',
  },
];

// Типы аутентификации
const authTypes = [
  { type: 'API Key', example: 'sk-...', color: 'text-blue-500' },
  { type: 'OAuth', example: 'Client ID + Secret (GigaChat)', color: 'text-purple-500' },
  { type: 'Local', example: 'URL (Ollama)', color: 'text-green-500' },
];

export default function ProvidersPage() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState('all'); // all, connected, available
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [providerModels, setProviderModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [showManualInput, setShowManualInput] = useState(false);
  const [manualModel, setManualModel] = useState('');
  const [cacheStatus, setCacheStatus] = useState({ status: 'none', message: 'Нет кэша' });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editingKey, setEditingKey] = useState(null);
  const [editModel, setEditModel] = useState('');

  // Загрузка подключенных ключей
  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/keys?offset=0&limit=100', {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const result = await response.json();
        const keysData = result.data || result;
        setKeys(Array.isArray(keysData) ? keysData : []);
      }
    } catch (error) {
      console.error('Failed to fetch keys:', error);
      setKeys([]);
    } finally {
      setLoading(false);
    }
  };

  // Получение статуса провайдера
  const getProviderStatus = (providerId) => {
    const providerKey = keys.find(k => k.provider === providerId);
    if (!providerKey) return { status: 'Available', color: 'text-gray-400', badge: 'bg-gray-500/10 text-gray-400' };
    if (providerKey.is_default) return { status: 'Active', color: 'text-green-500', badge: 'bg-green-500/10 text-green-500' };
    return { status: 'Connected', color: 'text-blue-500', badge: 'bg-blue-500/10 text-blue-500' };
  };

  // Фильтрация провайдеров
  const filteredProviders = allProviders.filter(provider => {
    const matchesSearch = provider.name.toLowerCase().includes(searchQuery.toLowerCase());
    const status = getProviderStatus(provider.id);
    if (filter === 'connected') return matchesSearch && status.status !== 'Available';
    if (filter === 'available') return matchesSearch && status.status === 'Available';
    return matchesSearch;
  });

  // Статистика
  const connectedCount = keys.length;
  const activeModel = keys.find(k => k.is_default);

  // Обработчик подключения - открывает форму добавления ключа
  const handleConnect = (provider) => {
    const fullProvider = litellmProviders.find(p => p.id === provider.id);
    if (fullProvider) {
      setSelectedProvider(fullProvider);
      setShowAddForm(true);
      loadModels(fullProvider.id);
    }
  };

  // Загрузка моделей (из кэша или API)
  const loadModels = async (providerId, forceRefresh = false) => {
    const status = getCacheStatus(providerId);
    setCacheStatus(status);

    if (!forceRefresh && status.status === 'fresh') {
      const cached = getCachedModels(providerId);
      if (cached) {
        const availableModels = getAvailableModels(cached.models);
        setProviderModels(availableModels);
        return;
      }
    }

    if (forceRefresh || status.status === 'stale' || status.status === 'none') {
      await fetchModelsFromApi(providerId);
    }
  };

  // Загрузка моделей из API
  const fetchModelsFromApi = async (providerId) => {
    setIsRefreshing(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/providers/${providerId}/models`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      if (response.ok) {
        const data = await response.json();
        const models = data.models || [];

        cacheModels(providerId, models);
        setCacheStatus(getCacheStatus(providerId));
        const availableModels = getAvailableModels(models);
        setProviderModels(availableModels);
      } else {
        useStaticModels(providerId);
      }
    } catch (error) {
      console.error('Failed to fetch models from API:', error);
      useStaticModels(providerId);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Использование статических моделей (fallback)
  const useStaticModels = (providerId) => {
    const fullProvider = litellmProviders.find(p => p.id === providerId);
    if (fullProvider) {
      const staticModels = fullProvider.models.map(m => ({
        id: m,
        name: m,
        cost: 'unknown',
        isStatic: true
      }));
      setProviderModels(staticModels);
      setCacheStatus({ status: 'stale', message: 'Данные устарели (статические)' });
    }
  };

  // Обработчик кнопки обновления
  const handleRefreshModels = async () => {
    if (selectedProvider) {
      await loadModels(selectedProvider.id, true);
    }
  };

  // Обработчик добавления ключа
  const handleAddKey = async (formData) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      });
      if (response.ok) {
        const newKey = await response.json();  // Получаем ID нового ключа
        await fetchKeys();
        setShowAddForm(false);
        setSelectedProvider(null);
        if (selectedProvider) {
          clearCache(selectedProvider.id);
        }
        alert('Провайдер успешно подключен!');
        // Отправляем событие для обновления в App.jsx
        window.dispatchEvent(new CustomEvent('keys-updated'));
        if (formData.is_default) {
          const actualKeyId = newKey?.id || newKey?.data?.[0]?.id;
          window.dispatchEvent(new CustomEvent('model-changed', {
            detail: {
              id: formData.model_preference || 'auto',
              name: formData.model_preference === 'auto' ? `${formData.provider} (Auto)` : formData.model_preference,
              keyId: actualKeyId,
              provider: formData.provider,
              providerName: formData.provider,
              isDefault: true,
            }
          }));
        }
      }
    } catch (err) {
      console.error('Failed to add key:', err);
      alert('Ошибка при подключении провайдера');
    }
  };

  // Обработчик установки по умолчанию
  const handleSetDefault = async (keyId) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/keys/${keyId}/set-default`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        await fetchKeys();
        // Отправляем событие для обновления в App.jsx
        window.dispatchEvent(new CustomEvent('keys-updated'));
      }
    } catch (error) {
      console.error('Failed to set default key:', error);
    }
  };

  // Обработчик удаления ключа
  const handleDelete = async (keyId) => {
    if (!confirm('Удалить этот API ключ?')) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/keys/${keyId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        await fetchKeys();
        // Отправляем событие для обновления в App.jsx
        window.dispatchEvent(new CustomEvent('keys-updated'));
      }
    } catch (error) {
      console.error('Failed to delete key:', error);
    }
  };

  // Обработчик открытия формы редактирования
  const handleEdit = (key) => {
    setEditingKey(key);
    setEditModel(key.model_preference);
    setShowEditForm(true);
    // Загружаем модели для этого провайдера
    loadModels(key.provider);
  };

  // Обработчик сохранения изменений
  const handleSaveEdit = async () => {
    if (!editingKey) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/keys/${editingKey.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          model_preference: editModel,
        }),
      });

      if (response.ok) {
        await fetchKeys();
        setShowEditForm(false);
        setEditingKey(null);
        // Отправляем событие для обновления
        window.dispatchEvent(new CustomEvent('keys-updated'));
        alert('Модель успешно обновлена!');
      }
    } catch (error) {
      console.error('Failed to update key:', error);
      alert('Ошибка при обновлении модели');
    }
  };

  // Получение цвета для latency
  const getLatencyColor = (latency) => {
    switch (latency) {
      case 'Ultra': return 'text-green-500';
      case 'Low': return 'text-blue-500';
      case 'Medium': return 'text-yellow-500';
      case 'High': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  // Получение цвета для cost
  const getCostColor = (cost) => {
    switch (cost) {
      case 'Free': return 'text-green-500';
      case 'Low': return 'text-blue-500';
      case 'Medium': return 'text-yellow-500';
      case 'High': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F14] text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold mb-2">Model Infrastructure</h1>
          <p className="text-gray-400">Manage providers, routing, and active models via LiteLLM</p>
        </div>

        {/* Quick Start Guide */}
        <Card className="bg-[#111827] border border-[#1F2937] mb-6">
          <CardHeader>
            <CardTitle>Quick Start Guide</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {quickStartSteps.map((step) => (
                <div key={step.step} className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-[#6366F1] flex items-center justify-center flex-shrink-0">
                    {step.step}
                  </div>
                  <div>
                    <h4 className="font-medium mb-1">{step.title}</h4>
                    <p className="text-sm text-gray-400">{step.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card className="bg-[#111827] border border-[#1F2937]">
            <CardContent className="p-4">
              <p className="text-xs text-gray-400">Connected</p>
              <p className="text-2xl font-bold text-white">{connectedCount}</p>
            </CardContent>
          </Card>
          <Card className="bg-[#111827] border border-[#1F2937]">
            <CardContent className="p-4">
              <p className="text-xs text-gray-400">Available</p>
              <p className="text-2xl font-bold text-white">{allProviders.length - connectedCount}</p>
            </CardContent>
          </Card>
          <Card className="bg-[#111827] border border-[#1F2937]">
            <CardContent className="p-4">
              <p className="text-xs text-gray-400">Total Providers</p>
              <p className="text-2xl font-bold text-white">{allProviders.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-[#111827] border border-[#1F2937]">
            <CardContent className="p-4">
              <p className="text-xs text-gray-400">Active Model</p>
              <p className="text-lg font-bold text-green-500">
                {activeModel ? (allProviders.find(p => p.id === activeModel.provider)?.name || 'Custom') : 'None'}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Auth Types */}
        <Card className="bg-[#111827] border border-[#1F2937] mb-6">
          <CardHeader>
            <CardTitle>Supported Authentication Types</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              {authTypes.map((auth) => (
                <div key={auth.type} className="flex items-center gap-2">
                  <span className={`text-sm ${auth.color}`}>{auth.type}:</span>
                  <span className="text-sm text-gray-400">{auth.example}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Refresh All Button */}
        <div className="flex justify-between items-center mb-6">
          <p className="text-sm text-gray-400">
            Кэш моделей хранится 24 часа. Нажмите для принудительного обновления.
          </p>
          <Button
            onClick={() => {
              clearAllCache();
              setCacheStatus({ status: 'none', message: 'Кэш очищен' });
              alert('Кэш моделей очищен! Списки обновятся при следующем открытии.');
            }}
            variant="outline"
            className="flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Обновить все модели
          </Button>
        </div>

        {/* Filters & Search */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="flex gap-2">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 rounded-lg text-sm ${
                filter === 'all' ? 'bg-[#6366F1] text-white' : 'bg-[#1F2937] text-gray-400 hover:text-white'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilter('connected')}
              className={`px-4 py-2 rounded-lg text-sm ${
                filter === 'connected' ? 'bg-[#6366F1] text-white' : 'bg-[#1F2937] text-gray-400 hover:text-white'
              }`}
            >
              Connected
            </button>
            <button
              onClick={() => setFilter('available')}
              className={`px-4 py-2 rounded-lg text-sm ${
                filter === 'available' ? 'bg-[#6366F1] text-white' : 'bg-[#1F2937] text-gray-400 hover:text-white'
              }`}
            >
              Available
            </button>
          </div>
          <input
            type="text"
            placeholder="Search providers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-4 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-[#6366F1]"
          />
        </div>

        {/* Providers Table - Two Columns */}
        <Card className="bg-[#111827] border border-[#1F2937]">
          <CardHeader>
            <CardTitle>Providers ({filteredProviders.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center text-gray-500 py-8">Loading...</div>
            ) : filteredProviders.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No providers found</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredProviders.map((provider) => {
                  const status = getProviderStatus(provider.id);
                  const providerKey = keys.find(k => k.provider === provider.id);

                  return (
                    <div key={provider.id} className="flex items-center justify-between p-4 bg-[#1F2937] rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{provider.icon}</span>
                        <div>
                          <h4 className="font-medium">{provider.name}</h4>
                          <div className="flex items-center gap-2 text-xs text-gray-400">
                            <span>{provider.models} models</span>
                            <span>•</span>
                            <span className={getLatencyColor(provider.latency)}>{provider.latency}</span>
                            <span>•</span>
                            <span className={getCostColor(provider.cost)}>{provider.cost}</span>
                            <span>•</span>
                            <span>{provider.type}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-2 py-1 rounded ${status.badge}`}>
                          {status.status}
                        </span>
                        {status.status === 'Available' ? (
                          <Button size="sm" onClick={() => handleConnect(provider)}>
                            Connect
                          </Button>
                        ) : (
                          <div className="flex gap-1">
                            {status.status === 'Connected' && (
                              <Button size="sm" variant="outline" onClick={() => handleSetDefault(providerKey?.id)}>
                                Default
                              </Button>
                            )}
                            <Button size="sm" variant="outline" onClick={() => handleEdit(providerKey)}>
                              Manage
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => handleDelete(providerKey?.id)}>
                              ×
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Edit Key Form Modal */}
        {showEditForm && editingKey && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <Card className="bg-[#111827] border border-[#1F2937] w-full max-w-md mx-4">
              <CardHeader>
                <CardTitle>Edit {allProviders.find(p => p.id === editingKey.provider)?.name || editingKey.provider}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Current Model</label>
                    <p className="text-white text-sm">{editingKey.model_preference}</p>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="block text-sm text-gray-400">New Model</label>
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        cacheStatus.status === 'fresh' ? 'bg-green-500/10 text-green-500' :
                        cacheStatus.status === 'stale' ? 'bg-yellow-500/10 text-yellow-500' :
                        'bg-gray-500/10 text-gray-500'
                      }`}>
                        {isRefreshing ? 'Обновление...' : cacheStatus.message}
                      </span>
                    </div>
                    {showManualInput ? (
                      <div>
                        <input
                          type="text"
                          value={editModel}
                          onChange={(e) => setEditModel(e.target.value)}
                          className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white text-sm font-mono"
                          placeholder="Enter model name"
                        />
                        <button
                          type="button"
                          onClick={() => setShowManualInput(false)}
                          className="text-xs text-[#6366F1] mt-1 hover:underline"
                        >
                          ← Choose from list
                        </button>
                      </div>
                    ) : (
                      <div>
                        <select
                          value={editModel}
                          onChange={(e) => setEditModel(e.target.value)}
                          className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white text-sm"
                        >
                          {providerModels.length > 0 ? (
                            providerModels.map(m => (
                              <option key={m.id} value={m.id}>
                                {m.name}
                                {m.cost === 'free' ? ' (FREE)' : ''}
                              </option>
                            ))
                          ) : (
                            litellmProviders.find(p => p.id === editingKey.provider)?.models.map(m => (
                              <option key={m} value={m}>{m}</option>
                            ))
                          )}
                        </select>
                        <button
                          type="button"
                          onClick={() => setShowManualInput(true)}
                          className="text-xs text-gray-500 mt-1 hover:text-[#6366F1] hover:underline"
                        >
                          Enter custom model →
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <Button onClick={handleSaveEdit} className="flex-1">Save</Button>
                    <Button variant="outline" onClick={() => { setShowEditForm(false); setEditingKey(null); }}>
                      Cancel
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Add Key Form Modal */}
        {showAddForm && selectedProvider && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <Card className="bg-[#111827] border border-[#1F2937] w-full max-w-md mx-4">
              <CardHeader>
                <CardTitle>Connect {selectedProvider.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={(e) => {
                  e.preventDefault();
                  const formData = new FormData(e.target);

                  if (selectedProvider.id === 'gigachat') {
                    handleAddKey({
                      provider: 'gigachat',
                      api_key: `${formData.get('clientId')}:${formData.get('clientSecret')}`,
                      name: formData.get('name') || 'GigaChat',
                      model_preference: formData.get('model') || 'GigaChat',
                      is_default: formData.get('isDefault') === 'on',
                    });
                  } else if (selectedProvider.id === 'ollama') {
                    handleAddKey({
                      provider: 'ollama',
                      api_key: formData.get('ollamaUrl') || 'http://localhost:11434',
                      name: formData.get('name') || 'Ollama Local',
                      model_preference: formData.get('model'),
                      is_default: formData.get('isDefault') === 'on',
                    });
                  } else {
                    handleAddKey({
                      provider: selectedProvider.id,
                      api_key: formData.get('apiKey'),
                      name: formData.get('name') || selectedProvider.name,
                      model_preference: showManualInput ? manualModel : formData.get('model'),
                      is_default: formData.get('isDefault') === 'on',
                    });
                  }
                }} className="space-y-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Name</label>
                    <input name="name" type="text" className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white text-sm" placeholder="Work Key" />
                  </div>

                  {selectedProvider.id === 'gigachat' ? (
                    <>
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">Client ID</label>
                        <input name="clientId" type="text" required className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white text-sm font-mono" />
                      </div>
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">Client Secret</label>
                        <input name="clientSecret" type="password" required className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white text-sm font-mono" />
                      </div>
                    </>
                  ) : selectedProvider.id === 'ollama' ? (
                    <>
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">Server URL</label>
                        <input name="ollamaUrl" type="text" className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white text-sm font-mono" placeholder="http://localhost:11434" />
                      </div>
                    </>
                  ) : (
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">API Key</label>
                      <input name="apiKey" type="password" required className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white text-sm font-mono" />
                    </div>
                  )}

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="block text-sm text-gray-400">Model</label>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          cacheStatus.status === 'fresh' ? 'bg-green-500/10 text-green-500' :
                          cacheStatus.status === 'stale' ? 'bg-yellow-500/10 text-yellow-500' :
                          'bg-gray-500/10 text-gray-500'
                        }`}>
                          {isRefreshing ? 'Обновление...' : cacheStatus.message}
                        </span>
                        <button
                          type="button"
                          onClick={handleRefreshModels}
                          disabled={isRefreshing}
                          className={`p-1 rounded hover:bg-[#374151] transition-colors ${
                            isRefreshing ? 'animate-spin' : ''
                          }`}
                          title="Обновить список моделей"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                          </svg>
                        </button>
                      </div>
                    </div>
                    {modelsLoading ? (
                      <div className="text-sm text-gray-500 py-2">Loading models...</div>
                    ) : showManualInput ? (
                      <div>
                        <input
                          type="text"
                          value={manualModel}
                          onChange={(e) => setManualModel(e.target.value)}
                          className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white text-sm font-mono"
                          placeholder="Enter model name (e.g., gpt-4-turbo)"
                        />
                        <button
                          type="button"
                          onClick={() => setShowManualInput(false)}
                          className="text-xs text-[#6366F1] mt-1 hover:underline"
                        >
                          ← Choose from list
                        </button>
                      </div>
                    ) : (
                      <div>
                        <select name="model" className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white text-sm">
                          {providerModels.length > 0 ? (
                            providerModels.map(m => (
                              <option key={m.id} value={m.id}>
                                {m.name}
                                {m.cost === 'free' ? ' (FREE)' : ''}
                                {m.max_tokens ? ` - ${Math.round(m.max_tokens / 1000)}K tokens` : ''}
                              </option>
                            ))
                          ) : (
                            selectedProvider.models.map(m => <option key={m} value={m}>{m}</option>)
                          )}
                        </select>
                        <button
                          type="button"
                          onClick={() => setShowManualInput(true)}
                          className="text-xs text-gray-500 mt-1 hover:text-[#6366F1] hover:underline"
                        >
                          Enter custom model →
                        </button>
                      </div>
                    )}
                  </div>

                  <label className="flex items-center gap-2 text-sm text-gray-400">
                    <input name="isDefault" type="checkbox" defaultChecked className="rounded bg-[#1F2937] border-[#374151]" />
                    Set as default
                  </label>

                  <div className="flex gap-2">
                    <Button type="submit" className="flex-1">Connect</Button>
                    <Button type="button" variant="outline" onClick={() => { setShowAddForm(false); setSelectedProvider(null); }}>
                      Cancel
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}