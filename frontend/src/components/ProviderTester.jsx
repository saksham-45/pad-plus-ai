import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';

export function ProviderTester({ keyId, provider, model }) {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState(null);

  const testConnection = async () => {
    setTesting(true);
    setResult(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/keys/${keyId}/test`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
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

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          🔍 Тест подключения
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
        </div>
      </CardContent>
    </Card>
  );
}

export default ProviderTester;