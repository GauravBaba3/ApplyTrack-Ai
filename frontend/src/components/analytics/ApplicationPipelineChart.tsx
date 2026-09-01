import React, { useState } from 'react';
import { PieChart, Info } from 'lucide-react';
import { ApplicationStatus } from '../../types';

interface StatusData {
  status: string;
  count: number;
  color: string;
  twColor: string;
  barBg: string;
}

interface ApplicationPipelineChartProps {
  statusCounts: Record<string, number>;
  totalApplications: number;
}

const STATUS_CONFIG: Record<string, { color: string; twColor: string; barBg: string }> = {
  'Applied': { color: '#3b82f6', twColor: 'bg-blue-500', barBg: 'bg-blue-500/10' },
  'Under Review': { color: '#6366f1', twColor: 'bg-indigo-500', barBg: 'bg-indigo-500/10' },
  'Assessment': { color: '#a855f7', twColor: 'bg-purple-500', barBg: 'bg-purple-500/10' },
  'Interview': { color: '#10b981', twColor: 'bg-emerald-500', barBg: 'bg-emerald-500/10' },
  'Offer': { color: '#06b6d4', twColor: 'bg-cyan-500', barBg: 'bg-cyan-500/10' },
  'Rejected': { color: '#f43f5e', twColor: 'bg-rose-500', barBg: 'bg-rose-500/10' },
  'Withdrawn': { color: '#64748b', twColor: 'bg-slate-500', barBg: 'bg-slate-500/10' },
  'No Response': { color: '#94a3b8', twColor: 'bg-slate-400', barBg: 'bg-slate-400/10' },
  'Stale': { color: '#f59e0b', twColor: 'bg-amber-500', barBg: 'bg-amber-500/10' },
  'Ghosted': { color: '#78716c', twColor: 'bg-stone-500', barBg: 'bg-stone-500/10' },
  'Needs Review': { color: '#eab308', twColor: 'bg-yellow-500', barBg: 'bg-yellow-500/10' },
};

