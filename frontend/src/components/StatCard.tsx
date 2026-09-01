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

const colorMap: Record<string, { iconBg: string; iconColor: string; glow: string }> = {
  blue: {
    iconBg: 'bg-blue-500/10 dark:bg-blue-500/15 border-blue-500/20',
    iconColor: 'text-blue-600 dark:text-blue-400',
    glow: 'group-hover:border-blue-500/30'
  },
  green: {
    iconBg: 'bg-emerald-500/10 dark:bg-emerald-500/15 border-emerald-500/20',
    iconColor: 'text-emerald-600 dark:text-emerald-400',
    glow: 'group-hover:border-emerald-500/30'
  },
  orange: {
    iconBg: 'bg-amber-500/10 dark:bg-amber-500/15 border-amber-500/20',
    iconColor: 'text-amber-600 dark:text-amber-400',
    glow: 'group-hover:border-amber-500/30'
  },
  purple: {
    iconBg: 'bg-purple-500/10 dark:bg-purple-500/15 border-purple-500/20',
    iconColor: 'text-purple-600 dark:text-purple-400',
    glow: 'group-hover:border-purple-500/30'
  },
  cyan: {
    iconBg: 'bg-cyan-500/10 dark:bg-cyan-500/15 border-cyan-500/20',
    iconColor: 'text-cyan-600 dark:text-cyan-400',
    glow: 'group-hover:border-cyan-500/30'
  },
  rose: {
    iconBg: 'bg-rose-500/10 dark:bg-rose-500/15 border-rose-500/20',
    iconColor: 'text-rose-600 dark:text-rose-400',
    glow: 'group-hover:border-rose-500/30'
  },
};

export default function StatCard({ 
  icon: Icon, 
  value, 
  label, 
  title,
  subtitle,
  trend, 
  trendUp = true,
  color = 'blue'
}: StatCardProps) {
  const displayLabel = title || label || '';
  const styling = colorMap[color] || colorMap.blue;

  return (
    <div className={`glass-card p-5 sm:p-6 group relative overflow-hidden ${styling.glow}`}>
      <div className="flex items-center justify-between mb-4">
        <div className={`w-11 h-11 rounded-2xl border flex items-center justify-center transition-transform group-hover:scale-105 duration-200 backdrop-blur-md ${styling.iconBg} ${styling.iconColor}`}>
          <Icon size={20} strokeWidth={2.2} />
        </div>
        {trend && (
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold backdrop-blur-md ${
            trendUp 
              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20' 
              : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'
          }`}>
            {trend}
          </span>
        )}
      </div>
      <div>
        <h4 className="text-3xl font-black text-slate-900 dark:text-slate-100 tracking-tight">{value}</h4>
        <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mt-1.5">{displayLabel}</p>
        {subtitle && <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5 font-medium">{subtitle}</p>}
      </div>
    </div>
  );
}

