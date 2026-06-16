import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';
import { ProviderTester } from './ProviderTester';

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

export function ProviderManagement() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [expandedKey, setExpandedKey] = useState(null);

  const fetchKeys = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/keys', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setKeys(data);
      }
    } catch (err) {
      console.error('Failed to fetch keys:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleDelete = async (keyId) => {
    if (!confirm('Удалить этот API ключ?')) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/keys/${keyId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        setKeys(prev => prev.filter(k => k.id !== keyId));
      }
    } catch (err) {
      console.error('Failed to delete key:', err);
    }
  };

  const handleSetDefault = async (keyId) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/keys/${keyId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ is_default: true }),
      });

      if (response.ok) {
        fetchKeys();
      }
    } catch (err) {
      console.error('Failed to set default:', err);
    }
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
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>🔑 Управление провайдерами</CardTitle>
        <Button size="sm" onClick={() => setShowAddForm(!showAddForm)}>
          {showAddForm ? 'Отмена' : '+ Добавить'}
        </Button>
      </CardHeader>
      <CardContent>
        {showAddForm && (
          <div className="mb-6">
            <p className="text-sm text-text-secondary mb-4">
              Выберите провайдера для добавления API ключа:
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { id: 'google', name: 'Google' },
                { id: 'groq', name: 'Groq' },
                { id: 'openai', name: 'OpenAI' },
                { id: 'anthropic', name: 'Anthropic' },
              ].map(provider => (
                <button
                  key={provider.id}
                  onClick={() => setSelectedProvider({ id: provider.id, name: provider.name })}
                  className={`p-3 rounded-lg border text-center transition-all ${
                    selectedProvider?.id === provider.id
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:border-primary/50'
                  }`}
                >
                  <span className="text-2xl">{providerIcons[provider.id]}</span>
                  <div className="text-sm mt-1">{provider.name}</div>
                </button>
              ))}
            </div>
            
            {selectedProvider && (
              <div className="mt-4">
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const formData = new FormData(e.target);
                    const token = localStorage.getItem('access_token');
                    
                    const response = await fetch('/api/v1/keys', {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`,
                      },
                      body: JSON.stringify({
                        provider: selectedProvider.id,
                        api_key: formData.get('apiKey'),
                        name: formData.get('name') || `${selectedProvider.name} Key`,
                        model_preference: formData.get('model') || 'auto',
                        is_default: formData.get('isDefault') === 'on',
                      }),
                    });

                    if (!response.ok) {
                      try {
                        const errorData = await response.json();
                        alert(errorData.detail || 'Ошибка при сохранении ключа');
                      } catch {
                        alert('Ошибка при сохранении ключа');
                      }
                    } else {
                      fetchKeys();
                      setShowAddForm(false);
                      setSelectedProvider(null);
                    }
                  }}
                  className="space-y-4"
                >
                  <div>
                    <label className="block text-sm text-text-secondary mb-1">Название</label>
                    <input
                      name="name"
                      type="text"
                      className="w-full px-3 py-2 bg-gray-800 border border-border rounded-lg text-text-primary text-sm"
                      placeholder="Рабочий ключ"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-text-secondary mb-1">API ключ</label>
                    <input
                      name="apiKey"
                      type="password"
                      required
                      className="w-full px-3 py-2 bg-gray-800 border border-border rounded-lg text-text-primary text-sm font-mono"
                      placeholder="sk-..."
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-text-secondary mb-1">Модель</label>
                    <input
                      name="model"
                      type="text"
                      className="w-full px-3 py-2 bg-gray-800 border border-border rounded-lg text-text-primary text-sm"
                      placeholder="auto"
                    />
                  </div>
                  <label className="flex items-center gap-2 text-sm text-text-secondary">
                    <input name="isDefault" type="checkbox" className="rounded" />
                    Использовать по умолчанию
                  </label>
                  <Button type="submit">Сохранить</Button>
                </form>
              </div>
            )}
          </div>
        )}

        {/* Список ключей */}
        <div className="space-y-3">
          {keys.length === 0 ? (
            <div className="text-center text-text-muted py-8">
              <div className="text-4xl mb-2">🔑</div>
              <div className="text-sm">Нет подключенных провайдеров</div>
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={() => setShowAddForm(true)}
              >
                Добавить провайдера
              </Button>
            </div>
          ) : (
            keys.map(key => (
              <div
                key={key.id}
                className="border border-border rounded-xl overflow-hidden"
              >
                <div
                  className="p-4 flex items-center justify-between cursor-pointer hover:bg-gray-800/50"
                  onClick={() => setExpandedKey(expandedKey === key.id ? null : key.id)}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{providerIcons[key.provider] || '🔗'}</span>
                    <div>
                      <div className="font-medium text-text-primary">{key.name || key.provider_display_name}</div>
                      <div className="text-xs text-text-secondary">
                        {key.provider_display_name} • {key.model_preference || 'Auto'}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {key.is_default && (
                      <span className="text-xs text-primary px-2 py-1 bg-primary/10 rounded">
                        По умолчанию
                      </span>
                    )}
                    <span className="text-xs text-text-muted">
                      {new Date(key.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                {expandedKey === key.id && (
                  <div className="px-4 pb-4 border-t border-border pt-4 space-y-3">
                    <ProviderTester
                      keyId={key.id}
                      provider={key.provider_display_name}
                      model={key.model_preference}
                    />
                    <div className="flex gap-2">
                      {!key.is_default && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleSetDefault(key.id)}
                        >
                          Сделать основным
                        </Button>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDelete(key.id)}
                        className="text-red-500 hover:text-red-600"
                      >
                        Удалить
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default ProviderManagement;