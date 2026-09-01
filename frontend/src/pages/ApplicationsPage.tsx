import React, { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { 
  Search, Plus, Trash2, Briefcase, X, 
  Calendar, MapPin, Globe, ArrowUpRight, ChevronRight, SlidersHorizontal,
  Sparkles, ExternalLink, Filter
} from 'lucide-react';
import { applicationApi } from '../services/api';
import { Application, ApplicationStatus, ApplicationSource } from '../types';
import { useSync } from '../context/SyncContext';
import StatusBadge from '../components/StatusBadge';
import EmptyState from '../components/EmptyState';
import { SkeletonTableRow, SkeletonCard } from '../components/LoadingSkeleton';
import { cacheService, CACHE_TTL } from '../services/cacheService';

export default function ApplicationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [applications, setApplications] = useState<Application[]>(() => {
    const cached = cacheService.get<Application[]>('applications:list', CACHE_TTL.APPLICATIONS);
    return cached || [];
  });
  
  const hasCachedData = applications.length > 0;
  const [loading, setLoading] = useState(!hasCachedData);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | ''>(() => {
    const paramStatus = searchParams.get('status');
    return (paramStatus as ApplicationStatus) || '';
  });
  const [showCreateModal, setShowCreateModal] = useState(false);

  const { dataVersion } = useSync();

  // Check URL params for ?add=true
  useEffect(() => {
    if (searchParams.get('add') === 'true') {
      setShowCreateModal(true);
      searchParams.delete('add');
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const fetchApplications = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const params: any = { ordering: '-application_date' };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      
      const response = await applicationApi.getAll(params);
      const results = response.data?.results || [];
      setApplications(results);
      
      // Only cache unfiltered queries
      if (!searchQuery && !statusFilter) {
        cacheService.set('applications:list', results);
      }
    } catch (error) {
      console.error('Failed to fetch applications:', error);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, statusFilter]);

  useEffect(() => {
    fetchApplications(hasCachedData && !searchQuery && !statusFilter);
  }, [fetchApplications, dataVersion]);

  const handleDelete = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this application?')) {
      try {
        await applicationApi.delete(id);
        cacheService.remove('applications:list');
        cacheService.remove('dashboard:stats');
        cacheService.remove('dashboard:recent');
        cacheService.remove('analytics:data');
        fetchApplications();
      } catch (error) {
        console.error('Failed to delete application:', error);
      }
    }
  };

  const statusOptions: (ApplicationStatus | '')[] = [
    '', 'Applied', 'Under Review', 'Assessment', 'Interview', 'Offer', 'Rejected', 'Withdrawn', 'No Response', 'Stale', 'Ghosted', 'Needs Review'
  ];

  return (
    <div className="space-y-4 sm:space-y-6 pb-12 animate-fade-in w-full max-w-full min-w-0">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
        <div className="min-w-0">
          <h1 className="text-page-title text-slate-900 dark:text-slate-100 truncate">
            Applications
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-0.5 max-w-2xl font-normal leading-relaxed">
            Track, filter, and organize all your job opportunities and recruiter pipelines.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn btn-primary text-xs sm:text-sm shadow-md shadow-indigo-500/20 w-full sm:w-auto justify-center"
        >
          <Plus size={16} />
          <span>Add Application</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-2 p-3 sm:p-4 rounded-2xl sm:rounded-3xl space-y-2.5 sm:space-y-3">
        {/* Search Bar */}
        <div className="relative w-full">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500 shrink-0" size={15} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by company, role, location..."
            className="input pl-9 pr-8 text-xs sm:text-sm py-2 sm:py-2.5"
          />
          {searchQuery && (
            <button 
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-md"
              aria-label="Clear search"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Status Filter Chips Ribbon (Edge-to-Edge scrolling on mobile) */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 -mx-3 px-3 sm:mx-0 sm:px-0 scrollbar-none">
          {statusOptions.map((status) => {
            const isSelected = statusFilter === status;
            return (
              <button
                key={status || 'all'}
                onClick={() => setStatusFilter(status)}
                className={`px-3 py-1 rounded-xl text-[11px] sm:text-xs font-semibold whitespace-nowrap transition-all shrink-0 ${
                  isSelected
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/25 font-bold scale-[1.02]'
                    : 'bg-white/60 dark:bg-white/[0.04] text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-white/[0.08] border border-slate-200/60 dark:border-white/[0.06]'
                }`}
              >
                {status === '' ? 'All Statuses' : status}
              </button>
            );
          })}
        </div>

        {/* Active Filter Hint */}
        {(searchQuery || statusFilter) && (
          <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-white/[0.06] text-xs text-slate-500 dark:text-slate-400">
            <span>
              Showing {applications.length} {applications.length === 1 ? 'result' : 'results'}
            </span>
            <button
              onClick={() => { setSearchQuery(''); setStatusFilter(''); }}
              className="text-indigo-600 dark:text-indigo-400 font-bold hover:underline"
            >
              Reset Filters
            </button>
          </div>
        )}
      </div>

      {/* Main Applications Container: Desktop Table + Mobile Responsive Cards */}
      <div className="glass-2 rounded-2xl sm:rounded-3xl overflow-hidden w-full">
        {loading ? (
          <div className="p-3.5 sm:p-6 space-y-3">
            <div className="md:hidden space-y-3">
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </div>
            <div className="hidden md:block">
              <table className="w-full">
                <tbody>
                  <SkeletonTableRow />
                  <SkeletonTableRow />
                  <SkeletonTableRow />
                </tbody>
              </table>
            </div>
          </div>
        ) : applications.length === 0 ? (
          <div className="p-8 sm:p-12">
            <EmptyState
              icon={Briefcase}
              title={searchQuery || statusFilter ? 'No matching applications' : 'No applications tracked yet'}
              description={
                searchQuery || statusFilter
                  ? 'Try adjusting your search query or status filter.'
                  : 'Get started by syncing your Gmail inbox or manually recording your first application.'
              }
              action={
                searchQuery || statusFilter ? (
                  <button 
                    onClick={() => { setSearchQuery(''); setStatusFilter(''); }} 
                    className="btn btn-secondary text-xs"
                  >
                    Clear Filters
                  </button>
                ) : (
                  <button 
                    onClick={() => setShowCreateModal(true)} 
                    className="btn btn-primary text-xs shadow-sm"
                  >
                    <Plus size={14} />
                    <span>Add First Application</span>
                  </button>
                )
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
                    <th className="table-th">Applied Date</th>
                    <th className="table-th text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70 dark:divide-white/[0.065]">
                  {applications.map((app) => (
                    <tr key={app.id} className="table-row group">
                      <td className="table-td max-w-xs truncate">
                        <Link to={`/applications/${app.id}`} className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-600 dark:text-indigo-400 font-bold flex items-center justify-center text-xs shrink-0 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
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
                        {new Date(app.application_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                      </td>
                      <td className="table-td text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Link
                            to={`/applications/${app.id}`}
                            className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-slate-100 dark:hover:bg-white/[0.08] rounded-xl transition-colors"
                            title="View Details"
                          >
                            <ArrowUpRight size={16} />
                          </Link>
                          <button
                            onClick={() => handleDelete(app.id)}
                            className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-xl transition-colors"
                            title="Delete Application"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Responsive Cards (< 768px: separated cards with clear margin) */}
            <div className="md:hidden p-3 sm:p-4 space-y-3">
              {applications.map((app) => (
                <div 
                  key={app.id} 
                  className="p-3.5 sm:p-4 rounded-2xl bg-white/70 dark:bg-white/[0.03] border border-slate-200/80 dark:border-white/[0.06] shadow-sm space-y-2.5 hover:border-slate-300 dark:hover:border-white/[0.12] transition-all"
                >
                  {/* Top: Avatar, Company, Role, Status */}
                  <div className="flex items-start justify-between gap-2.5">
                    <Link to={`/applications/${app.id}`} className="flex items-start gap-2.5 min-w-0 flex-1">
                      <div className="w-9 h-9 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-bold flex items-center justify-center text-xs shrink-0 border border-indigo-500/20 mt-0.5">
                        {app.company.charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="font-bold text-slate-900 dark:text-slate-100 text-sm truncate leading-tight">
                          {app.company}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5 leading-snug">
                          {app.job_title}
                        </p>
                      </div>
                    </Link>
                    <div className="shrink-0">
                      <StatusBadge status={app.current_status} />
                    </div>
                  </div>

                  {/* Metadata Chips: Date, Source, Location */}
                  <div className="flex items-center gap-1.5 flex-wrap text-[10px] sm:text-[11px] text-slate-500 dark:text-slate-400 font-medium pt-0.5">
                    <span className="inline-flex items-center gap-1 bg-slate-100/80 dark:bg-white/[0.04] px-2 py-0.5 rounded-md">
                      <Calendar size={11} className="text-slate-400 shrink-0" />
                      {new Date(app.application_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                    </span>
                    <span className="inline-flex items-center gap-1 bg-slate-100/80 dark:bg-white/[0.04] px-2 py-0.5 rounded-md">
                      <Globe size={11} className="text-slate-400 shrink-0" />
                      {app.source || 'Direct'}
                    </span>
                    {app.location && (
                      <span className="inline-flex items-center gap-1 bg-slate-100/80 dark:bg-white/[0.04] px-2 py-0.5 rounded-md truncate max-w-[120px]">
                        <MapPin size={11} className="text-slate-400 shrink-0" />
                        <span className="truncate">{app.location}</span>
                      </span>
                    )}
                  </div>

                  {/* Bottom Action Buttons */}
                  <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-100 dark:border-white/[0.04]">
                    <Link
                      to={`/applications/${app.id}`}
                      className="btn btn-secondary text-xs py-1.5 px-3 flex-1 justify-center"
                    >
                      <span>View Details</span>
                      <ChevronRight size={14} />
                    </Link>
                    <button
                      onClick={() => handleDelete(app.id)}
                      className="p-1.5 text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-xl transition-colors shrink-0"
                      title="Delete Application"
                      aria-label="Delete application"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Add Application Glass Modal */}
      {showCreateModal && (
        <CreateApplicationModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            cacheService.remove('applications:list');
            cacheService.remove('dashboard:stats');
            cacheService.remove('dashboard:recent');
            cacheService.remove('analytics:data');
            fetchApplications();
          }}
        />
      )}
    </div>
  );
}

function CreateApplicationModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [formData, setFormData] = useState({
    company: '',
    job_title: '',
    job_url: '',
    location: '',
    source: 'LinkedIn' as ApplicationSource,
    application_date: new Date().toISOString().split('T')[0],
    current_status: 'Applied' as ApplicationStatus,
    notes: '',
  });
  const [loading, setLoading] = useState(false);

  const sourceOptions: ApplicationSource[] = [
    'LinkedIn', 'Indeed', 'Company Website', 'Naukri', 'Wellfound', 'Referral', 'Email', 'Other'
  ];

  const statusOptions: ApplicationStatus[] = [
    'Applied', 'Under Review', 'Assessment', 'Interview', 'Offer', 'Rejected', 'Withdrawn', 'No Response', 'Stale', 'Ghosted', 'Needs Review'
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      await applicationApi.create(formData);
      onSuccess();
    } catch (error) {
      console.error('Failed to create application:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md flex items-center justify-center z-50 p-3 sm:p-4 animate-fade-in">
      <div className="glass-3 w-full max-w-lg max-h-[92dvh] rounded-2xl sm:rounded-3xl flex flex-col overflow-hidden animate-scale-in shadow-2xl">
        <div className="flex items-center justify-between p-4 sm:p-6 border-b border-slate-100 dark:border-white/[0.06] shrink-0">
          <div>
            <h2 className="text-base sm:text-xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">Add Opportunity</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Manually record a new job application</p>
          </div>
          <button 
            onClick={onClose} 
            className="p-1.5 sm:p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/[0.08] rounded-xl transition-colors"
          >
            <X size={18} />
          </button>
        </div>
        
        <div className="overflow-y-auto p-4 sm:p-6">
          <form id="create-app-form" onSubmit={handleSubmit} className="space-y-3.5 sm:space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
              <div>
                <label className="label">Company <span className="text-rose-500">*</span></label>
                <input
                  type="text"
                  value={formData.company}
                  onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                  className="input"
                  placeholder="e.g. Stripe, Google"
                  required
                />
              </div>

              <div>
                <label className="label">Job Title <span className="text-rose-500">*</span></label>
                <input
                  type="text"
                  value={formData.job_title}
                  onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
                  className="input"
                  placeholder="e.g. Software Engineer"
                  required
                />
              </div>
            </div>

            <div>
              <label className="label">Job URL</label>
              <input
                type="url"
                value={formData.job_url}
                onChange={(e) => setFormData({ ...formData, job_url: e.target.value })}
                className="input"
                placeholder="https://company.com/careers/..."
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
              <div>
                <label className="label">Location</label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="input"
                  placeholder="e.g. Remote, San Francisco"
                />
              </div>

              <div>
                <label className="label">Source</label>
                <select
                  value={formData.source}
                  onChange={(e) => setFormData({ ...formData, source: e.target.value as ApplicationSource })}
                  className="input"
                >
                  {sourceOptions.map((source) => (
                    <option key={source} value={source}>{source}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
              <div>
                <label className="label">Application Date <span className="text-rose-500">*</span></label>
                <input
                  type="date"
                  value={formData.application_date}
                  onChange={(e) => setFormData({ ...formData, application_date: e.target.value })}
                  className="input"
                  required
                />
              </div>

              <div>
                <label className="label">Initial Status</label>
                <select
                  value={formData.current_status}
                  onChange={(e) => setFormData({ ...formData, current_status: e.target.value as ApplicationStatus })}
                  className="input"
                >
                  {statusOptions.map((status) => (
                    <option key={status} value={status}>{status}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="label">Notes</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                className="input min-h-[75px] sm:min-h-[85px] resize-y"
                placeholder="Interview stages, recruiter contact, referral notes..."
              />
            </div>
          </form>
        </div>

        <div className="p-3.5 sm:p-6 border-t border-slate-100 dark:border-white/[0.06] bg-slate-50/50 dark:bg-white/[0.02] flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-end gap-2 sm:gap-3 shrink-0">
          <button type="button" onClick={onClose} className="btn btn-secondary justify-center">
            Cancel
          </button>
          <button type="submit" form="create-app-form" disabled={loading} className="btn btn-primary shadow-sm justify-center">
            {loading ? 'Creating...' : 'Save Application'}
          </button>
        </div>
      </div>
    </div>
  );
}
