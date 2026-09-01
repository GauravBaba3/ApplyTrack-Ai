import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  Mail, CheckCircle2, XCircle, AlertCircle, RefreshCw, 
  ArrowUpRight, Check, EyeOff, Sparkles, Inbox, ChevronRight
} from 'lucide-react';
import { emailApi } from '../services/api';
import { ProcessedEmail, ProcessingStatus } from '../types';
import { useSync } from '../context/SyncContext';
import PageHeader from '../components/PageHeader';
import StatCard from '../components/StatCard';
import EmptyState from '../components/EmptyState';
import { SkeletonTableRow, SkeletonCard } from '../components/LoadingSkeleton';
import { cacheService, CACHE_TTL } from '../services/cacheService';

export default function EmailActivityPage() {
  const [emails, setEmails] = useState<ProcessedEmail[]>(() => {
    const cached = cacheService.get<ProcessedEmail[]>('emails:list', CACHE_TTL.EMAILS);
    return cached || [];
  });
  
  const hasCachedData = emails.length > 0;
  const [loading, setLoading] = useState(!hasCachedData);
  const [statusFilter, setStatusFilter] = useState<ProcessingStatus | ''>('');

  const { dataVersion } = useSync();

  const fetchEmails = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const params: any = { ordering: '-received_at' };
      if (statusFilter) {
        params.status = statusFilter;
      }
      const response = await emailApi.getAll(params);
      const results = response.data?.results || [];
      setEmails(results);

      // Only cache unfiltered queries
      if (!statusFilter) {
        cacheService.set('emails:list', results);
      }
    } catch (error) {
      console.error('Failed to fetch emails:', error);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchEmails(hasCachedData && !statusFilter);
  }, [fetchEmails, dataVersion]);

  const handleMarkAsReviewed = async (emailId: number) => {
    try {
      await emailApi.markAsReviewed(emailId);
      cacheService.remove('emails:list');
      cacheService.remove('dashboard:stats');
      cacheService.remove('dashboard:recent');
      fetchEmails();
    } catch (error) {
      console.error('Failed to mark email as reviewed:', error);
    }
  };

  const handleIgnore = async (emailId: number) => {
    try {
      await emailApi.ignore(emailId);
      cacheService.remove('emails:list');
      cacheService.remove('dashboard:stats');
      cacheService.remove('dashboard:recent');
      fetchEmails();
    } catch (error) {
      console.error('Failed to ignore email:', error);
    }
  };

  const getPriorityBadge = (priority?: string) => {
    switch (priority) {
      case 'P1':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/25 shrink-0">
            P1 Urgent
          </span>
        );
      case 'P3':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-slate-500/10 text-slate-500 dark:text-slate-400 border border-slate-500/20 shrink-0">
            P3 Low
          </span>
        );
      case 'P2':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/25 shrink-0">
            P2 Medium
          </span>
        );
    }
  };

  const getStatusBadge = (status: ProcessingStatus) => {
    switch (status) {
      case 'detected':
        return (
          <span className="badge badge-applied">
            <Mail size={11} className="mr-1" /> Detected
          </span>
        );
      case 'needs_review':
        return (
          <span className="badge badge-needs-review">
            <AlertCircle size={11} className="mr-1" /> Needs Review
          </span>
        );
      case 'processed':
        return (
          <span className="badge badge-interview">
            <CheckCircle2 size={11} className="mr-1" /> Processed
          </span>
        );
      case 'ignored':
        return (
          <span className="badge badge-no-response">
            <EyeOff size={11} className="mr-1" /> Ignored
          </span>
        );
      case 'failed':
        return (
          <span className="badge badge-rejected">
            <XCircle size={11} className="mr-1" /> Failed
          </span>
        );
      default:
        return null;
    }
  };

  const tabs: { label: string; value: ProcessingStatus | '' }[] = [
    { label: 'All Emails', value: '' },
    { label: 'Review Needed', value: 'needs_review' },
    { label: 'Processed', value: 'processed' },
    { label: 'Detected', value: 'detected' },
    { label: 'Ignored', value: 'ignored' },
  ];

  const totalMonitored = emails.length;
  const needsReviewCount = emails.filter((e) => e.processing_status === 'needs_review').length;
  const processedCount = emails.filter((e) => e.processing_status === 'processed').length;

  return (
    <div className="space-y-4 sm:space-y-6 pb-12 animate-fade-in w-full max-w-full min-w-0">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
        <div className="min-w-0">
          <h1 className="text-page-title text-slate-900 dark:text-slate-100 truncate">
            Email Activity
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-0.5 max-w-2xl font-normal leading-relaxed">
            Monitor automated Gmail parsing, AI classification cascade, and recruiter event extractions.
          </p>
        </div>
        <button
          onClick={() => fetchEmails()}
          className="btn btn-secondary text-xs sm:text-sm shadow-sm w-full sm:w-auto justify-center"
          title="Refresh email logs"
        >
          <RefreshCw size={15} className={loading ? 'animate-spin text-indigo-500' : 'text-slate-400'} />
          <span>Refresh Logs</span>
        </button>
      </div>

      {/* Metrics Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
        <StatCard
          icon={Mail}
          value={totalMonitored}
          title="Monitored Emails"
          color="blue"
          subtitle="Total detected recruiter emails"
        />
        <StatCard
          icon={AlertCircle}
          value={needsReviewCount}
          title="Needs Review"
          color="orange"
          subtitle="Ambiguous recruiter updates"
        />
        <StatCard
          icon={CheckCircle2}
          value={processedCount}
          title="Auto-Processed"
          color="green"
          subtitle="Confirmed status updates"
        />
      </div>

      {/* Filter Tabs Card */}
      <div className="glass-2 p-1.5 sm:p-2 rounded-2xl flex items-center gap-1.5 overflow-x-auto scrollbar-none -mx-3 px-3 sm:mx-0 sm:px-2">
        {tabs.map((tab) => (
          <button
            key={tab.value || 'all'}
            onClick={() => setStatusFilter(tab.value)}
            className={`px-3 sm:px-4 py-1.5 sm:py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all shrink-0 ${
              statusFilter === tab.value
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/25 font-bold'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-white/[0.06]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main Email Activity Container: Desktop Table + Mobile Cards */}
      <div className="glass-2 rounded-2xl sm:rounded-3xl overflow-hidden w-full">
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
        ) : emails.length === 0 ? (
          <div className="p-8 sm:p-12">
            <EmptyState
              icon={Inbox}
              title={statusFilter ? 'No emails in this category' : 'No job-related emails detected yet'}
              description={
                statusFilter
                  ? 'There are no emails matching the selected category filter.'
                  : 'Sync Gmail to scan your inbox for application confirmations, interview invitations, and status updates.'
              }
              action={
                statusFilter ? (
                  <button onClick={() => setStatusFilter('')} className="btn btn-secondary text-xs">
                    Clear Filter
                  </button>
                ) : null
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
                    <th className="table-th">Subject & Sender</th>
                    <th className="table-th">Company & Event</th>
                    <th className="table-th">Status & Priority</th>
                    <th className="table-th">Received Date</th>
                    <th className="table-th text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70 dark:divide-white/[0.065]">
                  {emails.map((email) => (
                    <tr key={email.id} className="table-row group">
                      <td className="table-td max-w-xs sm:max-w-md truncate">
                        <div className="flex items-start gap-3">
                          <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-600 dark:text-indigo-400 font-bold flex items-center justify-center text-xs shrink-0 mt-0.5">
                            <Mail size={14} />
                          </div>
                          <div className="min-w-0">
                            <p className="font-bold text-slate-900 dark:text-slate-100 text-sm truncate">
                              {email.subject}
                            </p>
                            <p className="text-xs text-slate-400 dark:text-slate-500 truncate mt-0.5 font-medium">{email.sender}</p>
                          </div>
                        </div>
                      </td>
                      <td className="table-td">
                        <div>
                          <p className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                            {email.company || 'Unknown Company'}
                          </p>
                          <p className="text-xs text-indigo-600 dark:text-indigo-400 capitalize font-semibold mt-0.5">
                            {email.event_type ? email.event_type.replace(/_/g, ' ') : (email.detected_status || 'Detected')}
                          </p>
                        </div>
                      </td>
                      <td className="table-td">
                        <div className="flex flex-col items-start gap-1.5">
                          {getStatusBadge(email.processing_status)}
                          {email.triage_priority && getPriorityBadge(email.triage_priority)}
                        </div>
                      </td>
                      <td className="table-td text-xs text-slate-500 dark:text-slate-400 font-medium">
                        {new Date(email.received_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                      </td>
                      <td className="table-td text-right">
                        <div className="flex items-center justify-end gap-1">
                          {email.processing_status === 'needs_review' && (
                            <button
                              onClick={() => handleMarkAsReviewed(email.id)}
                              className="p-2 rounded-xl text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 transition-colors"
                              title="Confirm & Mark as Reviewed"
                            >
                              <Check size={16} />
                            </button>
                          )}
                          {email.processing_status !== 'ignored' && (
                            <button
                              onClick={() => handleIgnore(email.id)}
                              className="p-2 rounded-xl text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
                              title="Ignore Email"
                            >
                              <EyeOff size={16} />
                            </button>
                          )}
                          {email.application && (
                            <Link
                              to={`/applications/${email.application}`}
                              className="p-2 rounded-xl text-slate-400 hover:text-indigo-600 hover:bg-slate-100 dark:hover:bg-white/[0.08] transition-colors"
                              title="Go to Application"
                            >
                              <ArrowUpRight size={16} />
                            </Link>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Responsive Cards (< 768px: separated cards with clear margin) */}
            <div className="md:hidden p-3 sm:p-4 space-y-3">
              {emails.map((email) => (
                <div 
                  key={email.id} 
                  className="p-3.5 sm:p-4 rounded-2xl bg-white/70 dark:bg-white/[0.03] border border-slate-200/80 dark:border-white/[0.06] shadow-sm space-y-2.5 hover:border-slate-300 dark:hover:border-white/[0.12] transition-all"
                >
                  {/* Top Header: Company + Badges */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-bold text-slate-900 dark:text-slate-100 text-sm truncate leading-tight">
                        {email.company || 'Unknown Company'}
                      </p>
                      <p className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold capitalize mt-0.5">
                        {email.event_type ? email.event_type.replace(/_/g, ' ') : (email.detected_status || 'Recruiter Update')}
                      </p>
                    </div>
                    <div className="shrink-0 flex flex-col items-end gap-1">
                      {getStatusBadge(email.processing_status)}
                      {email.triage_priority && getPriorityBadge(email.triage_priority)}
                    </div>
                  </div>

                  {/* Subject & Sender */}
                  <div className="space-y-0.5">
                    <p className="text-xs text-slate-700 dark:text-slate-300 font-medium line-clamp-2 leading-relaxed">
                      {email.subject}
                    </p>
                    <p className="text-[11px] text-slate-400 dark:text-slate-500 truncate font-normal">
                      {email.sender}
                    </p>
                  </div>

                  {/* Footer & Touch Actions */}
                  <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-100 dark:border-white/[0.04] text-[11px] text-slate-500 dark:text-slate-400">
                    <span>
                      {new Date(email.received_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                    </span>
                    <div className="flex items-center gap-1.5">
                      {email.processing_status === 'needs_review' && (
                        <button
                          onClick={() => handleMarkAsReviewed(email.id)}
                          className="px-2.5 py-1 text-xs rounded-xl bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-bold"
                        >
                          Confirm
                        </button>
                      )}
                      {email.processing_status !== 'ignored' && (
                        <button
                          onClick={() => handleIgnore(email.id)}
                          className="p-1 text-slate-400 hover:text-rose-500"
                          title="Ignore Email"
                          aria-label="Ignore Email"
                        >
                          <EyeOff size={14} />
                        </button>
                      )}
                      {email.application && (
                        <Link
                          to={`/applications/${email.application}`}
                          className="p-1 text-indigo-600 dark:text-indigo-400 font-semibold"
                          title="View Application"
                          aria-label="View Application"
                        >
                          <ArrowUpRight size={15} />
                        </Link>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
