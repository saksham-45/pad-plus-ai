import React, { useState, useEffect, useCallback } from 'react';
import { FlowWidget } from './widgets/FlowWidget';
import { PadWidget } from './widgets/PadWidget';
import { MetricsWidget } from './widgets/MetricsWidget';
import { LogsWidget } from './widgets/LogsWidget';
import { HealthWidget } from './widgets/HealthWidget';
import { MemoryWidget } from './widgets/MemoryWidget';
import { KnowledgeWidget } from './widgets/KnowledgeWidget';
import { SystemResourcesWidget } from './widgets/SystemResourcesWidget';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';

// Оптимизированная раскладка - все в одной компактной области
const widgetGrid = [
  { id: 'system-resources', col: 'col-span-3' },
  { id: 'flow', col: 'col-span-3' },
  { id: 'pad', col: 'col-span-2' },
  { id: 'health', col: 'col-span-4' },
  { id: 'memory', col: 'col-span-3' },
  { id: 'knowledge', col: 'col-span-3' },
  { id: 'metrics', col: 'col-span-6' },
  { id: 'logs', col: 'col-span-6' },
];

// KPI карточки статуса системы
const systemStatusItems = [
  { label: 'System', value: 'Online', color: 'text-green-500' },
  { label: 'Memory', value: 'Active', color: 'text-blue-500' },
  { label: 'PAD State', value: 'Stable', color: 'text-purple-500' },
  { label: 'Model', value: 'GPT-4', color: 'text-yellow-500' },
];

// Этапы обработки
const processingFlow = [
  { step: '📥 Input', icon: '📥' },
  { step: '🧠 PAD', icon: '🧠' },
  { step: '📚 RAG', icon: '📚' },
  { step: '🤖 LLM', icon: '🤖' },
  { step: '📤 Output', icon: '📤' },
];

