import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from './ui/Card';
import { Button } from './ui/Button';

const modelSuggestions = {
  google: ['gemini-2.0-flash', 'gemini-1.5-pro'],
  groq: ['llama-3.1-70b-versatile', 'mixtral-8x7b-32768'],
  openai: ['gpt-4', 'gpt-3.5-turbo'],
  anthropic: ['claude-3-sonnet', 'claude-3-haiku'],
  openrouter: ['openai/gpt-3.5-turbo', 'google/gemini-2.0-flash'],
};

export function ApiKeyForm({ provider, onSuccess, onCancel }) {
  const [name, setName] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [modelPreference, setModelPreference] = useState('auto');
  const [isDefault, setIsDefault] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
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
            <label className="block text-sm text-text-secondary mb-1">
              Модель по умолчанию
            </label>
            <select
              value={modelPreference}
              onChange={(e) => setModelPreference(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              <option value="auto">Автоматически</option>
              {modelSuggestions[provider?.id]?.map((model) => (
                <option key={model} value={model}>{model}</option>
              ))}
              <option value="custom">Другая...</option>
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
                placeholder="model-name"
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