import { Card, CardContent } from './ui/Card';

export function KpiCard({ label, value, icon, color = 'text-white', subtext = '' }) {
  return (
    <Card className="bg-[#111827] border border-[#1F2937]">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-400">{label}</p>
            <p className={`text-lg font-medium ${color}`}>{value}</p>
            {subtext && <p className="text-xs text-gray-500 mt-1">{subtext}</p>}
          </div>
          {icon && (
            <div className={`w-8 h-8 rounded-lg bg-[#1F2937] flex items-center justify-center`}>
              {icon}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}