export default function Dashboard() {
  const [mindState, setMindState] = useState(null);
  const [logs, setLogs] = useState([]);
  const [metricsData, setMetricsData] = useState([]);
  const [pipelineStatus, setPipelineStatus] = useState('idle');
  const [activeStep, setActiveStep] = useState(null);
  
  // Загрузка состояния системы
  const fetchMindState = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/mind-state');
      if (response.ok) {
        const data = await response.json();
        setMindState(data);
      }
    } catch (error) {
      console.error('Failed to fetch mind state:', error);
    }
  }, []);
  
  // Загрузка логов
  const fetchLogs = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/events/recent?limit=20');
      if (response.ok) {
        const data = await response.json();
        if (data.events) {
          setLogs(data.events.map(e => ({
            id: e.id,
            timestamp: e.timestamp,
            type: e.type,
            message: `${e.type}: ${JSON.stringify(e.data).slice(0, 100)}`,
            source: e.source,
          })));
        }
      }
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    }
  }, []);
  
  // Периодическое обновление
  useEffect(() => {
    fetchMindState();
    fetchLogs();
    
    const interval = setInterval(() => {
      fetchMindState();
    }, 5000);
    
    return () => clearInterval(interval);
  }, [fetchMindState, fetchLogs]);
  
  // Генерация демо данных для графика
  useEffect(() => {
    const generateData = () => {
      const now = Date.now();
      return Array.from({ length: 20 }, (_, i) => ({
        time: i,
        value: 0.3 + Math.random() * 0.4 + Math.sin((now + i * 1000) / 3000) * 0.2,
      }));
    };
    
    setMetricsData(generateData());
    
    const interval = setInterval(() => {
      setMetricsData(prev => {
        const newData = [...prev.slice(1)];
        newData.push({
          time: prev[prev.length - 1].time + 1,
          value: 0.3 + Math.random() * 0.4 + Math.sin(Date.now() / 3000) * 0.2,
        });
        return newData;
      });
    }, 2000);
    
    return () => clearInterval(interval);
  }, []);
  
  // Рендер виджета по типу
  const renderWidget = (widgetType) => {
    switch (widgetType) {
      case 'flow':
        return (
          <FlowWidget
            activeStep={activeStep}
            status={pipelineStatus}
          />
        );
      case 'pad':
        return (
          <PadWidget
            emotion={mindState?.emotion || {}}
          />
        );
      case 'metrics':
        return (
          <MetricsWidget
            data={metricsData}
            title="Pipeline Performance"
          />
        );
      case 'logs':
        return (
          <LogsWidget logs={logs} />
        );
      case 'health':
        return (
          <HealthWidget
            health={mindState?.health || {}}
          />
        );
      case 'memory':
        return (
          <MemoryWidget
            memory={mindState?.memory || {}}
          />
        );
      case 'knowledge':
        return (
          <KnowledgeWidget
            knowledge={mindState?.knowledge || {}}
          />
        );
      case 'system-resources':
        return <SystemResourcesWidget />;
      default:
        return <div>Unknown widget: {widgetType}</div>;
    }
  };

  // Запуск демо обработки
  const runDemo = () => {
    setPipelineStatus('processing');
    setActiveStep('input');
    setTimeout(() => setActiveStep('safety'), 200);
    setTimeout(() => setActiveStep('intent'), 400);
    setTimeout(() => setActiveStep('retrieve'), 600);
    setTimeout(() => setActiveStep('generate'), 800);
    setTimeout(() => setActiveStep('output'), 1000);
    setTimeout(() => {
      setPipelineStatus('success');
      setActiveStep(null);
    }, 1200);
  };
  
  return (
    <div className="min-h-screen bg-[#0B0F14] text-white p-3">
      {/* Единая компактная сетка */}
      <div className="grid grid-cols-12 gap-2">
        
        {/* HEADER */}
        <div className="col-span-12 flex items-center justify-between px-1 mb-1">
          <div>
            <h1 className="text-lg font-bold">PAD-AI Control Center</h1>
            <p className="text-xs text-gray-400">Cognitive Layer for AI Systems</p>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => window.location.href='/chat'}>Chat</Button>
            <Button size="sm" onClick={runDemo}>Launch</Button>
          </div>
        </div>

        {/* KPI карточки */}
        <div className="col-span-12 grid grid-cols-4 gap-2">
          {systemStatusItems.map((item) => (
            <Card key={item.label} className="bg-[#111827] border border-[#1F2937]">
              <CardContent className="p-2">
                <p className="text-xs text-gray-400">{item.label}</p>
                <p className={`text-sm font-bold ${item.color}`}>{item.value}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Processing Flow - компактный */}
        <div className="col-span-12">
          <Card className="bg-[#111827] border border-[#1F2937]">
            <CardContent className="p-2">
              <div className="flex items-center gap-1 text-xs text-gray-300 overflow-x-auto">
                {processingFlow.map((item, index) => (
                  <React.Fragment key={item.step}>
                    <div className="flex items-center gap-1 px-2 py-1 bg-[#1F2937] rounded whitespace-nowrap">
                      <span>{item.icon}</span>
                      <span className="text-xs">{item.step}</span>
                    </div>
                    {index < processingFlow.length - 1 && (
                      <span className="text-gray-500">→</span>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* GRID LAYOUT с виджетами */}
        <div className="col-span-12 grid grid-cols-12 gap-2">
          {widgetGrid.map((widget) => (
            <div key={widget.id} className={`${widget.col} bg-[#111827] border border-[#1F2937] rounded-lg p-2`}>
              {renderWidget(widget.id)}
            </div>
          ))}
        </div>

        {/* Status Bar */}
        <div className="col-span-12 flex justify-between items-center text-xs text-gray-500 px-1">
          <div className="flex gap-3">
            <span>WS: <span className="text-green-500">●</span></span>
            <span>BE: <span className="text-green-500">●</span></span>
          </div>
          <span>{new Date().toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
}