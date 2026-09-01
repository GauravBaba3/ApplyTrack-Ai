import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  RefreshCw, Briefcase, Mail, CheckCircle2, XCircle, ChevronRight, 
  Activity, TrendingUp, Search, UserCheck, Loader2, Sparkles, Clock, 
  ArrowUpRight, Award, Plus, Layers, AlertCircle, ShieldCheck
} from 'lucide-react';
import { applicationApi, analyticsApi } from '../services/api';
import { ApplicationStats, UserAnalytics } from '../types';
import { useSync } from '../context/SyncContext';
import StatusBadge from '../components/StatusBadge';
import EmptyState from '../components/EmptyState';
import { SkeletonCard, SkeletonTableRow } from '../components/LoadingSkeleton';
import { cacheService, CACHE_TTL } from '../services/cacheService';

export default function DashboardPage() {
  const [stats, setStats] = useState<ApplicationStats | null>(() => 
    cacheService.get<ApplicationStats>('dashboard:stats', CACHE_TTL.DASHBOARD)
  );
  const [analytics, setAnalytics] = useState<UserAnalytics | null>(() => 
    cacheService.get<UserAnalytics>('dashboard:analytics', CACHE_TTL.DASHBOARD)
  );
  const [recentActivity, setRecentActivity] = useState<any[]>(() => 
    cacheService.get<any[]>('dashboard:recent', CACHE_TTL.DASHBOARD) || []
  );
  
  const hasCachedData = Boolean(stats || analytics);
  const [loading, setLoading] = useState(!hasCachedData);

  // Consume global background sync
  const { isSyncing, syncStatus, progress, error: syncError, dataVersion, triggerSync } = useSync();

  const fetchData = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const [statsRes, analyticsRes, appsRes] = await Promise.all([
        applicationApi.getStats().catch(() => ({ data: null })),
        analyticsApi.get().catch(() => ({ data: null })),
        applicationApi.getAll({ ordering: '-updated_at', limit: 6 }).catch(() => ({ data: { results: [] } }))
      ]);
      
      if (statsRes.data) {
        setStats(statsRes.data);
        cacheService.set('dashboard:stats', statsRes.data);
      }
      if (analyticsRes.data) {
        setAnalytics(analyticsRes.data);
        cacheService.set('dashboard:analytics', analyticsRes.data);
      }
      if (appsRes.data?.results) {
        setRecentActivity(appsRes.data.results);
        cacheService.set('dashboard:recent', appsRes.data.results);
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(hasCachedData);
  }, [fetchData, dataVersion]);

  const handleSync = () => {
    triggerSync(true);
  };

  const cumulativeStats = progress?.cumulative || {
    emails_scanned: progress?.emails_scanned || 0,
    job_related_emails: progress?.job_related_emails || 0,
    applications_updated: progress?.applications_updated || 0,
    new_applications: progress?.new_applications || 0,
  };

  const totalApps = stats?.total_applications || 0;
  const appliedCount = stats?.applied || 0;
  const assessmentCount = stats?.assessment || 0;
  const interviewCount = stats?.interview || 0;
  const offerCount = stats?.offer || 0;
  const rejectedCount = stats?.rejected || 0;
  const needsReviewCount = (stats as any)?.needs_review || 0;

  return (
    <div className="space-y-4 sm:space-y-6 pb-12 animate-fade-in w-full max-w-full min-w-0">
      {/* =========================================================================
          COMMAND CENTER HERO BANNER
          ========================================================================= */}
      <div className="glass-2 p-4 sm:p-7 rounded-2xl sm:rounded-3xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-bl from-indigo-500/15 via-blue-500/10 to-transparent rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1.5 min-w-0">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2 sm:px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 text-[11px] sm:text-xs font-bold backdrop-blur-md">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Active Mailbox Monitoring
              </span>
            </div>
            <h1 className="text-page-title text-slate-900 dark:text-slate-100">
              Command Center
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-xl font-normal leading-relaxed">
              Autonomous recruiter communication parser and hiring stage synchronizer.
            </p>
          </div>

          {/* Top Quick Actions */}
          <div className="flex items-center gap-2.5 w-full sm:w-auto self-stretch sm:self-auto shrink-0">
            <button
              onClick={handleSync}
              disabled={isSyncing}
              className="btn btn-primary text-xs sm:text-sm flex-1 sm:flex-initial shadow-md shadow-indigo-500/25 justify-center"
            >
              <RefreshCw className={isSyncing ? 'animate-spin' : ''} size={15} />
              <span>{isSyncing ? 'Syncing...' : 'Sync Gmail'}</span>
            </button>

            <Link
              to="/applications?add=true"
              className="btn btn-secondary text-xs sm:text-sm flex-1 sm:flex-initial shadow-sm justify-center"
            >
              <Plus size={15} />
              <span>Add Application</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Sync In-Progress Banner */}
      {isSyncing && (
        <div className="glass-2 p-3.5 sm:p-5 rounded-2xl border-indigo-500/30 bg-indigo-500/5 space-y-2.5 sm:space-y-3 animate-fade-in">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-indigo-600/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0">
                <Loader2 className="animate-spin" size={16} />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold text-indigo-700 dark:text-indigo-300 truncate">
                  {syncStatus === 'running' ? 'Scanning Gmail Mailbox...' : 'Ingesting Messages & Updating Pipeline...'}
                </p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate mt-0.5">
                  Importing message metadata and queuing for classification.
                </p>
              </div>
            </div>
          </div>
          {cumulativeStats.emails_scanned > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-indigo-500/15 text-center">
              <div className="p-2 rounded-xl bg-white/40 dark:bg-white/[0.03]">
                <p className="text-[10px] text-slate-500 uppercase font-semibold">Emails Scanned</p>
                <p className="text-sm font-bold text-slate-900 dark:text-slate-100">{cumulativeStats.emails_scanned}</p>
              </div>
              <div className="p-2 rounded-xl bg-white/40 dark:bg-white/[0.03]">
                <p className="text-[10px] text-slate-500 uppercase font-semibold">Job Related</p>
                <p className="text-sm font-bold text-indigo-600 dark:text-indigo-400">{cumulativeStats.job_related_emails}</p>
              </div>
              <div className="p-2 rounded-xl bg-white/40 dark:bg-white/[0.03]">
                <p className="text-[10px] text-slate-500 uppercase font-semibold">Updated</p>
                <p className="text-sm font-bold text-emerald-600 dark:text-emerald-400">{cumulativeStats.applications_updated}</p>
              </div>
              <div className="p-2 rounded-xl bg-white/40 dark:bg-white/[0.03]">
                <p className="text-[10px] text-slate-500 uppercase font-semibold">New Opportunities</p>
                <p className="text-sm font-bold text-cyan-600 dark:text-cyan-400">{cumulativeStats.new_applications}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Human Review Banner if items pending */}
      {needsReviewCount > 0 && (
        <div className="glass-2 p-4 sm:p-5 rounded-2xl sm:rounded-3xl border-amber-500/35 bg-amber-500/[0.05] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4 animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-2xl bg-amber-500/15 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0">
              <AlertCircle size={18} />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-xs sm:text-sm font-bold text-slate-900 dark:text-slate-100">
                  {needsReviewCount} {needsReviewCount === 1 ? 'Email Requires' : 'Emails Require'} Human Verification
                </h3>
                <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/20 text-amber-800 dark:text-amber-300">
                  Action Needed
                </span>
              </div>
              <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                The AI detected ambiguous recruiter updates that need your confirmation.
              </p>
            </div>
          </div>
          <Link
            to="/emails?status=needs_review"
            className="btn btn-secondary text-xs px-3 py-1.5 shrink-0 self-stretch sm:self-auto text-amber-700 dark:text-amber-300 border-amber-500/30 justify-center"
          >
            <span>Review Items</span>
            <ChevronRight size={14} />
          </Link>
        </div>
      )}

      {/* =========================================================================
          KEY METRICS HIERARCHY
          ========================================================================= */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-5">
        {/* Large Highlighted Command Card */}
        <div className="sm:col-span-2 glass-2 p-4 sm:p-6 rounded-2xl sm:rounded-3xl flex flex-col justify-between relative overflow-hidden">
          <div className="space-y-1">
            <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 flex items-center gap-1.5">
              <Briefcase size={13} className="text-indigo-600 dark:text-indigo-400" />
              Total Tracked Pipeline
            </span>
            <div className="flex items-baseline gap-2.5 flex-wrap">
              <span className="text-stat text-slate-900 dark:text-slate-100">
                {totalApps}
              </span>
              <span className="text-[11px] sm:text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
                {analytics?.interview_rate || 0}% Interview Rate
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-normal">
              Active job applications managed across all interview stages.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-4 mt-3 border-t border-slate-100 dark:border-white/[0.06]">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400">Response Rate</span>
              <p className="text-sm sm:text-base font-black text-slate-800 dark:text-slate-200">
                {analytics?.response_rate || 0}%
              </p>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400">Avg Response Time</span>
              <p className="text-sm sm:text-base font-black text-slate-800 dark:text-slate-200">
                {analytics?.avg_days_to_response || 0} days
              </p>
            </div>
          </div>
        </div>

        {/* 2 Supporting Metric Cards */}
        <div className="glass-2 p-4 sm:p-6 rounded-2xl sm:rounded-3xl flex flex-col justify-between">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                Interviews
              </span>
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold text-xs">
                <Award size={15} />
              </div>
            </div>
            <p className="text-2xl sm:text-3xl font-black text-emerald-600 dark:text-emerald-400 tracking-tight">
              {interviewCount}
            </p>
          </div>
          <div className="pt-2 sm:pt-3 border-t border-slate-100 dark:border-white/[0.06]">
            <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 font-medium">
              Rounds in progress
            </p>
          </div>
        </div>

        <div className="glass-2 p-4 sm:p-6 rounded-2xl sm:rounded-3xl flex flex-col justify-between">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                Offers Received
              </span>
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 flex items-center justify-center font-bold text-xs">
                <Sparkles size={15} />
              </div>
            </div>
            <p className="text-2xl sm:text-3xl font-black text-cyan-600 dark:text-cyan-400 tracking-tight">
              {offerCount}
            </p>
          </div>
          <div className="pt-2 sm:pt-3 border-t border-slate-100 dark:border-white/[0.06]">
            <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 font-medium">
              Active formal proposals
            </p>
          </div>
        </div>
      </div>

      {/* =========================================================================
          PIPELINE STAGE DISTRIBUTION
          ========================================================================= */}
      <div className="glass-2 p-4 sm:p-6 rounded-2xl sm:rounded-3xl space-y-4">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-section-title flex items-center gap-2">
              <Layers size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
              Pipeline Funnel
            </h2>
            <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Live breakdown across key hiring milestones.
            </p>
          </div>
          <Link to="/applications" className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline inline-flex items-center gap-1 shrink-0">
            <span>View All</span>
            <ChevronRight size={14} />
          </Link>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 sm:gap-3">
          {[
            { label: 'Applied', count: appliedCount, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
            { label: 'Assessment', count: assessmentCount, color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-500/10 border-purple-500/20' },
            { label: 'Interview', count: interviewCount, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
            { label: 'Offer', count: offerCount, color: 'text-cyan-600 dark:text-cyan-400', bg: 'bg-cyan-500/10 border-cyan-500/20' },
            { label: 'Rejected', count: rejectedCount, color: 'text-rose-600 dark:text-rose-400', bg: 'bg-rose-500/10 border-rose-500/20' },
          ].map((stage, idx) => (
            <Link
              key={idx}
              to={`/applications?status=${stage.label}`}
              className={`p-3 sm:p-4 rounded-xl sm:rounded-2xl border ${stage.bg} hover:scale-[1.02] active:scale-[0.98] transition-transform`}
            >
              <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 block truncate">
                {stage.label}
              </span>
              <p className={`text-xl sm:text-2xl font-black ${stage.color} mt-0.5`}>
                {stage.count}
              </p>
            </Link>
          ))}
        </div>
      </div>

      {/* =========================================================================
          RECENT ACTIVITY: DESKTOP TABLE + MOBILE COMPACT CARDS
          ========================================================================= */}
      <div className="glass-2 rounded-2xl sm:rounded-3xl overflow-hidden w-full">
        <div className="p-4 sm:p-6 border-b border-slate-100 dark:border-white/[0.06] flex items-center justify-between">
          <div>
            <h2 className="text-section-title flex items-center gap-2">
              <Activity size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
              Recent Activity
            </h2>
            <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Latest applications and status progressions.
            </p>
          </div>
          <Link
            to="/applications"
            className="btn btn-secondary text-xs shadow-sm py-1.5 px-3"
          >
            <span>Explore All</span>
            <ChevronRight size={14} />
          </Link>
        </div>

        {loading ? (
          <div className="p-4 sm:p-6 space-y-3">
            <div className="md:hidden space-y-3">
              <SkeletonCard />
              <SkeletonCard />
            </div>
            <div className="hidden md:block">
              <table className="w-full">
                <tbody>
                  <SkeletonTableRow />
                  <SkeletonTableRow />
                </tbody>
              </table>
            </div>
          </div>
        ) : recentActivity.length === 0 ? (
          <div className="p-8 sm:p-12">
            <EmptyState
              icon={Briefcase}
              title="No application activity yet"
              description="Sync your Gmail mailbox or manually record your first application to see activity here."
              action={
                <button onClick={handleSync} className="btn btn-primary text-xs shadow-sm">
                  <RefreshCw size={14} />
                  <span>Sync Mailbox</span>
                </button>
              }
            />
          </div>
        ) : (
          <div>
            {/* Desktop Table View (>= 768px) */}
            <div className="hidden md:block table-container">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="table-header">
                    <th className="table-th">Company & Role</th>
                    <th className="table-th">Status</th>
                    <th className="table-th">Source</th>
                    <th className="table-th">Last Updated</th>
                    <th className="table-th text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70 dark:divide-white/[0.065]">
                  {recentActivity.map((app) => (
                    <tr key={app.id} className="table-row group">
                      <td className="table-td max-w-xs truncate">
                        <Link to={`/applications/${app.id}`} className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-bold flex items-center justify-center text-xs shrink-0 border border-indigo-500/20">
                            {app.company.charAt(0).toUpperCase()}
                          </div>
                          <div className="min-w-0">
                            <p className="font-bold text-slate-900 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors text-sm truncate">
                              {app.company}
                            </p>
                            <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">{app.job_title}</p>
                          </div>
                        </Link>
                      </td>
                      <td className="table-td">
                        <StatusBadge status={app.current_status} />
                      </td>
                      <td className="table-td text-xs text-slate-500 dark:text-slate-400 font-medium">
                        {app.source || 'Direct'}
                      </td>
                      <td className="table-td text-xs text-slate-500 dark:text-slate-400 font-medium">
                        {new Date(app.updated_at || app.application_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                      </td>
                      <td className="table-td text-right">
                        <Link
                          to={`/applications/${app.id}`}
                          className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-slate-100 dark:hover:bg-white/[0.08] rounded-xl transition-colors inline-block"
                        >
                          <ArrowUpRight size={16} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Responsive Cards (< 768px) */}
            <div className="md:hidden p-3 sm:p-4 space-y-2.5">
              {recentActivity.map((app) => (
                <Link
                  key={app.id}
                  to={`/applications/${app.id}`}
                  className="p-3.5 sm:p-4 rounded-2xl bg-white/70 dark:bg-white/[0.03] border border-slate-200/80 dark:border-white/[0.06] shadow-sm flex items-center justify-between gap-2.5 hover:border-slate-300 dark:hover:border-white/[0.12] transition-all block"
                >
                  <div className="flex items-center gap-2.5 min-w-0 flex-1">
                    <div className="w-8 h-8 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-bold flex items-center justify-center text-xs shrink-0 border border-indigo-500/20">
                      {app.company.charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-bold text-slate-900 dark:text-slate-100 text-sm truncate leading-tight">
                        {app.company}
                      </p>
                      <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
                        {app.job_title}
                      </p>
                      <div className="mt-1.5 flex items-center gap-1.5">
                        <StatusBadge status={app.current_status} />
                      </div>
                    </div>
                  </div>
                  <ChevronRight size={15} className="text-slate-400 shrink-0" />
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
