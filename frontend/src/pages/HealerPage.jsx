import { useState, useEffect, useCallback, useRef } from 'react';
import { HealerTracePanel } from '../components/xray/HealerTracePanel';
import { HealerResults } from '../components/healer/HealerResults';
import { HealerReflection } from '../components/healer/HealerReflection';
import { HealerHistory } from '../components/healer/HealerHistory';
import { useWebSocket } from '../hooks/useWebSocket';
import { apiFetch } from '../services/api';
import { HealerReflectionPanel } from './HealerReflectionPanel';


function HealerPage() {
  const [bridgeStatus, setBridgeStatus] = useState({ status: 'ok', bridge: 'not_available' });
  const [bridgeMode, setBridgeMode] = useState('monitor');
  const [cycles, setCycles] = useState([]);
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState('idle');
  const [latestReports, setLatestReports] = useState([]);

  // Auto-cycle state
  const [autoCycleEnabled, setAutoCycleEnabled] = useState(false);
  const [autoCycleRunning, setAutoCycleRunning] = useState(false);
  const [autoCycleInterval, setAutoCycleInterval] = useState(300);
  const processedRef = useRef(0);

  const { connected, messages, send } = useWebSocket();

  // Загрузка статуса bridge и auto-cycle при монтировании
  useEffect(() => {
    apiFetch('/api/v1/healer/bridge/status')
      .then(r => r.ok && r.json().then(setBridgeStatus))
      .catch(() => {});

    apiFetch('/api/v1/healer/bridge/mode')
      .then(r => r.ok && r.json().then(d => {
        if (d.mode) setBridgeMode(d.mode);
        if (d.data?.mode) setBridgeMode(d.data.mode);
      }))
      .catch(() => {});

    apiFetch('/api/v1/healer/bridge/auto-cycle')
      .then(r => r.ok && r.json().then(d => {
        setAutoCycleEnabled(!!d.enabled);
        if (d.interval_sec) setAutoCycleInterval(d.interval_sec);
      }))
      .catch(() => {});

    refreshReports();
  }, []);

  const refreshReports = () => {
    apiFetch('/api/v1/healer/bridge/reports/latest?min_severity=info')
      .then(r => r.ok && r.json().then(d => {
        if (d.reports) setLatestReports(d.reports);
      }))
      .catch(() => {});
  };

  // Обработка WebSocket сообщений
  const handleMessage = useCallback((message) => {
    const { type, data } = message;

    if (type === 'subscribed' || type === 'pong' || type === 'welcome') {
      return;
    }

    if (type.startsWith('healer_bridge_') || type.startsWith('healer_diag_')) {
      const event = {
        type,
        data,
        timestamp: data?.timestamp || new Date().toLocaleTimeString('ru-RU'),
        id: Date.now() + Math.random(),
      };
      setEvents(prev => [...prev, event].slice(-200));

      if (type === 'healer_bridge_cycle_complete' || type === 'healer_diag_cycle_complete') {
        setCycles(prev => [...prev, {
          number: (prev.length + 1),
          timestamp: new Date().toLocaleTimeString('ru-RU'),
          status: data?.status || 'success',
          reports: data?.reports || data?.results || [],
        }]);
        if (data?.reports?.length) {
          setLatestReports(data.reports);
        }
        setStatus('idle');
      } else if (type === 'healer_bridge_diag_started' || type === 'healer_diag_started') {
        setStatus('processing');
      } else if (type === 'healer_bridge_diag_completed' || type === 'healer_diag_completed') {
        setStatus('idle');
      }

      if (type === 'healer_bridge_auto_cycle_start') {
        setAutoCycleRunning(true);
      } else if (type === 'healer_bridge_auto_cycle_complete') {
        setAutoCycleRunning(false);
        if (data?.reports?.length) {
          setLatestReports(data.reports);
        }
        if (data?.result) {
          setCycles(prev => [...prev, {
            number: (prev.length + 1),
            timestamp: new Date().toLocaleTimeString('ru-RU'),
            status: data.result.status || data.status || 'done',
            reports: data.reports || [],
          }]);
        }
      }
    }
  }, []);

  useEffect(() => {
    if (messages.length > processedRef.current) {
      for (let i = processedRef.current; i < messages.length; i++) {
        handleMessage(messages[i]);
      }
      processedRef.current = messages.length;
    }
  }, [messages, handleMessage]);

  // Подписка на HEALER каналы
  useEffect(() => {
    if (connected) {
      send({
        type: 'subscribe',
        channels: ['healer', 'healer_bridge', 'healer_diag', 'all']
      });
    }
  }, [connected, send]);

  const handleStartCycle = async () => {
    try {
      setStatus('processing');
      const r = await apiFetch('/api/v1/healer/bridge/cycle', { method: 'POST' });
      if (!r.ok) {
        setStatus('error');
        return;
      }
      const result = await r.json();
      setStatus('idle');
      if (result?.cycle?.reports?.length) {
        setLatestReports(result.cycle.reports);
      }
      if (result?.cycle) {
        setCycles(prev => [...prev, {
          number: (prev.length + 1),
          timestamp: new Date().toLocaleTimeString('ru-RU'),
          status: result.cycle.status || 'success',
          reports: result.cycle.reports || [],
        }]);
      }
    } catch (e) {
      setStatus('error');
    }
  };

  const handleModeChange = async (newMode) => {
    try {
      const r = await apiFetch('/api/v1/healer/bridge/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode }),
      });
      if (r.ok) {
        setBridgeMode(newMode);
      }
    } catch (e) {
      // ignore
    }
  };

  const handleAutoCycleToggle = async (enable) => {
    try {
      if (enable) {
        await apiFetch('/api/v1/healer/bridge/auto-cycle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ interval_sec: autoCycleInterval, mode: bridgeMode === 'monitor' ? 'suggest' : bridgeMode }),
        });
        setAutoCycleEnabled(true);
      } else {
        await apiFetch('/api/v1/healer/bridge/auto-cycle', { method: 'DELETE' });
        setAutoCycleEnabled(false);
        setAutoCycleRunning(false);
      }
    } catch (e) {
      // ignore
    }
  };

  const handleAutoCycleIntervalChange = async (newInterval) => {
    try {
      await apiFetch('/api/v1/healer/bridge/auto-cycle', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interval_sec: newInterval }),
      });
      setAutoCycleInterval(newInterval);
    } catch (e) {
      // ignore
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
              HEALER
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Самодиагностика кода и мета-обучение
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${
              bridgeStatus.bridge === 'available' ? 'bg-green-500' : 'bg-yellow-500'
            }`} />
            <span className="text-sm text-gray-400">
              Bridge: {bridgeStatus.bridge === 'available' ? 'Online' : 'Standby'}
            </span>
          </div>
        </div>

        {/* Healer Trace Panel */}
        <HealerTracePanel
          cycles={cycles}
          events={events}
          status={status}
          mode={bridgeMode}
          bridgeConnected={connected}
          onStartCycle={handleStartCycle}
          onModeChange={handleModeChange}

          autoCycleEnabled={autoCycleEnabled}
          autoCycleRunning={autoCycleRunning}
          autoCycleInterval={autoCycleInterval}
          onAutoCycleToggle={handleAutoCycleToggle}
          onAutoCycleIntervalChange={handleAutoCycleIntervalChange}

          latestReports={latestReports}
          onRefreshReports={refreshReports}
        />

        {/* New components in a grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          <HealerResults reports={latestReports} onRefresh={refreshReports} />
          <HealerHistory cycles={cycles} />
        </div>

        {/* Healer Reflection */}
        <HealerReflectionPanel />


        {/* Footer */}
        <div className="mt-6 text-center text-xs text-gray-500">
          HEALER Bridge v0.1 — Модуль самодиагностики PAD+ AI
        </div>
      </div>
    </div>
  );
}

export default HealerPage;

