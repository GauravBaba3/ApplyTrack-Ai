import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  RefreshCw, Briefcase, Mail, CheckCircle2, XCircle, ChevronRight, 
  Activity, TrendingUp, Search, UserCheck, Loader2, Sparkles, Clock, 
  ArrowUpRight, Award, Plus, Layers
} from 'lucide-react';
import { applicationApi, analyticsApi } from '../services/api';
import { ApplicationStats, UserAnalytics } from '../types';
import { useSync } from '../context/SyncContext';
import PageHeader from '../components/PageHeader';
import StatCard from '../components/StatCard';
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
  
  // If we already have cached data, don't show full-page skeleton
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
        applicationApi.getAll({ ordering: '-updated_at', limit: 5 }).catch(() => ({ data: { results: [] } }))
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

  // Fetch on mount (silent if cached) and reactively whenever background sync completes a batch
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

  return (
    <div className="space-y-8 pb-12">
      {/* Dashboard Top Header */}
      <PageHeader 
        title="Dashboard" 
        description="Welcome back. Here's your automated application tracking overview."
      >
        <button
          onClick={handleSync}
          disabled={isSyncing}
          className="btn btn-secondary shadow-sm"
        >
          <RefreshCw className={isSyncing ? 'animate-spin text-indigo-600' : 'text-slate-400 dark:text-slate-500'} size={16} />
          <span>{isSyncing ? 'Syncing...' : 'Sync Gmail'}</span>
        </button>
        <Link to="/applications" className="btn btn-primary shadow-sm">
          <Plus size={16} />
          <span>Add Application</span>
        </Link>
      </PageHeader>

      {/* Dynamic Sync Progress / Result Banner */}
      {isSyncing && (
        <div className="p-4 rounded-2xl border bg-indigo-50/80 dark:bg-indigo-950/40 border-indigo-200 dark:border-indigo-800/80 text-indigo-900 dark:text-indigo-200 shadow-sm animate-pulse">
          <div className="flex items-center gap-3.5">
            <Loader2 className="text-indigo-600 dark:text-indigo-400 animate-spin shrink-0" size={22} />
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="font-bold text-sm">Syncing Gmail in background...</p>
                {progress?.page && (
                  <span className="px-2 py-0.5 text-[10px] font-bold bg-indigo-200 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200 rounded-full">
                    Page {progress.page}
                  </span>
                )}
              </div>
              <p className="text-xs opacity-90 mt-0.5">
                {cumulativeStats.emails_scanned} emails scanned &bull; {cumulativeStats.job_related_emails} job-related &bull; {cumulativeStats.new_applications} new applications &bull; {cumulativeStats.applications_updated} updated
              </p>
            </div>
          </div>
        </div>
      )}

      {!isSyncing && syncError && (
        <div className="p-4 rounded-2xl border bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800 text-rose-900 dark:text-rose-200 shadow-sm">
          <div className="flex items-center gap-3">
            <XCircle className="text-rose-500 shrink-0" size={20} />
            <div>
              <p className="font-bold text-sm">Sync Notice</p>
              <p className="text-xs opacity-90 mt-0.5">{syncError}</p>
            </div>
          </div>
        </div>
      )}

      {/* Primary KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        {loading ? (
          Array(4).fill(0).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <StatCard
              icon={Briefcase}
              value={totalApps}
              title="Total Applications"
              color="blue"
              subtitle="All tracked opportunities"
            />
            <StatCard
              icon={Activity}
              value={appliedCount}
              title="Active / Applied"
              color="purple"
              subtitle="Awaiting response"
            />
            <StatCard
              icon={TrendingUp}
              value={interviewCount}
              title="Interviews"
              color="green"
              subtitle={analytics?.interview_rate ? `${analytics.interview_rate}% conversion` : 'Interview stage'}
            />
            <StatCard
              icon={Award}
              value={offerCount}
              title="Offers Received"
              color="cyan"
              subtitle="Final offers"
            />
          </>
        )}
      </div>

      {/* Application Status Pipeline Funnel */}
      <div className="card p-6 sm:p-7">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Layers size={18} className="text-indigo-600 dark:text-indigo-400" />
              Application Pipeline Overview
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Live distribution across hiring stages</p>
          </div>
          <Link to="/applications" className="text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1">
            <span>Manage Pipeline</span>
            <ChevronRight size={14} />
          </Link>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {[
            { label: 'Applied', count: appliedCount, badgeClass: 'badge-applied' },
            { label: 'Assessment', count: assessmentCount, badgeClass: 'badge-assessment' },
            { label: 'Interview', count: interviewCount, badgeClass: 'badge-interview' },
            { label: 'Offer', count: offerCount, badgeClass: 'badge-offer' },
            { label: 'Rejected', count: rejectedCount, badgeClass: 'badge-rejected' },
          ].map((stage, idx) => (
            <div key={idx} className="p-4 rounded-xl border border-slate-200/70 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-800/30">
              <span className={`badge ${stage.badgeClass} mb-2`}>{stage.label}</span>
              <p className="text-2xl font-black text-slate-900 dark:text-slate-100">{stage.count}</p>
              <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">
                {totalApps > 0 ? `${Math.round((stage.count / totalApps) * 100)}% of total` : '0%'}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Main Grid: Recent Activity & Side Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8 items-start">
        {/* Recent Applications (takes 2/3 width) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="card overflow-hidden">
            <div className="card-header flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 tracking-tight">Recent Activity</h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Recently updated applications</p>
              </div>
              <Link to="/applications" className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1">
                <span>View all</span>
                <ChevronRight size={14} />
              </Link>
            </div>

            {loading ? (
              <div className="p-6 space-y-4">
                <SkeletonTableRow />
                <SkeletonTableRow />
                <SkeletonTableRow />
              </div>
            ) : recentActivity.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={Briefcase}
                  title="No applications tracked yet"
                  description="Click 'Sync Gmail' to auto-detect applications from your emails or add one manually."
                  action={
                    <button onClick={handleSync} className="btn btn-primary text-xs">
                      <RefreshCw size={14} />
                      <span>Sync Gmail Now</span>
                    </button>
                  }
                />
              </div>
            ) : (
              <div className="table-container">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="table-header">
                      <th className="table-th">Company & Role</th>
                      <th className="table-th">Status</th>
                      <th className="table-th">Applied Date</th>
                      <th className="table-th text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {recentActivity.map((app) => (
                      <tr key={app.id} className="table-row group">
                        <td className="table-td">
                          <Link to={`/applications/${app.id}`} className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-bold flex items-center justify-center text-xs shrink-0 group-hover:bg-indigo-50 dark:group-hover:bg-indigo-950 group-hover:text-indigo-600 transition-colors">
                              {app.company.charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <p className="font-bold text-slate-900 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors text-sm">
                                {app.company}
                              </p>
                              <p className="text-xs text-slate-500 dark:text-slate-400">{app.job_title}</p>
                            </div>
                          </Link>
                        </td>
                        <td className="table-td">
                          <StatusBadge status={app.current_status} />
                        </td>
                        <td className="table-td text-xs text-slate-500 dark:text-slate-400">
                          {new Date(app.application_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                        </td>
                        <td className="table-td text-right">
                          <Link
                            to={`/applications/${app.id}`}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-slate-100 dark:hover:bg-slate-800 inline-flex transition-colors"
                          >
                            <ArrowUpRight size={16} />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar Widgets (takes 1/3 width) */}
        <div className="space-y-6">
          {/* Quick Actions Card */}
          <div className="card p-6 space-y-4">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 tracking-tight">Quick Actions</h2>
            <div className="flex flex-col gap-2.5">
              <button 
                onClick={handleSync} 
                disabled={isSyncing} 
                className="w-full flex items-center justify-between p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-700/80 hover:bg-indigo-50/50 dark:hover:bg-indigo-950/30 transition-all text-left group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0">
                    <RefreshCw size={18} className={isSyncing ? 'animate-spin' : ''} />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 dark:text-slate-100 text-xs group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">Sync Gmail</h3>
                    <p className="text-[11px] text-slate-400 dark:text-slate-500">Scan mailbox for updates</p>
                  </div>
                </div>
                <ChevronRight size={16} className="text-slate-400 group-hover:text-indigo-600 transition-colors" />
              </button>

              <Link 
                to="/applications?add=true" 
                className="w-full flex items-center justify-between p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-emerald-300 dark:hover:border-emerald-700/80 hover:bg-emerald-50/50 dark:hover:bg-emerald-950/30 transition-all text-left group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                    <Briefcase size={18} />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 dark:text-slate-100 text-xs group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">Add Application</h3>
                    <p className="text-[11px] text-slate-400 dark:text-slate-500">Manually record a job</p>
                  </div>
                </div>
                <ChevronRight size={16} className="text-slate-400 group-hover:text-emerald-600 transition-colors" />
              </Link>

              <Link 
                to="/emails" 
                className="w-full flex items-center justify-between p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-purple-300 dark:hover:border-purple-700/80 hover:bg-purple-50/50 dark:hover:bg-purple-950/30 transition-all text-left group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0">
                    <Mail size={18} />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 dark:text-slate-100 text-xs group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">Email Activity</h3>
                    <p className="text-[11px] text-slate-400 dark:text-slate-500">View parsed recruiter emails</p>
                  </div>
                </div>
                <ChevronRight size={16} className="text-slate-400 group-hover:text-purple-600 transition-colors" />
              </Link>
            </div>
          </div>

          {/* Performance & Health Card */}
          <div className="card p-6 space-y-4">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 tracking-tight">Performance Summary</h2>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs font-semibold mb-1.5">
                  <span className="text-slate-500 dark:text-slate-400">Response Rate</span>
                  <span className="text-slate-900 dark:text-slate-100 font-bold">{analytics?.response_rate || 0}%</span>
                </div>
                <div className="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-indigo-600 h-full rounded-full transition-all duration-500" 
                    style={{ width: `${Math.min(analytics?.response_rate || 0, 100)}%` }} 
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold mb-1.5">
                  <span className="text-slate-500 dark:text-slate-400">Interview Rate</span>
                  <span className="text-slate-900 dark:text-slate-100 font-bold">{analytics?.interview_rate || 0}%</span>
                </div>
                <div className="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-emerald-500 h-full rounded-full transition-all duration-500" 
                    style={{ width: `${Math.min(analytics?.interview_rate || 0, 100)}%` }} 
                  />
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs">
                <span className="text-slate-500 dark:text-slate-400">Avg Response Time</span>
                <span className="font-bold text-slate-900 dark:text-slate-100">{analytics?.avg_days_to_response || 0} days</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
