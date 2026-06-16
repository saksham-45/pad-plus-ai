import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from './ui/Card';
import { Button } from './ui/Button';
import { apiFetch } from '../services/api';

// Fallback модели по провайдерам (только 2 основных)
const fallbackModelSuggestions = {
  openrouter: ['meta-llama/llama-3.1-8b-instruct:free', 'microsoft/phi-3-mini-4k-instruct:free', 'openrouter/auto'],
  gigachat: ['GigaChat', 'GigaChat-Pro', 'GigaChat-Plus'],
};

export function ApiKeyForm({ provider, onSuccess, onCancel }) {
  const [name, setName] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [modelPreference, setModelPreference] = useState('auto');
  const [isDefault, setIsDefault] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [availableModels, setAvailableModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(false);

  // Загрузка моделей провайдера при монтировании
  useEffect(() => {
    if (provider?.id) {
      loadModels(provider.id);
    }
  }, [provider?.id]);

  const loadModels = async (providerId, forceRefresh = false) => {
    setModelsLoading(true);
    try {
      const url = forceRefresh
        ? `/api/v1/providers/${providerId}/models?refresh=true`
        : `/api/v1/providers/${providerId}/models`;
      const response = await apiFetch(url);
      if (response.ok) {
        const data = await response.json();
        const models = data.models || [];
        setAvailableModels(models);
      } else {
        // Fallback на статические модели
        const fallback = fallbackModelSuggestions[providerId] || [];
        setAvailableModels(fallback.map(m => ({ 
          id: m.includes('/') ? m : `${providerId}/${m}`, 
          name: m 
        })));
      }
    } catch (error) {
      console.error('Failed to load models:', error);
      const fallback = fallbackModelSuggestions[providerId] || [];
      setAvailableModels(fallback.map(m => ({ 
        id: m.includes('/') ? m : `${providerId}/${m}`, 
        name: m 
      })));
    } finally {
      setModelsLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await apiFetch('/api/v1/keys', {
        method: 'POST',
        body: JSON.stringify({
          provider: provider.id,
          api_key: apiKey,
          name: name || `${provider.name} Key`,
          model_preference: modelPreference,
          is_default: isDefault,
        }),
      });

      if (!response.ok) {
        let errorMessage = 'Ошибка сохранения ключa';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage;
        } catch {
          // Пустой ответ от сервера
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();

      if (onSuccess) onSuccess(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <span className="text-xl mr-2">
            {provider ? '🔵⚡🟢🟠'[['google','groq','openai','anthropic'].indexOf(provider.id)] || '🔗' : '🔗'}
          </span>
          Добавить API ключ: {provider?.name}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-text-secondary mb-1">
              Название (опционально)
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Рабочий ключ"
            />
          </div>

          <div>
            <label className="block text-sm text-text-secondary mb-1">
              API ключ *
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono"
              placeholder="sk-..."
              required
            />
            <p className="text-xs text-text-muted mt-1">
              Ключ будет зашифрован перед сохранением
            </p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm text-text-secondary">
                Модель по умолчанию
                {modelsLoading && <span className="ml-2 text-xs text-text-muted">(загрузка...)</span>}
              </label>
              <button
                type="button"
                onClick={() => loadModels(provider.id, true)}
                disabled={modelsLoading}
                className="text-xs text-primary hover:text-primary/80 disabled:opacity-50"
              >
                🔄 Обновить список
              </button>
            </div>
            <select
              value={modelPreference}
              onChange={(e) => setModelPreference(e.target.value)}
              disabled={modelsLoading}
              className="w-full px-3 py-2 bg-gray-800 border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
            >
              <option value="auto">Автоматически</option>
              {availableModels.map((model) => (
                <option key={model.id} value={model.id}>{model.name}</option>
              ))}
              <option value="custom">Другая (вручную)...</option>
            </select>
          </div>

          {modelPreference === 'custom' && (
            <div>
              <label className="block text-sm text-text-secondary mb-1">
                Укажите модель
              </label>
              <input
                type="text"
                onChange={(e) => setModelPreference(e.target.value)}
                className="w-full px-3 py-2 bg-gray-800 border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="provider/model-name"
              />
            </div>
          )}

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="isDefault"
              checked={isDefault}
              onChange={(e) => setIsDefault(e.target.checked)}
              className="w-4 h-4 rounded border-border bg-gray-800 text-primary focus:ring-primary/50"
            />
            <label htmlFor="isDefault" className="text-sm text-text-secondary">
              Использовать по умолчанию
            </label>
          </div>

          {error && (
            <div className="text-red-500 text-sm bg-red-500/10 p-3 rounded-lg">
              {error}
            </div>
          )}

          <div className="flex gap-2">
            <Button type="submit" loading={loading} className="flex-1">
              Сохранить
            </Button>
            {onCancel && (
              <Button type="button" variant="outline" onClick={onCancel}>
                Отмена
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

export default ApiKeyForm;