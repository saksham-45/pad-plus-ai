import { useState, useRef, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';
import { useWebSocket } from '../hooks/useWebSocket';
import CognitivePanel from './CognitivePanel';

export function ChatInterface({ selectedModel, user }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const messagesEndRef = useRef(null);
  const ws = useWebSocket();
  
  // === COGNITIVE UX LAYER ===
  const [showMetrics, setShowMetrics] = useState(true);
  const [lastResponseMeta, setLastResponseMeta] = useState(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Обработка WebSocket сообщений
  useEffect(() => {
    if (ws.messages.length > 0) {
      const lastMsg = ws.messages[ws.messages.length - 1];
      // Обрабатываем сообщения от сервера
      if (lastMsg.type === 'response') {
        setMessages(prev => {
          const updated = [...prev];
          const lastAssistant = updated.findIndex(m => m.role === 'assistant' && m.streaming);
          if (lastAssistant >= 0) {
            updated[lastAssistant] = {
              ...updated[lastAssistant],
              content: updated[lastAssistant].content + (lastMsg.content || ''),
            };
          }
          return updated;
        });
      }
    }
  }, [ws.messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { role: 'user', content: input.trim() };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setStreaming(true);

    // Добавляем placeholder для ответа
    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }]);

    console.log('📤 Sending chat request:', {
      keyId: selectedModel?.keyId,
      model: selectedModel?.id,
      provider: selectedModel?.provider,
      modelName: selectedModel?.name,
    });

    try {
      const token = localStorage.getItem('access_token');

      // Отправляем через полную систему (Pipeline)
      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: userMessage.content,
          key_id: selectedModel?.keyId || null,
          model: selectedModel?.id || 'auto',
          provider: selectedModel?.provider || null,
          auto_mode: false,  // Всегда через полную систему
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || 'Ошибка отправки');
      }

      const data = await response.json();
      
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: 'assistant',
          content: data.text || 'Нет ответа',
          streaming: false,
        };
        return updated;
      });
      
      // === COGNITIVE UX LAYER: Сохраняем мета-данные ответа ===
      setLastResponseMeta({
        cognitive: data.cognitive,
        memory: data.memory,
        emotion: data.emotion,
        truth: data.truth,
        xray: data.xray,
        meta: data.meta,
        execution_time_ms: data.cognitive?.execution_time_ms,
      });
    } catch (err) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: 'assistant',
          content: `Ошибка: ${err.message}`,
          streaming: false,
        };
        return updated;
      });
    } finally {
      setLoading(false);
      setStreaming(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span>💬</span>
          Чат
          {selectedModel && (
            <span className="text-xs text-text-secondary font-normal ml-2">
              {selectedModel.name}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col">
        {/* Сообщения */}
        <div className="flex-1 overflow-y-auto space-y-4 mb-4 min-h-0">
          {messages.length === 0 ? (
            <div className="text-center text-text-muted py-8">
              <div className="text-4xl mb-2">🤖</div>
              <div className="text-sm">Начните диалог с AI</div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2 ${
                    msg.role === 'user'
                      ? 'bg-primary text-white'
                      : 'bg-gray-800 text-text-primary'
                  }`}
                >
                  <div className="text-base whitespace-pre-wrap">{msg.content}</div>
                  {msg.streaming && (
                    <span className="inline-block w-2 h-4 ml-1 bg-primary animate-pulse align-middle" />
                  )}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Ввод */}
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Введите сообщение..."
            disabled={loading}
            className="flex-1 px-5 py-3 bg-gray-800 border border-border rounded-xl text-text-primary text-base focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
          />
          <Button
            onClick={sendMessage}
            loading={loading}
            disabled={!input.trim() || !selectedModel}
            className="px-6 py-3 text-lg"
          >
            {loading ? '...' : 'Отправить'}
          </Button>
          {/* Кнопка переключения метрик */}
          <Button
            variant="outline"
            onClick={() => setShowMetrics(!showMetrics)}
            className={`px-4 ${showMetrics ? 'bg-primary text-white' : ''}`}
            title="Показать/скрыть когнитивные метрики"
          >
            🧠
          </Button>
        </div>
        
        {/* === COGNITIVE UX LAYER: Панель метрик === */}
        {showMetrics && lastResponseMeta && (
          <CognitivePanel {...lastResponseMeta} />
        )}
      </CardContent>
    </Card>
  );
}

export default ChatInterface;