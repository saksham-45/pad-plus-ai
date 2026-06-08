import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';
import { ProviderTester } from './ProviderTester';
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

// Время кэширования статусов ключей (5 минут)
const KEY_STATUS_CACHE_TTL = 5 * 60 * 1000;
// Key для localStorage
const KEY_STATUS_STORAGE_KEY = 'padplus_key_statuses';

export function ProviderManagement() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [expandedKey, setExpandedKey] = useState(null);
  const [keyStatuses, setKeyStatuses] = useState({}); // { keyId: { status, message, last_checked } }
  const [testingKeys, setTestingKeys] = useState({});
  const [lastStatusFetch, setLastStatusFetch] = useState(null);
  const [useLocalStorageCache, setUseLocalStorageCache] = useState(false);

  // Загрузка кэша из localStorage при монтировании
  useEffect(() => {
    try {
      const cached = localStorage.getItem(KEY_STATUS_STORAGE_KEY);
      if (cached) {
        const { statuses, timestamp } = JSON.parse(cached);
        const age = Date.now() - timestamp;
        
        if (age < KEY_STATUS_CACHE_TTL) {
          console.log('📦 Loading key statuses from localStorage');
          setKeyStatuses(statuses);
          setLastStatusFetch(timestamp);
          setUseLocalStorageCache(true);
        } else {
          console.log('⚠️ localStorage cache expired, fetching fresh data');
        }
      }
    } catch (err) {
      console.error('Failed to load key statuses from localStorage:', err);
    }
  }, []);

  // Сохранение кэша в localStorage при изменении
  useEffect(() => {
    if (Object.keys(keyStatuses).length > 0) {
      try {
        const cacheData = {
          statuses: keyStatuses,
          timestamp: Date.now()
        };
        localStorage.setItem(KEY_STATUS_STORAGE_KEY, JSON.stringify(cacheData));
        console.log('💾 Key statuses saved to localStorage');
      } catch (err) {
        console.error('Failed to save key statuses to localStorage:', err);
      }
    }
  }, [keyStatuses]);

  const fetchKeys = async () => {
    try {
      const response = await apiFetch('/api/v1/keys');
      
      if (response.ok) {
        const data = await response.json();
        setKeys(data);
        autoCheckAllKeys(data);
        return data;
      }
    } catch (err) {
      console.error('Failed to fetch keys:', err);
    } finally {
      setLoading(false);
    }
  };

  // Авто-проверка статуса всех ключей с использованием кэша
  const autoCheckAllKeys = async (keysData) => {
    // Проверяем, есть ли свежий кэш в localStorage
    const now = Date.now();
    if (lastStatusFetch && (now - lastStatusFetch) < KEY_STATUS_CACHE_TTL) {
      console.log('📦 Using localStorage cached key statuses');
      return; // Используем кэш
    }

    // Проверяем, есть ли свежий кэш на backend
    try {
      const response = await apiFetch('/api/v1/keys/status/batch');
      if (response.ok) {
        const data = await response.json();
        
        // Сохраняем статусы
        const statuses = {};
        data.keys.forEach(keyStatus => {
          statuses[keyStatus.key_id] = {
            status: keyStatus.status,
            message: keyStatus.message,
            last_checked: keyStatus.last_checked,
            cached: keyStatus.cached || false
          };
        });
        
        setKeyStatuses(statuses);
        setLastStatusFetch(now);
        setUseLocalStorageCache(false);
      }
    } catch (err) {
      console.error('Failed to fetch batch key status:', err);
      // Fallback: проверяем каждый ключ индивидуально
      for (const key of keysData) {
        if (key.id && key.id !== 'system-gigachat') {
          await checkSingleKeyStatus(key.id);
        }
      }
    }
  };

  const checkSingleKeyStatus = async (keyId) => {
    setKeyStatuses(prev => ({ ...prev, [keyId]: { status: 'checking', message: 'Проверка...', last_checked: new Date().toISOString() } }));
    try {
      const response = await apiFetch(`/api/v1/keys/${keyId}/test`, {
        method: 'POST',
      });
      const data = await response.json();
      setKeyStatuses(prev => ({ 
        ...prev, 
        [keyId]: { 
          status: data.success ? 'success' : 'error',
          message: data.message,
          last_checked: new Date().toISOString()
        }
      }));
    } catch (err) {
      setKeyStatuses(prev => ({ 
        ...prev, 
        [keyId]: { 
          status: 'error',
          message: err.message || 'Ошибка проверки',
          last_checked: new Date().toISOString()
        }
      }));
    }
  };

  // Обновление статуса одного ключа (сброс кэша)
  const refreshKeyStatus = async (keyId) => {
    setKeyStatuses(prev => ({ ...prev, [keyId]: { status: 'checking', message: 'Обновление...', last_checked: new Date().toISOString() } }));
    try {
      const response = await apiFetch(`/api/v1/keys/status/${keyId}/refresh`, {
        method: 'POST',
      });
      const data = await response.json();
      setKeyStatuses(prev => ({ 
        ...prev, 
        [keyId]: { 
          status: data.status,
          message: data.message,
          last_checked: data.last_checked
        }
      }));
      // Сбрасываем кэш — очищаем localStorage и принудительно обновим при следующей загрузке
      localStorage.removeItem(KEY_STATUS_STORAGE_KEY);
      setLastStatusFetch(null);
    } catch (err) {
      setKeyStatuses(prev => ({ 
        ...prev, 
        [keyId]: { 
          status: 'error',
          message: err.message || 'Ошибка обновления',
          last_checked: new Date().toISOString()
        }
      }));
    }
  };

  // Иконка статуса для ключа
  const getKeyStatusIcon = (keyId) => {
    const statusData = keyStatuses[keyId];
    if (!statusData) return null;
    if (keyId === 'system-gigachat') return null; // Системный ключ не проверяем
    
    const status = statusData.status;
    let iconConfig;
    switch (status) {
      case 'checking':
        iconConfig = { icon: '🔄', color: 'text-yellow-500', bg: 'bg-yellow-500/10' };
        break;
      case 'success':
        iconConfig = { icon: '🟢', color: 'text-green-500', bg: 'bg-green-500/10' };
        break;
      case 'error':
        iconConfig = { icon: '🔴', color: 'text-red-500', bg: 'bg-red-500/10' };
        break;
      default:
        return null;
    }
    
    return { ...iconConfig, cached: statusData.cached, last_checked: statusData.last_checked };
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleDelete = async (keyId) => {
    if (!confirm('Удалить этот API ключ?')) return;

    try {
      const response = await apiFetch(`/api/v1/keys/${keyId}`, {
        method: 'DELETE',
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
      const response = await apiFetch(`/api/v1/keys/${keyId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_default: true }),
      });

      if (response.ok) {
        const updatedKeys = await fetchKeys();
        const defaultKey = updatedKeys?.find(k => k.id === keyId) || updatedKeys?.find(k => k.is_default);
        if (defaultKey) {
          window.dispatchEvent(new CustomEvent('model-changed', {
            detail: {
              id: defaultKey.model_preference || 'auto',
              name: defaultKey.model_preference === 'auto'
                ? `${defaultKey.provider_display_name} (Auto)`
                : defaultKey.model_preference,
              keyId: defaultKey.id,
              provider: defaultKey.provider,
              providerName: defaultKey.provider_display_name,
              isDefault: true,
            }
          }));
        }
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
            <div className="grid grid-cols-2 gap-3">
              {[
                { id: 'openrouter', name: 'OpenRouter', icon: '🌐' },
                { id: 'gigachat', name: 'GigaChat', icon: '🇷🇺' },
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
                  <span className="text-2xl">{provider.icon}</span>
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
                    
                    const response = await apiFetch('/api/v1/keys', {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json',
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

        {/* Индикатор устаревших данных */}
        {keys.length > 0 && lastStatusFetch && (Date.now() - lastStatusFetch) >= KEY_STATUS_CACHE_TTL && (
          <div className="mb-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-blue-500">
                <span className="text-lg">🕐</span>
                <span className="text-sm font-medium">Статусы ключей устарели (более 5 минут)</span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  setLastStatusFetch(null);
                  await autoCheckAllKeys(keys);
                }}
                className="text-xs px-3 py-1"
              >
                Обновить сейчас
              </Button>
            </div>
            <div className="text-xs text-text-secondary mt-1 ml-6">
              Статусы будут обновлены автоматически при следующем открытии страницы
            </div>
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
                      {/* Статус-индикатор ключа */}
                      {(() => {
                        const status = getKeyStatusIcon(key.id);
                        if (status) {
                          return (
                            <span className={`flex items-center gap-1 text-xs px-2 py-1 rounded ${status.color} ${status.bg} relative group cursor-help`}>
                              <span>{status.icon}</span>
                              {status.cached && (
                                <span title="Из кэша" className="text-blue-400">⚡</span>
                              )}
                              {/* Tooltip с подробностями */}
                              {keyStatuses[key.id]?.message && (
                                <span className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 hidden group-hover:block bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                                  {keyStatuses[key.id].message}
                                  {keyStatuses[key.id]?.last_checked && (
                                    <div className="text-xs opacity-70 mt-1">
                                      {new Date(keyStatuses[key.id].last_checked).toLocaleString()}
                                    </div>
                                  )}
                                </span>
                              )}
                            </span>
                          );
                        }
                        if (key.id === 'system-gigachat') {
                          return (
                            <span className="text-xs text-blue-500 px-2 py-1 bg-blue-500/10 rounded">
                              Системный
                            </span>
                          );
                        }
                        return null;
                      })()}
                      {/* Кнопка обновления статуса */}
                      {key.id !== 'system-gigachat' && (
                        <Button
                          variant="ghost"
                          size="xs"
                          onClick={(e) => {
                            e.stopPropagation();
                            refreshKeyStatus(key.id);
                          }}
                          className="text-xs px-2 py-1 opacity-50 hover:opacity-100"
                          title="Обновить статус"
                        >
                          ↻
                        </Button>
                      )}
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