import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export function MetricsWidget({ data = [], title = 'Live Metrics' }) {
  // Генерируем данные если их нет
  const chartData = data.length > 0 ? data : Array.from({ length: 20 }, (_, i) => ({
    time: i,
    value: Math.random() * 0.5 + 0.25,
  }));
  
  return (
    <Card hover className="h-full">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={150}>
          <LineChart data={chartData}>
            <XAxis 
              dataKey="time" 
              hide 
              tick={{ fill: '#737373', fontSize: 10 }}
            />
            <YAxis 
              hide 
              domain={[0, 1]}
              tick={{ fill: '#737373', fontSize: 10 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#141414',
                border: '1px solid #262626',
                borderRadius: '8px',
                color: '#f5f5f5',
              }}
              labelFormatter={(value) => `T+${value}s`}
              formatter={(value) => [value.toFixed(3), 'Value']}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#7c3aed"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#7c3aed' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export default MetricsWidget;