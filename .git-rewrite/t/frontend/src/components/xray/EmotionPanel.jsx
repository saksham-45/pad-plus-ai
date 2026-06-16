import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { motion } from 'framer-motion';

const emotionMoods = [
  { id: 'pleasure', label: 'Удовольствие', color: 'bg-pink-500', icon: '😊' },
  { id: 'arousal', label: 'Активность', color: 'bg-yellow-500', icon: '⚡' },
  { id: 'dominance', label: 'Уверенность', color: 'bg-green-500', icon: '💪' },
  { id: 'curiosity', label: 'Любопытство', color: 'bg-blue-500', icon: '🤔' },
  { id: 'uncertainty', label: 'Неопределенность', color: 'bg-red-500', icon: '❓' },
  { id: 'trust', label: 'Доверие', color: 'bg-purple-500', icon: '🤝' },
];

export function EmotionPanel({ emotions = {} }) {
  return (
    <Card className="w-full bg-gray-900/50 border-gray-700">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg text-white">
          😊 Эмоциональное состояние
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3">
          {emotionMoods.map((mood) => {
            const value = emotions[mood.id] ?? 0.5;
            const percent = Math.round(value * 100);
            
            return (
              <div key={mood.id} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1 text-gray-400">
                    <span>{mood.icon}</span>
                    {mood.label}
                  </span>
                  <span className="text-gray-300">{percent}%</span>
                </div>
                
                <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                  <motion.div
                    className={`h-full ${mood.color}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${percent}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}