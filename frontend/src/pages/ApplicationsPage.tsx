import React, { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { 
  Search, Filter, Plus, Edit, Trash2, Eye, Briefcase, X, 
  MoreVertical, Calendar, MapPin, Globe, ArrowUpRight 
} from 'lucide-react';
import { applicationApi } from '../services/api';
import { Application, ApplicationStatus, ApplicationSource } from '../types';
import { useSync } from '../context/SyncContext';
import PageHeader from '../components/PageHeader';
import StatusBadge from '../components/StatusBadge';
import EmptyState from '../components/EmptyState';
import { SkeletonTableRow } from '../components/LoadingSkeleton';
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
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | ''>('');
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
      
      // Only cache unfiltered queries to avoid cache pollution
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
    '', 'Applied', 'Assessment', 'Interview', 'Offer', 'Rejected', 'Pending', 'No Response'
  ];

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <PageHeader 
        title="Applications" 
        description="Track, filter, and organize all your active job applications in one place."
      >
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn btn-primary shadow-sm"
        >
          <Plus size={16} />
          <span>Add Application</span>
        </button>
      </PageHeader>

      {/* Filter and Search Bar */}
      <div className="card p-4 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        {/* Search Bar */}
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500" size={16} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by company, role, location..."
            className="input pl-10"
          />
          {searchQuery && (
            <button 
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
          {statusOptions.map((status) => (
            <button
              key={status || 'all'}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                statusFilter === status
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              {status === '' ? 'All Applications' : status}
            </button>
          ))}
        </div>
      </div>

      {/* Main Applications Table Card */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-6">
            <table className="w-full">
              <tbody>
                <SkeletonTableRow />
                <SkeletonTableRow />
                <SkeletonTableRow />
                <SkeletonTableRow />
              </tbody>
            </table>
          </div>
        ) : applications.length === 0 ? (
          <div className="p-12">
            <EmptyState
              icon={Briefcase}
              title={searchQuery || statusFilter ? 'No matching applications' : 'No applications tracked yet'}
              description={
                searchQuery || statusFilter
                  ? 'Try adjusting your search criteria or filter to find what you are looking for.'
                  : 'Get started by syncing your Gmail inbox or manually tracking your first application.'
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
                    className="btn btn-primary text-xs"
                  >
                    <Plus size={14} />
                    <span>Add First Application</span>
                  </button>
                )
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
                  <th className="table-th">Source</th>
                  <th className="table-th">Applied Date</th>
                  <th className="table-th text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {applications.map((app) => (
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
                    <td className="table-td text-xs text-slate-500 dark:text-slate-400 font-medium">
                      {app.source || 'Direct'}
                    </td>
                    <td className="table-td text-xs text-slate-500 dark:text-slate-400">
                      {new Date(app.application_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                    </td>
                    <td className="table-td text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Link
                          to={`/applications/${app.id}`}
                          className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                          title="View Details"
                        >
                          <ArrowUpRight size={16} />
                        </Link>
                        <button
                          onClick={() => handleDelete(app.id)}
                          className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-lg transition-colors"
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
        )}
      </div>

      {/* Add Application Modal */}
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
    'Applied', 'Assessment', 'Interview', 'Offer', 'Rejected', 'Pending', 'No Response'
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
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 w-full max-w-lg max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between p-6 border-b border-slate-100 dark:border-slate-800 shrink-0">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Add Application</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Manually record a new job application</p>
          </div>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors">
            <X size={18} />
          </button>
        </div>
        
        <div className="overflow-y-auto p-6">
          <form id="create-app-form" onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                className="input min-h-[90px] resize-y"
                placeholder="Interview stages, recruiter contact, referral notes..."
              />
            </div>
          </form>
        </div>

        <div className="p-6 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 flex items-center justify-end gap-3 shrink-0">
          <button type="button" onClick={onClose} className="btn btn-secondary">
            Cancel
          </button>
          <button type="submit" form="create-app-form" disabled={loading} className="btn btn-primary">
            {loading ? 'Creating...' : 'Save Application'}
          </button>
        </div>
      </div>
    </div>
  );
}
