import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';
import { apiFetch } from '../services/api';

export function ProviderTester({ keyId, provider, model }) {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState(null);
  const [autoCheckDone, setAutoCheckDone] = useState(false);

  // Авто-проверка статуса ключа при монтировании компонента
  useEffect(() => {
    if (keyId && !autoCheckDone) {
      const autoTest = async () => {
        setTesting(true);
        try {
          const response = await apiFetch(`/api/v1/keys/${keyId}/test`, {
            method: 'POST',
          });
          const data = await response.json();
          setResult(data);
        } catch (err) {
          setResult({
            success: false,
            message: `Ошибка: ${err.message}`,
          });
        } finally {
          setTesting(false);
          setAutoCheckDone(true);
        }
      };
      autoTest();
    }
  }, [keyId, autoCheckDone]);

  const testConnection = async () => {
    setTesting(true);
    setResult(null);

    try {
      const response = await apiFetch(`/api/v1/keys/${keyId}/test`, {
        method: 'POST',
      });

      if (!response.ok) {
        let errorMessage = 'Ошибка тестирования';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage;
        } catch {
          // Пустой ответ от сервера
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setResult({
        success: false,
        message: `Ошибка: ${err.message}`,
      });
    } finally {
      setTesting(false);
    }
  };

  // Статус-индикатор на основе результата
  const getStatusIndicator = () => {
    if (testing) return { icon: '🔄', color: 'text-yellow-500', label: 'Проверка...' };
    if (!result) return { icon: '⚪', color: 'text-gray-500', label: 'Не проверен' };
    if (result.success) return { icon: '🟢', color: 'text-green-500', label: 'Работает' };
    return { icon: '🔴', color: 'text-red-500', label: 'Ошибка' };
  };

  const status = getStatusIndicator();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <span className={status.color}>{status.icon}</span>
          <span>Тест подключения</span>
          <span className={`text-xs px-2 py-0.5 rounded-full ${status.color} bg-opacity-10`}>
            {status.label}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="text-sm text-text-secondary">
            Провайдер: <span className="text-text-primary font-medium">{provider}</span>
          </div>
          {model && (
            <div className="text-sm text-text-secondary">
              Модель: <span className="text-text-primary font-medium">{model}</span>
            </div>
          )}

          <Button
            onClick={testConnection}
            loading={testing}
            variant="outline"
            size="sm"
          >
            {testing ? 'Тестирование...' : 'Проверить подключение'}
          </Button>

          {result && (
            <div className={`p-3 rounded-lg text-sm ${
              result.success
                ? 'bg-green-500/10 text-green-500 border border-green-500/20'
                : 'bg-red-500/10 text-red-500 border border-red-500/20'
            }`}>
              <div className="font-medium">
                {result.success ? '✅ Успешно' : '❌ Ошибка'}
              </div>
              <div className="mt-1 text-text-secondary">
                {result.message}
              </div>
              {result.model_tested && (
                <div className="mt-1 text-xs">
                  Протестировано: {result.model_tested}
                </div>
              )}
            </div>
          )}

          {/* Информация о fallback */}
          {result && result.success === false && provider?.toLowerCase() === 'openrouter' && (
            <div className="p-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-xs text-yellow-500">
              ⚠️ Если OpenRouter недоступен, система автоматически переключится на GigaChat.
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default ProviderTester;