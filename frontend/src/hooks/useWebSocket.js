import { useState, useEffect, useCallback, useRef } from 'react';
import { getAuthToken, getRefreshToken } from '../services/api';

const MAX_MESSAGES = 5;

// Глобальный экземпляр для предотвращения множественных подключений
let globalWsInstance = null;
let globalSubscribers = 0;

export function useWebSocket(url = null) {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimeout = useRef(null);
  const isMountedRef = useRef(false);

  const connect = useCallback(() => {
    // Если уже есть глобальное подключение - используем его
    if (globalWsInstance && globalWsInstance.readyState === WebSocket.OPEN) {
      wsRef.current = globalWsInstance;
      setConnected(true);
      return;
    }

    // Защита от множественных подключений
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      return;
    }

    // Очищаем предыдущий таймаут если есть
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }

    const token = getAuthToken();
    const refreshToken = getRefreshToken();
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const baseWsUrl = url || `${protocol}//${window.location.host}/ws`;
    const wsUrl = new URL(baseWsUrl);

    if (token) {
      wsUrl.searchParams.set('token', token);
    }
    if (refreshToken) {
      wsUrl.searchParams.set('refresh_token', refreshToken);
    }

    try {
      const ws = new WebSocket(wsUrl.toString());
      globalWsInstance = ws;
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMountedRef.current) return;
        console.log('✅ WebSocket подключен');
        setConnected(true);
        
        // Подписка на обновления
        ws.send(JSON.stringify({
          type: 'subscribe',
          channels: ['all']
        }));
      };

      ws.onmessage = (event) => {
        if (!isMountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          setMessages(prev => [...prev.slice(-(MAX_MESSAGES - 1)), data]);
        } catch (e) {
          console.error('❌ Ошибка парсинга сообщения:', e);
        }
      };

      ws.onclose = (event) => {
        if (!isMountedRef.current) return;
        console.log('🔌 WebSocket отключен', event.code, event.reason);
        setConnected(false);
        globalWsInstance = null;
        
        // Автоматическое переподключение только если соединение было разорвано не корректно
        if (!event.wasClean && event.code !== 1000 && event.code !== 1001) {
          reconnectTimeout.current = setTimeout(connect, 5000);
        }
      };

      ws.onerror = (error) => {
        if (!isMountedRef.current) return;
        console.warn('⚠️ WebSocket ошибка (попытка переподключения...)');
      };
    } catch (error) {
      console.error('❌ Ошибка создания WebSocket:', error);
      if (isMountedRef.current) {
        reconnectTimeout.current = setTimeout(connect, 5000);
      }
    }
  }, [url]);

  const disconnect = useCallback(() => {
    globalSubscribers--;
    
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }

    // Закрываем соединение только если больше нет подписчиков
    if (globalSubscribers <= 0 && wsRef.current) {
      wsRef.current.close(1000, 'Normal closure');
      wsRef.current = null;
      globalWsInstance = null;
    }
    
    setConnected(false);
  }, []);

  const send = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    globalSubscribers++;

    // Задержка для защиты от двойного монтажа React 18 Strict Mode
    const initTimer = setTimeout(() => {
      if (isMountedRef.current) {
        connect();
      }
    }, 250);

    return () => {
      isMountedRef.current = false;
      clearTimeout(initTimer);
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    connected,
    messages,
    send,
    connect,
    disconnect,
  };
}

export default useWebSocket;