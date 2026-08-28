import React, { useState, useEffect, useCallback } from 'react';
import { 
  TrendingUp, Users, Briefcase, Calendar, Award, XCircle, 
  Clock, RefreshCw, BarChart3, PieChart, Activity, CheckCircle2 
} from 'lucide-react';
import { analyticsApi, applicationApi } from '../services/api';
import { UserAnalytics, ApplicationStats } from '../types';
import { useSync } from '../context/SyncContext';
import PageHeader from '../components/PageHeader';
import StatCard from '../components/StatCard';
import { SkeletonCard } from '../components/LoadingSkeleton';
import { cacheService, CACHE_TTL } from '../services/cacheService';

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<UserAnalytics | null>(() => 
    cacheService.get<UserAnalytics>('analytics:data', CACHE_TTL.ANALYTICS)
  );
  const [stats, setStats] = useState<ApplicationStats | null>(() => 
    cacheService.get<ApplicationStats>('analytics:stats', CACHE_TTL.ANALYTICS)
  );
  
  const hasCachedData = Boolean(analytics || stats);
  const [loading, setLoading] = useState(!hasCachedData);

  const { dataVersion } = useSync();

  const fetchData = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const [analyticsResponse, statsResponse] = await Promise.all([
        analyticsApi.get().catch(() => ({ data: null })),
        applicationApi.getStats().catch(() => ({ data: null }))
      ]);
      if (analyticsResponse.data) {
        setAnalytics(analyticsResponse.data);
        cacheService.set('analytics:data', analyticsResponse.data);
      }
      if (statsResponse.data) {
        setStats(statsResponse.data);
        cacheService.set('analytics:stats', statsResponse.data);
      }
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(hasCachedData);
  }, [fetchData, dataVersion]);

  if (loading) {
    return (
      <div className="space-y-6 pb-12">
        <PageHeader title="Analytics & Insights" description="Performance tracking and job search conversion rates" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  const totalApps = stats?.total_applications || 0;
  const appliedCount = stats?.applied || 0;
  const assessmentCount = stats?.assessment || 0;
  const interviewCount = stats?.interview || 0;
  const offerCount = stats?.offer || 0;
  const rejectedCount = stats?.rejected || 0;

  return (
    <div className="space-y-8 pb-12">
      <PageHeader
        title="Analytics & Insights"
        description="Comprehensive metrics, response rates, and conversion funnel of your job search."
      >
        <button onClick={() => fetchData()} className="btn btn-secondary shadow-sm">
          <RefreshCw size={16} className="text-slate-400" />
          <span>Refresh Data</span>
        </button>
      </PageHeader>

      {/* Top Level KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        <StatCard
          icon={Briefcase}
          value={totalApps}
          title="Total Applications"
          color="blue"
          subtitle="Total volume tracked"
        />
        <StatCard
          icon={TrendingUp}
          value={`${analytics?.interview_rate || 0}%`}
          title="Interview Rate"
          color="green"
          subtitle="Applications reaching interview"
        />
        <StatCard
          icon={Activity}
          value={`${analytics?.response_rate || 0}%`}
          title="Response Rate"
          color="purple"
          subtitle="Replies received from recruiters"
        />
        <StatCard
          icon={Clock}
          value={`${analytics?.avg_days_to_response || 0}d`}
          title="Avg Response Time"
          color="cyan"
          subtitle="Days from applied to reply"
        />
      </div>

      {/* Main Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 sm:gap-8">
        {/* Status Funnel Card */}
        <div className="card p-6 sm:p-7 space-y-6">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <BarChart3 size={18} className="text-indigo-600 dark:text-indigo-400" />
              Application Status Distribution
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Distribution across pipeline stages</p>
          </div>

          <div className="space-y-4">
            {[
              { label: 'Applied', count: appliedCount, color: 'bg-blue-500', barBg: 'bg-blue-100 dark:bg-blue-950/60' },
              { label: 'Assessment', count: assessmentCount, color: 'bg-purple-500', barBg: 'bg-purple-100 dark:bg-purple-950/60' },
              { label: 'Interview', count: interviewCount, color: 'bg-emerald-500', barBg: 'bg-emerald-100 dark:bg-emerald-950/60' },
              { label: 'Offer', count: offerCount, color: 'bg-cyan-500', barBg: 'bg-cyan-100 dark:bg-cyan-950/60' },
              { label: 'Rejected', count: rejectedCount, color: 'bg-rose-500', barBg: 'bg-rose-100 dark:bg-rose-950/60' },
            ].map((stage, idx) => {
              const percentage = totalApps > 0 ? Math.round((stage.count / totalApps) * 100) : 0;
              return (
                <div key={idx} className="space-y-1.5">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-slate-700 dark:text-slate-300">{stage.label}</span>
                    <span className="text-slate-500 dark:text-slate-400">{stage.count} ({percentage}%)</span>
                  </div>
                  <div className={`w-full ${stage.barBg} h-2.5 rounded-full overflow-hidden`}>
                    <div 
                      className={`${stage.color} h-full rounded-full transition-all duration-500`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Pipeline Conversion Rates */}
        <div className="card p-6 sm:p-7 space-y-6">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <PieChart size={18} className="text-indigo-600 dark:text-indigo-400" />
              Conversion & Conversion Funnel
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Effectiveness across key milestones</p>
          </div>

          <div className="space-y-4">
            <div className="p-4 rounded-xl border border-slate-200/70 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Offer Conversion</p>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Offers relative to interview invitations</p>
              </div>
              <p className="text-2xl font-black text-slate-900 dark:text-slate-100">
                {interviewCount > 0 ? `${Math.round((offerCount / interviewCount) * 100)}%` : '0%'}
              </p>
            </div>

            <div className="p-4 rounded-xl border border-slate-200/70 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Interview Conversion</p>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Interviews relative to total applied</p>
              </div>
              <p className="text-2xl font-black text-slate-900 dark:text-slate-100">
                {analytics?.interview_rate || 0}%
              </p>
            </div>

            <div className="p-4 rounded-xl border border-slate-200/70 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Average Response Time</p>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Days from submission to initial reply</p>
              </div>
              <p className="text-2xl font-black text-slate-900 dark:text-slate-100">
                {analytics?.avg_days_to_response || 0} <span className="text-sm font-normal text-slate-400">days</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
