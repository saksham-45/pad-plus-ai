import React, { useState, useEffect } from 'react';
import './Settings.css';

const Settings = ({ onClose }) => {
  const [providers, setProviders] = useState({
    gigachat: { enabled: false, has_key: false },
    gemini: { enabled: false, has_key: false },
    openrouter: { enabled: false, has_key: false, model: 'google/gemma-7b-it' }
  });
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Получение session_id
  const getSessionId = () => {
    let sessionId = localStorage.getItem('session_id')
    if (!sessionId) {
      sessionId = 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now()
      localStorage.setItem('session_id', sessionId)
    }
    return sessionId
  };

  // Загрузка текущей конфигурации
  useEffect(() => {
    loadProviders();
  }, []);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const loadProviders = async () => {
    try {
      const sessionId = getSessionId()
      const response = await fetch(`${API_URL}/api/v1/llm/providers?session_id=${sessionId}`);
      if (response.ok) {
        const data = await response.json();
        setProviders(data.providers);
      }
    } catch (err) {
      console.error('Failed to load providers:', err);
    }
  };

  const loadModels = async (provider) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/llm/models?provider=${provider}`);
      if (response.ok) {
        const data = await response.json();
        setModels(data.models);
      }
    } catch (err) {
      console.error('Failed to load models:', err);
    }
  };

  const handleProviderToggle = (provider, enabled) => {
    setProviders(prev => ({
      ...prev,
      [provider]: { ...prev[provider], enabled }
    }));
  };

  const handleModelChange = (model) => {
    setProviders(prev => ({
      ...prev,
      openrouter: { ...prev.openrouter, model }
    }));
  };

  const handleApiKeyChange = (provider, key) => {
    setProviders(prev => ({
      ...prev,
      [provider]: { ...prev[provider], api_key: key }
    }));
  };

  const handleTestProvider = async (provider) => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const sessionId = getSessionId()
      const response = await fetch(`${API_URL}/api/v1/llm/test/${provider}?session_id=${sessionId}`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (data.status === 'success') {
        setSuccess(`Провайдер ${provider} работает корректно`);
      } else {
        setError(`Ошибка тестирования ${provider}: ${data.error || 'Неизвестная ошибка'}`);
      }
    } catch (err) {
      setError(`Ошибка тестирования ${provider}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const sessionId = getSessionId()
      const response = await fetch(`${API_URL}/api/v1/llm/config?session_id=${sessionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          gigachat: {
            enabled: providers.gigachat.enabled,
            api_key: providers.gigachat.api_key || null
          },
          gemini: {
            enabled: providers.gemini.enabled,
            api_key: providers.gemini.api_key || null
          },
          openrouter: {
            enabled: providers.openrouter.enabled,
            api_key: providers.openrouter.api_key || null,
            model: providers.openrouter.model
          }
        })
      });

      if (response.ok) {
        setSuccess('Конфигурация сохранена успешно');
        // Обновляем состояние после сохранения
        loadProviders();
      } else {
        const errorData = await response.json();
        setError(`Ошибка сохранения: ${errorData.detail || 'Неизвестная ошибка'}`);
      }
    } catch (err) {
      setError(`Ошибка сохранения: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const getProviderStatus = (provider) => {
    if (!provider.enabled) return 'disabled';
    if (provider.has_key) return 'active';
    return 'no_key';
  };

  return (
    <div className="settings-overlay">
      <div className="settings-modal">
        <div className="settings-header">
          <h2>⚙️ Настройки провайдеров LLM</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="settings-content">
          {error && (
            <div className="alert error">
              <span className="alert-icon">⚠️</span>
              {error}
            </div>
          )}

          {success && (
            <div className="alert success">
              <span className="alert-icon">✅</span>
              {success}
            </div>
          )}

          <div className="providers-grid">
            {/* OpenRouter */}
            <div className="provider-card">
              <div className="provider-header">
                <h3>🌐 OpenRouter</h3>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={providers.openrouter.enabled}
                    onChange={(e) => handleProviderToggle('openrouter', e.target.checked)}
                  />
                  <span className="slider"></span>
                </label>
              </div>
              
              <div className="provider-status">
                <span className={`status-badge ${getProviderStatus(providers.openrouter)}`}>
                  {getProviderStatus(providers.openrouter) === 'active' && '✅ Активен'}
                  {getProviderStatus(providers.openrouter) === 'no_key' && '🔑 Нет ключа'}
                  {getProviderStatus(providers.openrouter) === 'disabled' && '❌ Отключен'}
                </span>
              </div>

              <div className="provider-form">
                <div className="form-group">
                  <label>API Key</label>
                  <input
                    type="password"
                    placeholder="Введите ваш OpenRouter API ключ"
                    value={providers.openrouter.api_key || ''}
                    onChange={(e) => handleApiKeyChange('openrouter', e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Модель</label>
                  <select
                    value={providers.openrouter.model}
                    onChange={(e) => handleModelChange(e.target.value)}
                  >
                    <option value="google/gemma-7b-it">Google Gemma 7B (бесплатно)</option>
                    <option value="google/gemma-2-9b-it">Google Gemma 2 9B</option>
                    <option value="meta-llama/llama-3-8b-instruct">Llama 3 8B</option>
                    <option value="meta-llama/llama-3-70b-instruct">Llama 3 70B</option>
                    <option value="anthropic/claude-3-sonnet">Claude 3 Sonnet</option>
                    <option value="openai/gpt-4">GPT-4</option>
                    <option value="openai/gpt-3.5-turbo">GPT-3.5 Turbo</option>
                  </select>
                </div>

                <div className="provider-actions">
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleTestProvider('openrouter')}
                    disabled={loading}
                  >
                    🧪 Протестировать
                  </button>
                </div>
              </div>
            </div>

            {/* GigaChat */}
            <div className="provider-card">
              <div className="provider-header">
                <h3>🤖 GigaChat</h3>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={providers.gigachat.enabled}
                    onChange={(e) => handleProviderToggle('gigachat', e.target.checked)}
                  />
                  <span className="slider"></span>
                </label>
              </div>
              
              <div className="provider-status">
                <span className={`status-badge ${getProviderStatus(providers.gigachat)}`}>
                  {getProviderStatus(providers.gigachat) === 'active' && '✅ Активен'}
                  {getProviderStatus(providers.gigachat) === 'no_key' && '🔑 Нет ключа'}
                  {getProviderStatus(providers.gigachat) === 'disabled' && '❌ Отключен'}
                </span>
              </div>

              <div className="provider-form">
                <div className="form-group">
                  <label>API Key</label>
                  <input
                    type="password"
                    placeholder="Введите ваш GigaChat API ключ"
                    value={providers.gigachat.api_key || ''}
                    onChange={(e) => handleApiKeyChange('gigachat', e.target.value)}
                  />
                </div>

                <div className="provider-actions">
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleTestProvider('gigachat')}
                    disabled={loading}
                  >
                    🧪 Протестировать
                  </button>
                </div>
              </div>
            </div>

            {/* Gemini */}
            <div className="provider-card">
              <div className="provider-header">
                <h3>🌟 Gemini</h3>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={providers.gemini.enabled}
                    onChange={(e) => handleProviderToggle('gemini', e.target.checked)}
                  />
                  <span className="slider"></span>
                </label>
              </div>
              
              <div className="provider-status">
                <span className={`status-badge ${getProviderStatus(providers.gemini)}`}>
                  {getProviderStatus(providers.gemini) === 'active' && '✅ Активен'}
                  {getProviderStatus(providers.gemini) === 'no_key' && '🔑 Нет ключа'}
                  {getProviderStatus(providers.gemini) === 'disabled' && '❌ Отключен'}
                </span>
              </div>

              <div className="provider-form">
                <div className="form-group">
                  <label>API Key</label>
                  <input
                    type="password"
                    placeholder="Введите ваш Gemini API ключ"
                    value={providers.gemini.api_key || ''}
                    onChange={(e) => handleApiKeyChange('gemini', e.target.value)}
                  />
                </div>

                <div className="provider-actions">
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleTestProvider('gemini')}
                    disabled={loading}
                  >
                    🧪 Протестировать
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="settings-footer">
            <button
              className="btn btn-primary"
              onClick={handleSave}
              disabled={loading}
            >
              {loading ? '💾 Сохранение...' : '💾 Сохранить настройки'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;