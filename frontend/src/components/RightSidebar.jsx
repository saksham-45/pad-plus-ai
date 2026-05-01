import { useState, useRef, useEffect, useCallback } from 'react';
import { KpiCard } from './KpiCard';
import { PadWidget } from './widgets/PadWidget';
import { HealthWidget } from './widgets/HealthWidget';
import { MemoryWidget } from './widgets/MemoryWidget';
import { KnowledgeWidget } from './widgets/KnowledgeWidget';
import { MetricsWidget } from './widgets/MetricsWidget';
import { XRayPipeline } from './xray/XRayPipeline';
import { useWebSocket } from '../hooks/useWebSocket';

export function RightSidebar({ isOpen, onToggle, width, onWidthChange }) {
  const sidebarRef = useRef(null);
  const isResizing = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(0);

  // KPI метрики
  const [metrics, setMetrics] = useState({
    activeSessions: 0,
    requestsPerMinute: 0,
    costToday: 0,
    cacheHitRate: 0,
  });

  // Эмоции, здоровье, память, знания
  const [emotion, setEmotion] = useState({});
  const [health, setHealth] = useState({});
  const [memory, setMemory] = useState({});
  const [knowledge, setKnowledge] = useState({});

  // AI Pipeline состояние
  const [activeStage, setActiveStage] = useState(null);
  const [completedStages, setCompletedStages] = useState([]);
  const [pipelineStatus, setPipelineStatus] = useState('idle');
  const [pipelineError, setPipelineError] = useState(null);
  const [stageData, setStageData] = useState({});

  // WebSocket для Pipeline
  const { connected, messages, send } = useWebSocket();

  // Загрузка метрик
  const fetchMetrics = useCallback(async () => {
    try {
      const [activityRes, systemRes] = await Promise.all([
        fetch('/api/v1/metrics/activity'),
        fetch('/api/v1/metrics/system'),
      ]);

      if (activityRes.ok) {
        const activityData = await activityRes.json();
        setMetrics(prev => ({
          ...prev,
          requestsPerMinute: activityData.requests_per_minute || 0,
        }));
      }

      if (systemRes.ok) {
        const systemData = await systemRes.json();
        setMetrics(prev => ({
          ...prev,
          activeSessions: systemData.active_sessions || 0,
          cacheHitRate: systemData.cache_hit_rate || 0,
        }));
      }
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    }
  }, []);

  // Загрузка состояния системы
  const fetchMindState = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/mind-state');
      if (res.ok) {
        const data = await res.json();
        if (data.emotion) setEmotion(data.emotion);
        if (data.health) setHealth(data.health);
        if (data.memory) setMemory(data.memory);
        if (data.knowledge) setKnowledge(data.knowledge);
      }
    } catch (error) {
      console.error('Failed to fetch mind state:', error);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    fetchMindState();
    const interval = setInterval(() => {
      fetchMetrics();
      fetchMindState();
    }, 10000);
    return () => clearInterval(interval);
  }, [fetchMetrics, fetchMindState]);

  // Обработка событий Pipeline по WebSocket
  useEffect(() => {
    if (messages.length === 0) return;

    const lastMessage = messages[messages.length - 1];
    const { type, data } = lastMessage;

    if (type === 'pipeline_update') {
      setActiveStage(data.current_stage);
      if (data.stage_data) {
        setStageData(prev => ({
          ...prev,
          [data.current_stage]: data.stage_data
        }));
      }
      setPipelineStatus('processing');
    }

    if (type === 'trace_event') {
      const { stage, status, duration_ms, data: eventData } = data;

      if (status === 'success') {
        setCompletedStages(prev => {
          if (!prev.includes(stage)) return [...prev, stage];
          return prev;
        });
      }

      if (status === 'error') {
        setPipelineError(eventData?.error || 'Ошибка на стадии ' + stage);
        setPipelineStatus('error');
      }

      if (stage === 'emit' && status === 'success') {
        setPipelineStatus('success');
        setTimeout(() => {
          setActiveStage(null);
          setCompletedStages([]);
          setStageData({});
          setPipelineStatus('idle');
          setPipelineError(null);
        }, 2000);
      }
    }
  }, [messages]);

  // Подписка на pipeline события
  useEffect(() => {
    if (connected) {
      send({ type: 'subscribe', channels: ['pipeline', 'trace'] });
    }
  }, [connected, send]);

  // Обработчик изменения размера
  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    isResizing.current = true;
    startX.current = e.clientX;
    startWidth.current = width;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    console.log('🔧 Started resizing, initial width:', width, 'startX:', startX.current);
  }, [width]);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing.current) return;
      const deltaX = startX.current - e.clientX;
      const newWidth = Math.max(400, Math.min(900, startWidth.current + deltaX));
      console.log('🔧 Resizing: deltaX:', deltaX, 'newWidth:', newWidth);
      onWidthChange(newWidth);
    };

    const handleMouseUp = () => {
      if (isResizing.current) {
        console.log('🔧 Stopped resizing, final width:', startWidth.current);
        isResizing.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [onWidthChange]);

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed right-0 top-1/2 -translate-y-1/2 z-40 bg-[#1F2937] text-white p-2 rounded-l-lg hover:bg-[#374151] transition-colors"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
    );
  }

  return (
    <>
      <aside 
        ref={sidebarRef}
        className="fixed right-0 top-0 h-full bg-[#111827] border-l border-[#1F2937] z-40 flex flex-col"
        style={{ width: `${width}px` }}
      >
        {/* Header */}
        <div className="p-4 border-b border-[#1F2937] flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Показатели системы</h2>
          <button
            onClick={onToggle}
            className="p-1 hover:bg-[#1F2937] rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        {/* KPI карточки */}
        <div className="p-4 grid grid-cols-2 gap-3 border-b border-[#1F2937]">
          <KpiCard
            label="Активные сессии"
            value={metrics.activeSessions}
            color="text-green-500"
            icon={<svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" /></svg>}
          />
          <KpiCard
            label="Запросов/мин"
            value={metrics.requestsPerMinute}
            color="text-blue-500"
            icon={<svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
          />
          <KpiCard
            label="Стоимость (день)"
            value={`$${metrics.costToday}`}
            color="text-yellow-500"
            icon={<svg className="w-4 h-4 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
          <KpiCard
            label="Cache Hit Rate"
            value={`${metrics.cacheHitRate}%`}
            color="text-purple-500"
            icon={<svg className="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>}
          />
        </div>

        {/* Контент - виджеты */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Emotions */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500"></span>
              Эмоции (PAD)
            </h3>
            <PadWidget emotion={emotion} />
          </div>

          {/* Health */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500"></span>
              Здоровье системы
            </h3>
            <HealthWidget health={health} />
          </div>

          {/* Memory */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-purple-500"></span>
              Память
            </h3>
            <MemoryWidget memory={memory} />
          </div>

          {/* Knowledge */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-yellow-500"></span>
              База знаний
            </h3>
            <KnowledgeWidget knowledge={knowledge} />
          </div>

          {/* AI Pipeline */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-500"></span>
              AI Pipeline
            </h3>
            <XRayPipeline
              activeStage={activeStage}
              completedStages={completedStages}
              stageData={stageData}
              status={pipelineStatus}
              error={pipelineError}
            />
          </div>

          {/* Metrics */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500"></span>
              Метрики
            </h3>
            <MetricsWidget />
          </div>
        </div>

        {/* Ручка для изменения размера */}
        <div
          onMouseDown={handleMouseDown}
          className="absolute left-0 top-0 w-2 h-full cursor-col-resize hover:bg-[#6366F1] hover:w-3 transition-all z-50 flex items-center justify-center"
          style={{ transform: 'translateX(-50%)' }}
        >
          <div className="h-12 w-0.5 bg-gray-600 rounded-full opacity-50 hover:opacity-100 hover:bg-[#6366F1] transition-all" />
        </div>
      </aside>
    </>
  );
}