import React from 'react';
import { LucideIcon } from 'lucide-react';

interface AnalyticsMetricCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: LucideIcon;
  color: 'blue' | 'purple' | 'green' | 'cyan' | 'red' | 'amber';
  badge?: string;
  badgeType?: 'positive' | 'neutral' | 'accent';
}

const colorStyles = {
  blue: {
    iconBg: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
    valColor: 'text-slate-900 dark:text-slate-100',
    accentBar: 'bg-blue-500',
  },
  purple: {
    iconBg: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20',
    valColor: 'text-purple-600 dark:text-purple-400',
    accentBar: 'bg-purple-500',
  },
  green: {
    iconBg: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
    valColor: 'text-emerald-600 dark:text-emerald-400',
    accentBar: 'bg-emerald-500',
  },
  cyan: {
    iconBg: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20',
    valColor: 'text-cyan-600 dark:text-cyan-400',
    accentBar: 'bg-cyan-500',
  },
  red: {
    iconBg: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20',
    valColor: 'text-rose-600 dark:text-rose-400',
    accentBar: 'bg-rose-500',
  },
  amber: {
    iconBg: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
    valColor: 'text-amber-600 dark:text-amber-400',
    accentBar: 'bg-amber-500',
  },
};

export default function AnalyticsMetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
  badge,
  badgeType = 'positive',
}: AnalyticsMetricCardProps) {
  const style = colorStyles[color];

  return (
    <div className="glass-2 p-4 sm:p-5 rounded-2xl sm:rounded-3xl relative overflow-hidden flex flex-col justify-between hover:border-indigo-500/30 transition-all group">
      {/* Top accent glow line */}
      <div className={`absolute top-0 left-0 right-0 h-0.5 ${style.accentBar} opacity-60 group-hover:opacity-100 transition-opacity`} />

      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 truncate">
            {title}
          </span>
          <div className={`w-7 h-7 sm:w-8 sm:h-8 rounded-xl flex items-center justify-center border shadow-xs shrink-0 ${style.iconBg}`}>
            <Icon size={15} />
          </div>
        </div>

        <div className="flex items-baseline gap-2 flex-wrap">
          <span className={`text-xl sm:text-2xl lg:text-3xl font-black tracking-tight ${style.valColor}`}>
            {value}
          </span>
          {badge && (
            <span
              className={`text-[10px] sm:text-[11px] font-bold px-2 py-0.5 rounded-full border ${
                badgeType === 'positive'
                  ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20'
                  : badgeType === 'accent'
                  ? 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border-indigo-500/20'
                  : 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20'
              }`}
            >
              {badge}
            </span>
          )}
        </div>
      </div>

      <div className="pt-2 sm:pt-3 mt-1 border-t border-slate-100 dark:border-white/[0.05]">
        <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium truncate">
          {subtitle}
        </p>
      </div>
    </div>
  );
}
