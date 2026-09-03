import React from 'react';
import { LucideIcon } from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string | number;
  change?: string;
  trend?: 'up' | 'down' | 'neutral';
  icon: LucideIcon;
  color?: string;
}

export const KPICard: React.FC<KPICardProps> = ({ 
  title, 
  value, 
  change, 
  trend, 
  icon: Icon,
  color = "blue" 
}) => {
  const colorMap: Record<string, string> = {
    blue: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    red: "text-red-400 bg-red-500/10 border-red-500/20",
    orange: "text-orange-400 bg-orange-500/10 border-orange-500/20",
    green: "text-green-400 bg-green-500/10 border-green-500/20",
  };

  return (
    <div className={`p-4 rounded-xl border ${colorMap[color]} flex flex-col gap-2 relative overflow-hidden group hover:bg-opacity-20 transition-all duration-300`}>
      <div className="flex justify-between items-start">
        <span className="text-[10px] font-bold uppercase tracking-wider opacity-60">
          {title}
        </span>
        <Icon size={16} className="opacity-60 group-hover:scale-110 transition-transform" />
      </div>
      
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold tracking-tight">{value}</span>
        {change && (
          <span className={`text-[10px] font-medium ${trend === 'up' ? 'text-green-400' : 'text-red-400'}`}>
            {change}
          </span>
        )}
      </div>

      {/* Decorative background glow */}
      <div className={`absolute -right-4 -bottom-4 w-16 h-16 blur-2xl rounded-full opacity-20 ${colorMap[color].split(' ')[0].replace('text', 'bg')}`} />
    </div>
  );
};
