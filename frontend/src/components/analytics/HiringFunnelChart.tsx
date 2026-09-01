import React from 'react';
import { Layers, ArrowRight, CheckCircle2, XCircle, Award } from 'lucide-react';

interface HiringFunnelChartProps {
  totalApplications: number;
  applied: number;
  underReview?: number;
  assessment: number;
  interview: number;
  offer: number;
  rejected: number;
  interviewRate?: number;
  offerRate?: number;
}

export default function HiringFunnelChart({
  totalApplications,
  applied,
  underReview = 0,
  assessment,
  interview,
  offer,
  rejected,
  interviewRate = 0,
  offerRate = 0,
}: HiringFunnelChartProps) {
  const stages = [
    {
      name: 'Applied',
      count: applied,
      color: '#3b82f6',
      twBg: 'bg-blue-500',
      lightBg: 'bg-blue-500/10 border-blue-500/20 text-blue-700 dark:text-blue-300',
      barTrack: 'bg-blue-500/15',
    },
    {
      name: 'Assessment',
      count: assessment,
      color: '#a855f7',
      twBg: 'bg-purple-500',
      lightBg: 'bg-purple-500/10 border-purple-500/20 text-purple-700 dark:text-purple-300',
      barTrack: 'bg-purple-500/15',
    },
    {
      name: 'Interview',
      count: interview,
      color: '#10b981',
      twBg: 'bg-emerald-500',
      lightBg: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-700 dark:text-emerald-300',
      barTrack: 'bg-emerald-500/15',
    },
    {
      name: 'Offer',
      count: offer,
      color: '#06b6d4',
      twBg: 'bg-cyan-500',
      lightBg: 'bg-cyan-500/10 border-cyan-500/20 text-cyan-700 dark:text-cyan-300',
      barTrack: 'bg-cyan-500/15',
    },
    {
      name: 'Rejected',
      count: rejected,
      color: '#f43f5e',
      twBg: 'bg-rose-500',
      lightBg: 'bg-rose-500/10 border-rose-500/20 text-rose-700 dark:text-rose-300',
      barTrack: 'bg-rose-500/15',
    },
  ];

  const maxCount = Math.max(...stages.map(s => s.count), totalApplications, 1);

  return (
    <div className="glass-2 p-4 sm:p-6 rounded-2xl sm:rounded-3xl space-y-4 sm:space-y-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-section-title flex items-center gap-2">
            <Layers size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
            Hiring Stage Funnel & Outcomes
          </h2>
          <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Stage-by-stage progression comparison from initial submission to final outcome.
          </p>
        </div>
      </div>

      {/* Stage Progression Bars */}
      <div className="space-y-3 pt-1">
        {stages.map((stage) => {
          const widthPct = maxCount > 0 ? Math.max((stage.count / maxCount) * 100, stage.count > 0 ? 6 : 0) : 0;
          const shareOfTotal = totalApplications > 0 ? ((stage.count / totalApplications) * 100).toFixed(1) : '0';

          return (
            <div key={stage.name} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span 
                    className="w-2.5 h-2.5 rounded-full shrink-0" 
                    style={{ backgroundColor: stage.color }}
                  />
                  <span className="font-bold text-slate-800 dark:text-slate-200 text-xs">
                    {stage.name}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs font-semibold">
                  <span className="text-slate-900 dark:text-slate-100 font-bold">{stage.count}</span>
                  <span className="text-slate-400 text-[11px]">({shareOfTotal}%)</span>
                </div>
              </div>

              {/* Progress track */}
              <div className={`h-3 w-full rounded-full ${stage.barTrack} overflow-hidden`}>
                <div
                  className="h-full rounded-full transition-all duration-600 ease-out"
                  style={{
                    width: `${widthPct}%`,
                    backgroundColor: stage.color,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Conversion Rate Highlight Cards */}
      <div className="grid grid-cols-2 gap-2.5 pt-3 border-t border-slate-100 dark:border-white/[0.05]">
        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex flex-col justify-between">
          <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-300">
            Interview Rate
          </span>
          <div className="flex items-baseline gap-1 mt-1">
            <span className="text-lg sm:text-xl font-black text-emerald-600 dark:text-emerald-400">
              {interviewRate}%
            </span>
            <span className="text-[10px] text-slate-500 dark:text-slate-400">of applied</span>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex flex-col justify-between">
          <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-cyan-700 dark:text-cyan-300">
            Offer Rate
          </span>
          <div className="flex items-baseline gap-1 mt-1">
            <span className="text-lg sm:text-xl font-black text-cyan-600 dark:text-cyan-400">
              {offerRate}%
            </span>
            <span className="text-[10px] text-slate-500 dark:text-slate-400">of applied</span>
          </div>
        </div>
      </div>
    </div>
  );
}
