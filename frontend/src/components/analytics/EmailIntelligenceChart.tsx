import React from 'react';
import { Mail, CheckCircle2, AlertCircle, EyeOff, ShieldAlert, Sparkles, Filter } from 'lucide-react';
import { ProcessedEmail } from '../../types';

interface EmailIntelligenceChartProps {
  emails: ProcessedEmail[];
}

export default function EmailIntelligenceChart({ emails }: EmailIntelligenceChartProps) {
  if (emails.length === 0) {
    return (
      <div className="glass-2 p-6 sm:p-7 rounded-2xl sm:rounded-3xl flex flex-col items-center justify-center text-center min-h-[280px]">
        <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-3">
          <Mail size={22} />
        </div>
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">No Email Intelligence Yet</h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xs">
          Sync your Gmail inbox to view email processing status and AI priority triage distributions.
        </p>
      </div>
    );
  }

  const total = emails.length;
  const processed = emails.filter((e) => e.processing_status === 'processed').length;
  const needsReview = emails.filter((e) => e.processing_status === 'needs_review').length;
  const ignored = emails.filter((e) => e.processing_status === 'ignored').length;
  const detected = emails.filter((e) => e.processing_status === 'detected').length;

  // Priority counts
  const p1 = emails.filter((e) => e.triage_priority === 'P1').length;
  const p2 = emails.filter((e) => e.triage_priority === 'P2' || !e.triage_priority).length;
  const p3 = emails.filter((e) => e.triage_priority === 'P3').length;

  const priorityTotal = p1 + p2 + p3;

  return (
    <div className="glass-2 p-4 sm:p-6 rounded-2xl sm:rounded-3xl space-y-5 sm:space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-section-title flex items-center gap-2">
            <Mail size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
            Email & AI Intelligence Cascade
          </h2>
          <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Recruiter communications parsing efficiency and triage priority distribution.
          </p>
        </div>
        <div className="text-right shrink-0">
          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block">Monitored</span>
          <span className="text-base sm:text-lg font-black text-slate-900 dark:text-slate-100">{total}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        {/* Left: Processing Status Breakdown */}
        <div className="space-y-3">
          <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
            Ingestion Pipeline Status
          </span>

          <div className="space-y-2 text-xs">
            <div className="space-y-1">
              <div className="flex justify-between font-semibold">
                <span className="text-emerald-700 dark:text-emerald-300 flex items-center gap-1.5">
                  <CheckCircle2 size={12} className="text-emerald-500" /> Auto-Processed
                </span>
                <span className="text-slate-700 dark:text-slate-300 font-bold">
                  {processed} ({total > 0 ? ((processed / total) * 100).toFixed(0) : 0}%)
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-emerald-500/15 overflow-hidden">
                <div 
                  className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                  style={{ width: `${total > 0 ? (processed / total) * 100 : 0}%` }}
                />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between font-semibold">
                <span className="text-amber-700 dark:text-amber-300 flex items-center gap-1.5">
                  <AlertCircle size={12} className="text-amber-500" /> Needs Review
                </span>
                <span className="text-slate-700 dark:text-slate-300 font-bold">
                  {needsReview} ({total > 0 ? ((needsReview / total) * 100).toFixed(0) : 0}%)
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-amber-500/15 overflow-hidden">
                <div 
                  className="h-full bg-amber-500 rounded-full transition-all duration-500"
                  style={{ width: `${total > 0 ? (needsReview / total) * 100 : 0}%` }}
                />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between font-semibold">
                <span className="text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                  <EyeOff size={12} /> Ignored / Non-Job
                </span>
                <span className="text-slate-700 dark:text-slate-300 font-bold">
                  {ignored} ({total > 0 ? ((ignored / total) * 100).toFixed(0) : 0}%)
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-400/15 overflow-hidden">
                <div 
                  className="h-full bg-slate-400 rounded-full transition-all duration-500"
                  style={{ width: `${total > 0 ? (ignored / total) * 100 : 0}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right: AI Triage Priority Distribution */}
        <div className="space-y-3">
          <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
            AI Triage Priority Distribution
          </span>

          <div className="space-y-2.5">
            {/* P1 Urgent */}
            <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="px-1.5 py-0.5 rounded text-[10px] font-black uppercase bg-rose-500 text-white">
                  P1
                </span>
                <span className="font-bold text-rose-800 dark:text-rose-300">
                  Urgent / Interviews & Offers
                </span>
              </div>
              <span className="font-black text-rose-700 dark:text-rose-300 text-sm">
                {p1}
              </span>
            </div>

            {/* P2 Medium */}
            <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="px-1.5 py-0.5 rounded text-[10px] font-black uppercase bg-amber-500 text-white">
                  P2
                </span>
                <span className="font-bold text-amber-800 dark:text-amber-300">
                  Standard Status Updates
                </span>
              </div>
              <span className="font-black text-amber-700 dark:text-amber-300 text-sm">
                {p2}
              </span>
            </div>

            {/* P3 Low */}
            <div className="p-2.5 rounded-xl bg-slate-500/10 border border-slate-500/20 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="px-1.5 py-0.5 rounded text-[10px] font-black uppercase bg-slate-500 text-white">
                  P3
                </span>
                <span className="font-bold text-slate-700 dark:text-slate-300">
                  Confirmations & Newsletters
                </span>
              </div>
              <span className="font-black text-slate-700 dark:text-slate-300 text-sm">
                {p3}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
