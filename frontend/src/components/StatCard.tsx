import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  icon: LucideIcon;
  value: string | number;
  label?: string;
  title?: string;
  subtitle?: string;
  trend?: string;
  trendUp?: boolean;
  colorClass?: string;
  color?: 'blue' | 'green' | 'orange' | 'purple' | 'cyan' | 'rose' | string;
}

const colorMap: Record<string, { iconBg: string; iconColor: string }> = {
  blue: { iconBg: 'bg-blue-500/10 dark:bg-blue-500/15', iconColor: 'text-blue-600 dark:text-blue-400' },
  green: { iconBg: 'bg-emerald-500/10 dark:bg-emerald-500/15', iconColor: 'text-emerald-600 dark:text-emerald-400' },
  orange: { iconBg: 'bg-amber-500/10 dark:bg-amber-500/15', iconColor: 'text-amber-600 dark:text-amber-400' },
  purple: { iconBg: 'bg-purple-500/10 dark:bg-purple-500/15', iconColor: 'text-purple-600 dark:text-purple-400' },
  cyan: { iconBg: 'bg-cyan-500/10 dark:bg-cyan-500/15', iconColor: 'text-cyan-600 dark:text-cyan-400' },
  rose: { iconBg: 'bg-rose-500/10 dark:bg-rose-500/15', iconColor: 'text-rose-600 dark:text-rose-400' },
};

export default function StatCard({ 
  icon: Icon, 
  value, 
  label, 
  title,
  subtitle,
  trend, 
  trendUp = true,
  colorClass,
  color = 'blue'
}: StatCardProps) {
  const displayLabel = title || label || '';
  const styling = colorMap[color] || colorMap.blue;

  return (
    <div className="card p-5 sm:p-6 transition-all duration-200 hover:shadow-md hover:border-slate-300 dark:hover:border-slate-700/80 group">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center transition-transform group-hover:scale-105 duration-200 ${styling.iconBg} ${styling.iconColor}`}>
          <Icon size={22} strokeWidth={2} />
        </div>
        {trend && (
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
            trendUp 
              ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60' 
              : 'bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60'
          }`}>
            {trend}
          </span>
        )}
      </div>
      <div>
        <h4 className="text-3xl font-black text-slate-900 dark:text-slate-100 tracking-tight">{value}</h4>
        <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mt-1.5">{displayLabel}</p>
        {subtitle && <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  );
}
