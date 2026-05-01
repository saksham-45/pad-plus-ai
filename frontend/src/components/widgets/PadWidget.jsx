import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { motion, AnimatePresence } from 'framer-motion';
import { useWebSocket } from '../../hooks/useWebSocket';

const padDimensions = [
  { key: 'pleasure', label: 'Pleasure', min: -1, max: 1, neutral: 0, color: 'bg-green-500' },
  { key: 'arousal', label: 'Arousal', min: -1, max: 1, neutral: 0, color: 'bg-yellow-500' },
  { key: 'dominance', label: 'Dominance', min: -1, max: 1, neutral: 0, color: 'bg-blue-500' },
  { key: 'curiosity', label: 'Curiosity', min: 0, max: 1, neutral: 0.5, color: 'bg-purple-500' },
  { key: 'confidence', label: 'Confidence', min: 0, max: 1, neutral: 0.5, color: 'bg-orange-500' },
  { key: 'social_connection', label: 'Social', min: -1, max: 1, neutral: 0, color: 'bg-pink-500' },
];

function ProgressBar({ value, min, max, neutral, color }) {
  const range = max - min;
  const percentage = ((value - min) / range) * 100;
  const neutralPercentage = ((neutral - min) / range) * 100;
  
  return (
    <div className="relative">
      <div className="flex justify-between text-xs text-text-muted mb-1">
        <span>{min}</span>
        <span className="text-text-primary font-medium">{value.toFixed(2)}</span>
        <span>{max}</span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        {/* Neutral marker */}
        <div 
          className="absolute h-full w-0.5 bg-gray-500"
          style={{ left: `${neutralPercentage}%` }}
        />
        {/* Value bar */}
        <motion.div
          className={`h-full ${color} rounded-full`}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

export function PadWidget({ emotion: initialEmotion = {} }) {
  const [state, setState] = useState({
    удовольствие: initialEmotion?.удовольствие ?? 0,
    возбуждение: initialEmotion?.возбуждение ?? 0,
    доминирование: initialEmotion?.доминирование ?? 0,
    любопытство: initialEmotion?.любопытство ?? 0.5,
    уверенность: initialEmotion?.уверенность ?? 0.5,
    социальная_связь: initialEmotion?.социальная_связь ?? 0,
    lastUpdate: Date.now()
  });

  const { connected, messages, send } = useWebSocket();

  // Подписка на обновления эмоций по WebSocket в реальном времени
  useEffect(() => {
    if (connected) {
      send({ type: 'subscribe', channels: ['emotion', 'cognitive'] });
    }
  }, [connected, send]);

  // Обработка входящих сообщений
  useEffect(() => {
    if (messages.length === 0) return;
    
    const lastMessage = messages[messages.length - 1];
    const { type, data } = lastMessage;

    if (type === 'emotion_update') {
      setState(prev => ({
        ...prev,
        ...data,
        lastUpdate: Date.now()
      }));
    }

    if (type === 'pad_state') {
      setState(prev => ({
        ...prev,
        удовольствие: data.pleasure ?? prev.удовольствие,
        возбуждение: data.arousal ?? prev.возбуждение,
        доминирование: data.dominance ?? prev.доминирование,
        любопытство: data.curiosity ?? prev.любопытство,
        уверенность: data.confidence ?? prev.уверенность,
        социальная_связь: data.social_connection ?? prev.социальная_связь,
        lastUpdate: Date.now()
      }));
    }
  }, [messages]);

  // Легкое естественное колебание значений когда нет обновлений
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now();
      if (now - state.lastUpdate > 3000) {
        setState(prev => ({
          ...prev,
          удовольствие: prev.удовольствие + (Math.random() - 0.5) * 0.02,
          возбуждение: prev.возбуждение + (Math.random() - 0.5) * 0.03,
          доминирование: prev.доминирование + (Math.random() - 0.5) * 0.015,
          любопытство: prev.любопытство + (Math.random() - 0.5) * 0.01,
          уверенность: prev.уверенность + (Math.random() - 0.5) * 0.01,
          социальная_связь: prev.социальная_связь + (Math.random() - 0.5) * 0.02
        }));
      }
    }, 500);

    return () => clearInterval(interval);
  }, [state.lastUpdate]);
  
  const mapping = {
    pleasure: Math.max(-1, Math.min(1, state.удовольствие ?? 0)),
    arousal: Math.max(-1, Math.min(1, state.возбуждение ?? 0)),
    dominance: Math.max(-1, Math.min(1, state.доминирование ?? 0)),
    curiosity: Math.max(0, Math.min(1, state.любопытство ?? 0.5)),
    confidence: Math.max(0, Math.min(1, state.уверенность ?? 0.5)),
    social_connection: Math.max(-1, Math.min(1, state.социальная_связь ?? 0)),
  };
  
  return (
    <Card hover className="h-full">
      <CardHeader>
        <CardTitle>PAD+ State</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {padDimensions.map((dim) => (
            <div key={dim.key}>
              <div className="text-xs text-text-secondary mb-1">{dim.label}</div>
              <ProgressBar
                value={mapping[dim.key] ?? 0}
                min={dim.min}
                max={dim.max}
                neutral={dim.neutral}
                color={dim.color}
              />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default PadWidget;