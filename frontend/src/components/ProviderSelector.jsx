import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';
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
};

export function ProviderSelector({ onSelect, selectedProvider }) {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const response = await apiFetch('/api/v1/providers');
        if (!response.ok) throw new Error('Failed to fetch providers');
        const data = await response.json();
        setProviders(data);
      } catch (err) {
        setError(err.message);
        // Fallback providers (актуальный список - только 2 основных)
        setProviders([
          { id: 'openrouter', name: 'OpenRouter', description: '100+ моделей через единый API', free_models: ['meta-llama/llama-3.1-8b-instruct:free'], is_premium: true },
          { id: 'gigachat', name: 'GigaChat', description: 'Модели GigaChat от Сбера', free_models: ['GigaChat', 'GigaChat-Pro'], is_premium: false },
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchProviders();
  }, []);

  const handleSelect = (provider) => {
    if (onSelect) onSelect(provider);
  };

  if (loading) {
    return (
      <Card>
        <CardContent>
          <div className="text-center text-text-muted py-4">Загрузка...</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Выберите провайдера</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {providers.map((provider) => (
            <button
              key={provider.id}
              onClick={() => handleSelect(provider)}
              className={`p-4 rounded-xl border text-left transition-all ${
                selectedProvider?.id === provider.id
                  ? 'border-primary bg-primary/10'
                  : 'border-border hover:border-primary/50 hover:bg-gray-800/50'
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">{providerIcons[provider.id] || '🔗'}</span>
                <div>
                  <div className="font-medium text-text-primary">{provider.name}</div>
                  <div className="text-xs text-text-secondary">{provider.description}</div>
                </div>
              </div>
              {provider.free_models.length > 0 && (
                <div className="text-xs text-green-500 mt-2">
                  ✓ Бесплатные модели: {provider.free_models.join(', ')}
                </div>
              )}
              {provider.is_premium && (
                <div className="text-xs text-yellow-500 mt-2">
                  ⭐ Premium
                </div>
              )}
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default ProviderSelector;