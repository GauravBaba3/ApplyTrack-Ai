import React, { useState, useEffect, useCallback } from 'react';
import { 
  TrendingUp, Briefcase, Award, Clock, RefreshCw, BarChart3, 
  Sparkles, Layers, CheckCircle2, XCircle, Mail, Filter
} from 'lucide-react';
import { analyticsApi, applicationApi, emailApi } from '../services/api';
import { UserAnalytics, ApplicationStats, Application, ProcessedEmail } from '../types';
import { useSync } from '../context/SyncContext';
import { cacheService, CACHE_TTL } from '../services/cacheService';

import AnalyticsMetricCard from '../components/analytics/AnalyticsMetricCard';
import ApplicationPipelineChart from '../components/analytics/ApplicationPipelineChart';
import HiringFunnelChart from '../components/analytics/HiringFunnelChart';
import ApplicationTrendChart from '../components/analytics/ApplicationTrendChart';
import SourceDistributionChart from '../components/analytics/SourceDistributionChart';
import EmailIntelligenceChart from '../components/analytics/EmailIntelligenceChart';
import AnalyticsSkeleton from '../components/analytics/AnalyticsSkeleton';
import AnalyticsEmptyState from '../components/analytics/AnalyticsEmptyState';
import AnalyticsError from '../components/analytics/AnalyticsError';

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<UserAnalytics | null>(() => 
    cacheService.get<UserAnalytics>('analytics:data', CACHE_TTL.ANALYTICS)
  );
  const [stats, setStats] = useState<ApplicationStats | null>(() => 
    cacheService.get<ApplicationStats>('analytics:stats', CACHE_TTL.ANALYTICS)
  );
  const [applications, setApplications] = useState<Application[]>(() => 
    cacheService.get<Application[]>('applications:list', CACHE_TTL.APPLICATIONS) || []
  );
  const [emails, setEmails] = useState<ProcessedEmail[]>(() => 
    cacheService.get<ProcessedEmail[]>('emails:list', CACHE_TTL.EMAILS) || []
  );
  
  const hasCachedData = Boolean(analytics || stats || applications.length > 0);
  const [loading, setLoading] = useState(!hasCachedData);
  const [error, setError] = useState(false);

  const { dataVersion, isSyncing, triggerSync } = useSync();

  const fetchData = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      setError(false);

      const [analyticsRes, statsRes, appsRes, emailsRes] = await Promise.all([
        analyticsApi.get().catch(() => ({ data: null })),
        applicationApi.getStats().catch(() => ({ data: null })),
        applicationApi.getAll({ ordering: '-application_date' }).catch(() => ({ data: { results: [] } })),
        emailApi.getAll().catch(() => ({ data: { results: [] } })),
      ]);

      if (analyticsRes.data) {
        setAnalytics(analyticsRes.data);
        cacheService.set('analytics:data', analyticsRes.data);
      }
      if (statsRes.data) {
        setStats(statsRes.data);
        cacheService.set('analytics:stats', statsRes.data);
      }
      if (appsRes.data?.results) {
        setApplications(appsRes.data.results);
        cacheService.set('applications:list', appsRes.data.results);
      }
      if (emailsRes.data?.results) {
        setEmails(emailsRes.data.results);
        cacheService.set('emails:list', emailsRes.data.results);
      }
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(hasCachedData);
  }, [fetchData, dataVersion]);

  if (loading) {
    return <AnalyticsSkeleton />;
  }

  if (error && !analytics && !stats && applications.length === 0) {
    return <AnalyticsError onRetry={() => fetchData(false)} />;
  }

  const totalApps = stats?.total_applications || applications.length || 0;
  const appliedCount = stats?.applied || 0;
  const assessmentCount = stats?.assessment || 0;
  const interviewCount = stats?.interview || 0;
  const offerCount = stats?.offer || 0;
  const rejectedCount = stats?.rejected || 0;

  // Build comprehensive status map from actual applications and stats
  const statusCounts: Record<string, number> = {
    'Applied': appliedCount,
    'Assessment': assessmentCount,
    'Interview': interviewCount,
    'Offer': offerCount,
    'Rejected': rejectedCount,
    'Under Review': 0,
    'Withdrawn': 0,
    'No Response': stats?.no_response || 0,
    'Stale': stats?.stale || 0,
    'Ghosted': 0,
    'Needs Review': (stats as any)?.needs_review || 0,
  };

  // Supplement status counts from individual application records if available
  applications.forEach((app) => {
    if (app.current_status && !statusCounts[app.current_status]) {
      statusCounts[app.current_status] = 1;
    }
  });

  const hasAnyData = totalApps > 0 || emails.length > 0;

  if (!hasAnyData) {
    return <AnalyticsEmptyState onSync={() => triggerSync(true)} isSyncing={isSyncing} />;
  }

  return (
    <div className="space-y-5 sm:space-y-6 pb-12 animate-fade-in w-full max-w-full min-w-0">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
        <div className="min-w-0">
          <h1 className="text-page-title text-slate-900 dark:text-slate-100 truncate">
            Analytics & Insights
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-0.5 max-w-2xl font-normal leading-relaxed">
            Real-time pipeline progression metrics, hiring stage conversion, and mailbox intelligence.
          </p>
        </div>
        <button 
          onClick={() => fetchData(false)} 
          className="btn btn-secondary text-xs sm:text-sm shadow-sm w-full sm:w-auto justify-center"
          title="Refresh analytics dataset"
        >
          <RefreshCw size={15} className="text-slate-400" />
          <span>Refresh Data</span>
        </button>
      </div>

      {/* =========================================================================
          KEY METRICS ROW (4 COMPACT CARDS)
          ========================================================================= */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <AnalyticsMetricCard
          title="Total Applications"
          value={totalApps}
          subtitle="Total volume tracked across all stages"
          icon={Briefcase}
          color="blue"
          badge={analytics?.applications_this_month ? `${analytics.applications_this_month} this month` : undefined}
          badgeType="neutral"
        />
        <AnalyticsMetricCard
          title="Interviews"
          value={interviewCount}
          subtitle={`${analytics?.interview_rate || 0}% overall conversion rate`}
          icon={Award}
          color="green"
          badge={`${analytics?.interview_rate || 0}%`}
          badgeType="positive"
        />
        <AnalyticsMetricCard
          title="Offers Received"
          value={offerCount}
          subtitle={`${analytics?.offer_rate || 0}% overall offer conversion`}
          icon={Sparkles}
          color="cyan"
          badge={offerCount > 0 ? 'Active Offers' : undefined}
          badgeType="positive"
        />
        <AnalyticsMetricCard
          title="Avg Response Latency"
          value={`${analytics?.avg_days_to_response || 0}d`}
          subtitle={`${analytics?.response_rate || 0}% recruiter response rate`}
          icon={Clock}
          color="purple"
          badge={`${analytics?.response_rate || 0}% Response`}
          badgeType="accent"
        />
      </div>

      {/* =========================================================================
          MAIN CHARTS ROW (PIPELINE BREAKDOWN + HIRING STAGE FUNNEL)
          ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Chart 1: Proportional Pipeline Donut & Distribution Bars */}
        <ApplicationPipelineChart
          statusCounts={statusCounts}
          totalApplications={totalApps}
        />

        {/* Chart 2 & 5: Hiring Stage Funnel & Outcome Progression */}
        <HiringFunnelChart
          totalApplications={totalApps}
          applied={appliedCount}
          assessment={assessmentCount}
          interview={interviewCount}
          offer={offerCount}
          rejected={rejectedCount}
          interviewRate={analytics?.interview_rate || 0}
          offerRate={analytics?.offer_rate || 0}
        />
      </div>

      {/* =========================================================================
          TIMELINE & SOURCE DISTRIBUTION
          ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Chart 3: Application Activity Over Time */}
        <ApplicationTrendChart applications={applications} />

        {/* Chart 4: Application Channel Distribution */}
        <SourceDistributionChart applications={applications} />
      </div>

      {/* =========================================================================
          MAILBOX & AI TRIAGE INTELLIGENCE
          ========================================================================= */}
      {emails.length > 0 && (
        <EmailIntelligenceChart emails={emails} />
      )}
    </div>
  );
}
