import React from 'react';
import { Globe, ArrowUpRight } from 'lucide-react';
import { Application } from '../../types';

interface SourceDistributionChartProps {
  applications: Application[];
}

const SOURCE_COLORS: Record<string, { color: string; bg: string }> = {
  'LinkedIn': { color: '#0a66c2', bg: 'bg-sky-500/10 text-sky-600 dark:text-sky-400' },
  'Indeed': { color: '#2164f3', bg: 'bg-blue-500/10 text-blue-600 dark:text-blue-400' },
  'Company Website': { color: '#8b5cf6', bg: 'bg-purple-500/10 text-purple-600 dark:text-purple-400' },
  'Naukri': { color: '#f59e0b', bg: 'bg-amber-500/10 text-amber-600 dark:text-amber-400' },
  'Wellfound': { color: '#ef4444', bg: 'bg-red-500/10 text-red-600 dark:text-red-400' },
  'Referral': { color: '#10b981', bg: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' },
  'Email': { color: '#06b6d4', bg: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400' },
  'Other': { color: '#64748b', bg: 'bg-slate-500/10 text-slate-600 dark:text-slate-400' },
};

export default function SourceDistributionChart({ applications }: SourceDistributionChartProps) {
  const total = applications.length;

  if (total === 0) {
    return null;
  }

  // Count by source
  const counts: Record<string, number> = {};
  applications.forEach((app) => {
    const src = app.source || 'Direct';
    counts[src] = (counts[src] || 0) + 1;
  });

  const sortedSources = Object.entries(counts)
    .map(([source, count]) => ({
      source,
      count,
      pct: ((count / total) * 100).toFixed(0),
      exactPct: ((count / total) * 100).toFixed(1),
      color: SOURCE_COLORS[source]?.color || '#6366f1',
    }))
    .sort((a, b) => b.count - a.count);

  return (
    <div className="glass-2 p-4 sm:p-6 rounded-2xl sm:rounded-3xl space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-section-title flex items-center gap-2">
            <Globe size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
            Application Channel Distribution
          </h2>
          <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Share of applications submitted across job portals, referrals, and direct careers pages.
          </p>
        </div>
      </div>

      <div className="space-y-3 pt-1">
        {sortedSources.map((item) => (
          <div key={item.source} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span 
                  className="w-2.5 h-2.5 rounded-full shrink-0" 
                  style={{ backgroundColor: item.color }} 
                />
                <span className="font-bold text-slate-800 dark:text-slate-200">
                  {item.source}
                </span>
              </div>
              <div className="flex items-center gap-2 font-semibold text-xs">
                <span className="text-slate-900 dark:text-slate-100 font-bold">{item.count}</span>
                <span className="text-slate-400 text-[11px]">({item.exactPct}%)</span>
              </div>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-white/[0.04] overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${item.pct}%`,
                  backgroundColor: item.color,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
