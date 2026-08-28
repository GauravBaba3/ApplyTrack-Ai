import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  Mail, CheckCircle2, XCircle, AlertCircle, Eye, RefreshCw, 
  Filter, ArrowUpRight, Check, EyeOff, Bot, Sparkles, Inbox
} from 'lucide-react';
import { emailApi } from '../services/api';
import { ProcessedEmail, ProcessingStatus } from '../types';
import { useSync } from '../context/SyncContext';
import PageHeader from '../components/PageHeader';
import StatCard from '../components/StatCard';
import EmptyState from '../components/EmptyState';
import { SkeletonTableRow } from '../components/LoadingSkeleton';
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

  const getStatusBadge = (status: ProcessingStatus) => {
    switch (status) {
      case 'detected':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800/60"><Mail size={12} /> Detected</span>;
      case 'needs_review':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800/60"><AlertCircle size={12} /> Review Needed</span>;
      case 'processed':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60"><CheckCircle2 size={12} /> Processed</span>;
      case 'ignored':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700"><EyeOff size={12} /> Ignored</span>;
      case 'failed':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60"><XCircle size={12} /> Failed</span>;
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
  const needsReviewCount = emails.filter(e => e.processing_status === 'needs_review').length;
  const processedCount = emails.filter(e => e.processing_status === 'processed').length;

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <PageHeader
        title="Email Activity"
        description="Monitor automated Gmail parsing, Groq AI classification, and recruiter status extraction."
      >
        <button
          onClick={() => fetchEmails()}
          className="btn btn-secondary shadow-sm"
          title="Refresh email logs"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin text-indigo-600' : 'text-slate-400'} />
          <span>Refresh</span>
        </button>
      </PageHeader>

      {/* Metrics Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          icon={Mail}
          value={totalMonitored}
          title="Monitored Emails"
          color="blue"
          subtitle="Total detected job emails"
        />
        <StatCard
          icon={AlertCircle}
          value={needsReviewCount}
          title="Needs Review"
          color="orange"
          subtitle="Ambiguous updates"
        />
        <StatCard
          icon={CheckCircle2}
          value={processedCount}
          title="Auto-Processed"
          color="green"
          subtitle="Confirmed matches"
        />
      </div>

      {/* Filter Tabs Card */}
      <div className="card p-2 flex items-center gap-1.5 overflow-x-auto scrollbar-none">
        {tabs.map((tab) => (
          <button
            key={tab.value || 'all'}
            onClick={() => setStatusFilter(tab.value)}
            className={`px-4 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
              statusFilter === tab.value
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main Email Activity Table Card */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-6">
            <table className="w-full">
              <tbody>
                <SkeletonTableRow />
                <SkeletonTableRow />
                <SkeletonTableRow />
              </tbody>
            </table>
          </div>
        ) : emails.length === 0 ? (
          <div className="p-12">
            <EmptyState
              icon={Inbox}
              title={statusFilter ? 'No emails found in this category' : 'No job-related emails detected yet'}
              description={
                statusFilter
                  ? 'There are no emails matching the selected filter.'
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
          <div className="table-container">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="table-header">
                  <th className="table-th">Subject & Sender</th>
                  <th className="table-th">Company & Event</th>
                  <th className="table-th">Status</th>
                  <th className="table-th">Received Date</th>
                  <th className="table-th text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {emails.map((email) => (
                  <tr key={email.id} className="table-row group">
                    <td className="table-td max-w-xs sm:max-w-md truncate">
                      <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-bold flex items-center justify-center text-xs shrink-0 mt-0.5">
                          <Mail size={14} />
                        </div>
                        <div className="min-w-0">
                          <p className="font-bold text-slate-900 dark:text-slate-100 text-sm truncate">
                            {email.subject}
                          </p>
                          <p className="text-xs text-slate-400 dark:text-slate-500 truncate mt-0.5">{email.sender}</p>
                        </div>
                      </div>
                    </td>
                    <td className="table-td">
                      <div>
                        <p className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                          {email.company || 'Unknown Company'}
                        </p>
                        <p className="text-xs text-indigo-600 dark:text-indigo-400 capitalize font-medium mt-0.5">
                          {email.event_type ? email.event_type.replace(/_/g, ' ') : (email.detected_status || 'Detected')}
                        </p>
                      </div>
                    </td>
                    <td className="table-td">
                      {getStatusBadge(email.processing_status)}
                    </td>
                    <td className="table-td text-xs text-slate-500 dark:text-slate-400">
                      {new Date(email.received_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                    </td>
                    <td className="table-td text-right">
                      <div className="flex items-center justify-end gap-1">
                        {email.processing_status === 'needs_review' && (
                          <button
                            onClick={() => handleMarkAsReviewed(email.id)}
                            className="p-1.5 rounded-lg text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 transition-colors"
                            title="Mark as Reviewed"
                          >
                            <Check size={16} />
                          </button>
                        )}
                        {email.processing_status !== 'ignored' && (
                          <button
                            onClick={() => handleIgnore(email.id)}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
                            title="Ignore Email"
                          >
                            <EyeOff size={16} />
                          </button>
                        )}
                        {email.application && (
                          <Link
                            to={`/applications/${email.application}`}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
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
        )}
      </div>
    </div>
  );
}
