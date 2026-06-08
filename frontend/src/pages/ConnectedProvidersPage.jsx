import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { apiFetch } from '../services/api';

// Все доступные провайдеры (только 2 основных)
const allProviders = [
  { id: 'openrouter', name: 'OpenRouter', icon: '🌐' },
  { id: 'gigachat', name: 'GigaChat', icon: '🇷🇺' },
];

export default function ConnectedProvidersPage() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editingKey, setEditingKey] = useState(null);
  const [editModel, setEditModel] = useState('');

  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    console.log('🔄 ConnectedProvidersPage.fetchKeys() called');
    try {
      const response = await apiFetch('/api/v1/keys?offset=0&limit=100');
      console.log('🔄 fetchKeys response status:', response.status);

      if (response.ok) {
        const result = await response.json();
        console.log('🔄 fetchKeys result:', result);
        const keysData = result.data || result;
        const arr = Array.isArray(keysData) ? keysData : [];
        console.log('🔄 fetchKeys keys count:', arr.length);
        setKeys(arr);
        return arr;
      } else {
        console.warn('🔄 fetchKeys failed:', response.status);
      }
    } catch (error) {
      console.error('🔄 Failed to fetch keys:', error);
      setKeys([]);
    } finally {
      setLoading(false);
    }
    return [];
  };

  // Получение информации о провайдере
  const getProviderInfo = (providerId) => {
    return allProviders.find(p => p.id === providerId) || { 
      name: providerId, 
      icon: '🔑' 
    };
  };

  // Обработчик открытия формы редактирования
  const handleEdit = (key) => {
    setEditingKey(key);
    setEditModel(key.model_preference);
    setShowEditForm(true);
    // Загружаем модели для этого провайдера
    loadModels(key.provider);
  };

  // Загрузка моделей для провайдера
  const [availableModels, setAvailableModels] = useState([]);

  const loadModels = async (providerId) => {
    try {
      const response = await apiFetch(`/api/v1/providers/${providerId}/models`);
      if (response.ok) {
        const data = await response.json();
        setAvailableModels(data.models || []);
      }
    } catch (error) {
      console.error('Failed to load models:', error);
      setAvailableModels([]);
    }
  };

  // Обработчик сохранения изменений
  const handleSaveEdit = async () => {
    if (!editingKey) return;

    try {
      console.log('💾 Saving model:', editModel, 'for key:', editingKey.id);
      
      const response = await apiFetch(`/api/v1/keys/${editingKey.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_preference: editModel,
        }),
      });

      const responseData = await response.json().catch(() => null);
      console.log('📡 Response:', response.status, responseData);

      if (response.ok) {
        await fetchKeys();
        setShowEditForm(false);
        setEditingKey(null);
        window.dispatchEvent(new CustomEvent('keys-updated'));
        alert('Модель успешно обновлена!');
      } else {
        const errorMsg = responseData?.detail || responseData?.message || 'Ошибка при сохранении';
        console.error('❌ Save failed:', errorMsg);
        alert(`Ошибка: ${errorMsg}`);
      }
    } catch (error) {
      console.error('Failed to update key:', error);
      alert('Ошибка при обновлении модели: ' + error.message);
    }
  };

  // Обработчик удаления ключа
  const handleDelete = async (keyId) => {
    if (!confirm('Удалить этот API ключ?')) return;
    
    try {
      const response = await apiFetch(`/api/v1/keys/${keyId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        fetchKeys();
        // Отправляем событие для обновления в App.jsx
        window.dispatchEvent(new CustomEvent('keys-updated'));
      }
    } catch (error) {
      console.error('Failed to delete key:', error);
    }
  };

  // Обработчик установки по умолчанию
  const handleSetDefault = async (keyId) => {
    try {
      const response = await apiFetch(`/api/v1/keys/${keyId}/set-default`, {
        method: 'POST',
      });

      if (response.ok) {
        const freshKeys = await fetchKeys();
        const key = freshKeys?.find(k => k.id === keyId) || keys.find(k => k.id === keyId);
        if (key) {
          updateSelectedModel(key);
        }
        window.dispatchEvent(new CustomEvent('keys-updated'));
      }
    } catch (error) {
      console.error('Failed to set default key:', error);
    }
  };

  // Обновление выбранной модели
  const updateSelectedModel = (key) => {
    const modelInfo = {
      id: key.model_preference || 'auto',
      name: key.model_preference === 'auto'
        ? `${key.provider_display_name} (Auto)`
        : key.model_preference,
      keyId: key.id,
      provider: key.provider,
      providerName: key.provider_display_name,
      isDefault: key.is_default,
    };
    console.log('🔄 Switching model:', modelInfo);
    localStorage.setItem('selectedModel', JSON.stringify(modelInfo));
    window.dispatchEvent(new CustomEvent('model-changed', { detail: modelInfo }));
  };

  return (
    <div className="min-h-screen bg-[#0B0F14] text-white p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold mb-2">Подключенные провайдеры</h1>
          <p className="text-gray-400">Управляйте вашими подключенными провайдерами и API ключами</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <Card className="bg-[#111827] border border-[#1F2937]">
            <CardContent className="p-4">
              <p className="text-xs text-gray-400">Всего подключено</p>
              <p className="text-2xl font-bold text-white">{keys.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-[#111827] border border-[#1F2937]">
            <CardContent className="p-4">
              <p className="text-xs text-gray-400">Активный провайдер</p>
              <p className="text-lg font-bold text-green-500">
                {keys.find(k => k.is_default) 
                  ? getProviderInfo(keys.find(k => k.is_default).provider).name 
                  : 'Не выбран'}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Connected Providers List */}
        <Card className="bg-[#111827] border border-[#1F2937]">
          <CardHeader>
            <CardTitle>Ваши провайдеры</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center text-gray-500 py-8">Загрузка...</div>
            ) : keys.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <p className="mb-2">Нет подключенных провайдеров</p>
                <Button onClick={() => window.location.href = '/providers'}>
                  Подключить провайдера
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {(() => {
                  // Группируем ключи по провайдеру, берём первый (или default) для каждого провайдера
                  const groupedKeys = keys.reduce((acc, key) => {
                    if (!acc[key.provider] || key.is_default) {
                      acc[key.provider] = key;
                    }
                    return acc;
                  }, {});
                  const uniqueKeys = Object.values(groupedKeys);
                  
                  return uniqueKeys.map(key => {
                    const provider = getProviderInfo(key.provider);
                    
                    return (
                      <div 
                        key={key.id} 
                        className="flex items-center justify-between p-4 bg-[#1F2937] rounded-lg"
                      >
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 rounded-lg bg-[#6366F1] flex items-center justify-center text-2xl">
                            {provider.icon}
                          </div>
                          <div>
                            <h4 className="font-medium text-lg">{provider.name}</h4>
                            <div className="flex items-center gap-2 text-sm text-gray-400">
                              <span>Модель: {key.model_preference || 'Auto'}</span>
                              {key.is_default && (
                                <span className="text-xs text-green-500 bg-green-500/10 px-2 py-0.5 rounded">
                                  По умолчанию
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            onClick={() => updateSelectedModel(key)}
                            className={key.is_default ? 'bg-green-600 hover:bg-green-700' : ''}
                          >
                            {key.is_default ? '✓ Активен' : 'Использовать'}
                          </Button>
                          {!key.is_default && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleSetDefault(key.id)}
                            >
                              Сделать основным
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleEdit(key)}
                          >
                            Изменить модель
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleDelete(key.id)}
                          >
                            Удалить
                          </Button>
                        </div>
                      </div>
                    );
                  });
                })()}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Edit Modal */}
        {showEditForm && editingKey && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <Card className="bg-[#111827] border border-[#1F2937] w-full max-w-md mx-4">
              <CardHeader>
                <CardTitle>Изменить модель — {getProviderInfo(editingKey.provider).name}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Текущая модель</label>
                    <p className="text-white text-sm font-mono">{editingKey.model_preference}</p>
                  </div>

                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Модель</label>
                    <select
                      value={editModel}
                      onChange={(e) => setEditModel(e.target.value)}
                      className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white text-sm"
                    >
                      {availableModels.length > 0 ? (
                        <>
                          {availableModels.map(m => (
                            <option key={m.id} value={m.name}>{m.name}</option>
                          ))}
                          <option value="custom">✏️ Ввести вручную...</option>
                        </>
                      ) : (
                        <option value={editModel}>{editModel}</option>
                      )}
                    </select>
                    {editModel === 'custom' && (
                      <input
                        type="text"
                        onChange={(e) => setEditModel(e.target.value)}
                        className="w-full px-3 py-2 bg-[#1F2937] border border-[#374151] rounded-lg text-white text-sm font-mono mt-2"
                        placeholder="Введите название модели"
                      />
                    )}
                    <p className="text-xs text-gray-500 mt-1">
                      {availableModels.length} моделей доступно
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <Button onClick={handleSaveEdit} className="flex-1">Сохранить</Button>
                    <Button variant="outline" onClick={() => { setShowEditForm(false); setEditingKey(null); }}>
                      Отмена
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Quick Actions */}
        <div className="mt-6 flex gap-4">
          <Button onClick={() => window.location.href = '/providers'}>
            Подключить нового провайдера
          </Button>
          <Button variant="outline" onClick={() => window.location.href = '/'}>
            Вернуться на главную
          </Button>
        </div>
      </div>
    </div>
  );
}