export default function ApplicationPipelineChart({
  statusCounts,
  totalApplications,
}: ApplicationPipelineChartProps) {
  const [hoveredStatus, setHoveredStatus] = useState<string | null>(null);

  // Filter out statuses with 0 counts for donut rendering, but keep non-zero ones
  const activeStatuses: StatusData[] = Object.entries(statusCounts)
    .filter(([_, count]) => count > 0)
    .map(([status, count]) => ({
      status,
      count,
      color: STATUS_CONFIG[status]?.color || '#94a3b8',
      twColor: STATUS_CONFIG[status]?.twColor || 'bg-slate-500',
      barBg: STATUS_CONFIG[status]?.barBg || 'bg-slate-500/10',
    }))
    .sort((a, b) => b.count - a.count);

  if (totalApplications === 0 || activeStatuses.length === 0) {
    return (
      <div className="glass-2 p-6 sm:p-7 rounded-2xl sm:rounded-3xl flex flex-col items-center justify-center text-center min-h-[300px]">
        <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-3">
          <PieChart size={22} />
        </div>
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">No Pipeline Data Yet</h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xs">
          Record or sync your first application to visualize your pipeline breakdown.
        </p>
      </div>
    );
  }

  // Calculate SVG donut segments
  const size = 180;
  const strokeWidth = 24;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  let accumulatedOffset = 0;

  const donutSegments = activeStatuses.map((item) => {
    const percentage = item.count / totalApplications;
    const strokeDasharray = `${percentage * circumference} ${circumference}`;
    const strokeDashoffset = -accumulatedOffset;
    accumulatedOffset += percentage * circumference;

    return {
      ...item,
      percentage: Math.round(percentage * 100),
      exactPct: (percentage * 100).toFixed(1),
      strokeDasharray,
      strokeDashoffset,
    };
  });

  const activeItem = hoveredStatus 
    ? donutSegments.find(s => s.status === hoveredStatus)
    : donutSegments[0];

  return (
    <div className="glass-2 p-4 sm:p-6 rounded-2xl sm:rounded-3xl space-y-4 sm:space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-section-title flex items-center gap-2">
            <PieChart size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
            Application Pipeline Breakdown
          </h2>
          <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Proportional distribution across all active and historical hiring stages.
          </p>
        </div>
        <div className="text-right shrink-0">
          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block">Total Volume</span>
          <span className="text-base sm:text-lg font-black text-slate-900 dark:text-slate-100">{totalApplications}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-5 sm:gap-6 items-center">
        {/* Left: Interactive SVG Donut Chart */}
        <div className="md:col-span-5 flex flex-col items-center justify-center relative py-2">
          <div className="relative w-[180px] h-[180px] sm:w-[200px] sm:h-[200px] flex items-center justify-center">
            <svg 
              className="w-full h-full -rotate-90 transform"
              viewBox={`0 0 ${size} ${size}`}
              aria-label="Application Status Donut Chart"
            >
              {/* Background ring */}
              <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                className="stroke-slate-200/60 dark:stroke-white/[0.06] fill-none"
                strokeWidth={strokeWidth}
              />
              {/* Donut Segments */}
              {donutSegments.map((segment) => {
                const isHovered = hoveredStatus === segment.status;
                return (
                  <circle
                    key={segment.status}
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    fill="none"
                    stroke={segment.color}
                    strokeWidth={isHovered ? strokeWidth + 4 : strokeWidth}
                    strokeDasharray={segment.strokeDasharray}
                    strokeDashoffset={segment.strokeDashoffset}
                    className="transition-all duration-300 cursor-pointer"
                    onMouseEnter={() => setHoveredStatus(segment.status)}
                    onMouseLeave={() => setHoveredStatus(null)}
                    style={{
                      opacity: hoveredStatus && !isHovered ? 0.45 : 1,
                      filter: isHovered ? `drop-shadow(0 0 6px ${segment.color}80)` : 'none'
                    }}
                  />
                );
              })}
            </svg>

            {/* Central Info Tooltip */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center px-4">
              <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-400 truncate max-w-[120px]">
                {activeItem?.status || 'Total'}
              </span>
              <span className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100 tracking-tight">
                {activeItem?.count || totalApplications}
              </span>
              <span className="text-[10px] sm:text-[11px] font-bold text-indigo-600 dark:text-indigo-400">
                {activeItem ? `${activeItem.exactPct}%` : '100%'}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Distribution List with Progress Bars */}
        <div className="md:col-span-7 space-y-2 sm:space-y-2.5 max-h-64 overflow-y-auto pr-1">
          {donutSegments.map((segment) => {
            const isHovered = hoveredStatus === segment.status;
            return (
              <div
                key={segment.status}
                onMouseEnter={() => setHoveredStatus(segment.status)}
                onMouseLeave={() => setHoveredStatus(null)}
                className={`p-2 sm:p-2.5 rounded-xl transition-all cursor-pointer ${
                  isHovered 
                    ? 'bg-white/80 dark:bg-white/[0.08] shadow-xs scale-[1.01]' 
                    : 'hover:bg-white/40 dark:hover:bg-white/[0.03]'
                }`}
              >
                <div className="flex items-center justify-between text-xs mb-1">
                  <div className="flex items-center gap-2 min-w-0">
                    <span 
                      className="w-2.5 h-2.5 rounded-full shrink-0" 
                      style={{ backgroundColor: segment.color }}
                    />
                    <span className={`font-bold truncate ${isHovered ? 'text-slate-900 dark:text-white' : 'text-slate-700 dark:text-slate-300'}`}>
                      {segment.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 text-xs">
                    <span className="font-bold text-slate-900 dark:text-slate-100">{segment.count}</span>
                    <span className="text-slate-400 text-[11px]">({segment.exactPct}%)</span>
                  </div>
                </div>
                {/* Horizontal Progress Bar */}
                <div className={`h-1.5 w-full rounded-full ${segment.barBg} overflow-hidden`}>
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ 
                      width: `${segment.percentage}%`,
                      backgroundColor: segment.color 
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
