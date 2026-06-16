import React, { useState, useEffect, useCallback } from 'react';
import { XRayPipeline } from '../components/xray/XRayPipeline';
import { ThoughtStream } from '../components/xray/ThoughtStream';
import { EmotionPanel } from '../components/xray/EmotionPanel';
import { DecisionLog } from '../components/xray/DecisionLog';
import { useWebSocket } from '../hooks/useWebSocket';

export function XRayPage() {
  // Состояние пайплайна
  const [activeStage, setActiveStage] = useState(null);
  const [completedStages, setCompletedStages] = useState([]);
  const [pipelineStatus, setPipelineStatus] = useState('idle');
  const [pipelineError, setPipelineError] = useState(null);
  const [stageData, setStageData] = useState({});

  // Состояние мыслей
  const [thoughts, setThoughts] = useState([]);

  // Состояние эмоций
  const [emotions, setEmotions] = useState({});
  
  // Состояние решений
  const [decisions, setDecisions] = useState([]);

  // Состояние сессии
  const [sessionId, setSessionId] = useState(null);

  // Используем общий хук WebSocket
  const { connected, messages, send } = useWebSocket();

  // Обработка сообщений
  const handleMessage = (message) => {
    const { type, data } = message;

    switch (type) {
      case 'subscribed':
        console.log('✅ Подписано на каналы:', data?.channels);
        break;

      case 'pong':
        // Heartbeat response
        break;

      case 'trace_event':
        handleTraceEvent(data);
        break;

      case 'thought':
        handleThought(data);
        break;

      case 'pipeline_update':
        handlePipelineUpdate(data);
        break;

      case 'emotion_update':
        handleEmotionUpdate(data);
        break;

      case 'decision':
        handleDecision(data);
        break;

      case 'welcome':
        console.log('🔬 Добро пожаловать в X-Ray:', data);
        break;

      default:
        console.log('🔬 Неизвестное сообщение:', type, data);
    }
  };

  const handleTraceEvent = (data) => {
    const { stage, status, duration_ms, timestamp, data: eventData } = data;

    // Обновляем активную стадию
    if (status === 'success' || status === 'error') {
      setCompletedStages(prev => {
        if (!prev.includes(stage)) {
          return [...prev, stage];
        }
        return prev;
      });

      // Устанавливаем следующую стадию активной
      const stages = ['safety', 'intent', 'retrieve', 'persona', 'generate', 'verify', 'remember', 'emit'];
      const currentIndex = stages.indexOf(stage);
      if (currentIndex < stages.length - 1) {
        setActiveStage(stages[currentIndex + 1]);
      } else {
        setActiveStage(null);
        setPipelineStatus('success');
      }
    } else {
      setActiveStage(stage);
    }

    // Сохраняем данные стадии
    setStageData(prev => ({
      ...prev,
      [stage]: {
        ...eventData,
        duration_ms: Math.round(duration_ms),
        timestamp
      }
    }));

    if (status === 'error') {
      setPipelineError(eventData?.error || 'Ошибка на стадии ' + stage);
      setPipelineStatus('error');
    }
  };

  const handleThought = (data) => {
    setThoughts(prev => [...prev, data].slice(-50)); // Храним последние 50 мыслей
  };

  const handlePipelineUpdate = (data) => {
    const { current_stage, stage_data } = data;
    setActiveStage(current_stage);

    if (stage_data) {
      setStageData(prev => ({
        ...prev,
        [current_stage]: {
          ...prev[current_stage],
          ...stage_data
        }
      }));
    }
  };

  const handleEmotionUpdate = (data) => {
    setEmotions(data);
  };

  const handleDecision = (data) => {
    setDecisions(prev => [...prev, { ...data, id: Date.now(), timestamp: new Date() }].slice(-100));
  };

  // Обработка входящих сообщений
  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      handleMessage(lastMessage);
    }
  }, [messages]);

  // Подписка на каналы X-Ray при подключении
  useEffect(() => {
    if (connected) {
      send({
        type: 'subscribe',
        channels: ['trace', 'thought', 'pipeline', 'emotion', 'decision', 'all']
      });
    }
  }, [connected, send]);

  // Сброс состояния
  const resetPipeline = () => {
    setActiveStage(null);
    setCompletedStages([]);
    setPipelineStatus('idle');
    setPipelineError(null);
    setStageData({});
    setThoughts([]);
    setEmotions({});
    setDecisions([]);
    setSessionId(null);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              🔬 X-Ray
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Система полной наблюдаемости AI
            </p>
          </div>

          <div className="flex items-center gap-4">
            {/* Status Indicator */}
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${
                pipelineStatus === 'processing' ? 'bg-blue-500 animate-pulse' :
                pipelineStatus === 'success' ? 'bg-green-500' :
                pipelineStatus === 'error' ? 'bg-red-500' :
                'bg-gray-500'
              }`} />
              <span className="text-sm text-gray-400">
                {pipelineStatus === 'idle' && 'Ожидание'}
                {pipelineStatus === 'processing' && 'Обработка'}
                {pipelineStatus === 'success' && 'Завершено'}
                {pipelineStatus === 'error' && 'Ошибка'}
              </span>
            </div>

            {/* Reset Button */}
            <button
              onClick={resetPipeline}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm transition-colors"
            >
              Сбросить
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Pipeline & Stats */}
          <div className="lg:col-span-2 space-y-6">
            {/* Pipeline Visualization */}
            <XRayPipeline
              activeStage={activeStage}
              completedStages={completedStages}
              stageData={stageData}
              status={pipelineStatus}
              error={pipelineError}
            />

            {/* Session Info */}
            {sessionId && (
              <div className="p-4 bg-gray-900/50 border border-gray-700 rounded-lg">
                <div className="text-sm text-gray-400">
                  Session ID: <code className="text-gray-300">{sessionId}</code>
                </div>
              </div>
            )}

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
              <StatCard
                label="Стадии завершено"
                value={completedStages.length}
                total={8}
                color="blue"
              />
              <StatCard
                label="Мыслей"
                value={thoughts.length}
                color="purple"
              />
              <StatCard
                label="Решений"
                value={decisions.length}
                color="cyan"
              />
              <StatCard
                label="Эмоций"
                value={Object.keys(emotions).length}
                color="pink"
              />
              <StatCard
                label="Статус"
                value={pipelineStatus}
                color={
                  pipelineStatus === 'success' ? 'green' :
                  pipelineStatus === 'error' ? 'red' : 'gray'
                }
              />
              <StatCard
                label="WebSocket"
                value={connected ? 'Online' : 'Offline'}
                color={connected ? 'green' : 'red'}
              />
            </div>
          </div>

          {/* Right Column - Thought Stream, Emotions & Decisions */}
          <div className="lg:col-span-1 space-y-6">
            <div className="max-h-[350px]">
              <ThoughtStream
                thoughts={thoughts}
                maxThoughts={30}
                autoScroll={true}
              />
            </div>
            
            <EmotionPanel emotions={emotions} />
            
            <DecisionLog decisions={decisions} maxItems={10} />
          </div>
        </div>

        {/* Footer */}
        <div className="mt-6 text-center text-xs text-gray-500">
          X-Ray v1.0.0 — Система полной наблюдаемости PAD+ AI
        </div>
      </div>
    </div>
  );
}

// Компонент карточки статистики
function StatCard({ label, value, total, color = 'blue' }) {
  const colorClasses = {
    blue: 'text-blue-400',
    purple: 'text-purple-400',
    green: 'text-green-400',
    red: 'text-red-400',
    gray: 'text-gray-400',
    cyan: 'text-cyan-400',
    pink: 'text-pink-400'
  };

  return (
    <div className="p-4 bg-gray-900/50 border border-gray-700 rounded-lg">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-2xl font-bold ${colorClasses[color]}`}>
        {value}
        {total !== undefined && (
          <span className="text-sm text-gray-500 ml-1">/ {total}</span>
        )}
      </div>
    </div>
  );
}

export default XRayPage;