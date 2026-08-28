import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  ArrowLeft, Calendar, Link as LinkIcon, MapPin, Briefcase, Clock, 
  Edit, Trash2, Mail, Plus, X, Globe, Building2, AlignLeft, Send, 
  CheckCircle2, Sparkles, Copy, Check 
} from 'lucide-react';
import { applicationApi } from '../services/api';
import { Application, StatusHistory, FollowUp } from '../types';
import PageHeader from '../components/PageHeader';
import StatusBadge from '../components/StatusBadge';
import EmptyState from '../components/EmptyState';
import { SkeletonCard, SkeletonLine } from '../components/LoadingSkeleton';
import { cacheService, CACHE_TTL } from '../services/cacheService';

export default function ApplicationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [application, setApplication] = useState<Application | null>(() => {
    return id ? cacheService.get<Application>(`application:detail:${id}`, CACHE_TTL.APPLICATIONS) : null;
  });
  const [statusHistory, setStatusHistory] = useState<StatusHistory[]>([]);
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [loading, setLoading] = useState(!application);
  const [copiedDraft, setCopiedDraft] = useState(false);
  const [generatingDraft, setGeneratingDraft] = useState(false);

  useEffect(() => {
    if (id) fetchData(Boolean(application));
  }, [id]);

  const fetchData = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const [appRes, historyRes, followUpsRes] = await Promise.all([
        applicationApi.getById(Number(id)).catch(() => ({ data: null })),
        applicationApi.getStatusHistory(Number(id)).catch(() => ({ data: { results: [] } })),
        applicationApi.getFollowUps(Number(id)).catch(() => ({ data: { results: [] } }))
      ]);
      
      if (appRes.data) {
        setApplication(appRes.data);
        cacheService.set(`application:detail:${id}`, appRes.data);
      }
      if (historyRes.data) setStatusHistory(historyRes.data.results || []);
      if (followUpsRes.data) setFollowUps(followUpsRes.data.results || []);
    } catch (error) {
      console.error('Failed to fetch application details:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this application? This action cannot be undone.')) {
      try {
        await applicationApi.delete(Number(id));
        cacheService.remove(`application:detail:${id}`);
        cacheService.remove('applications:list');
        cacheService.remove('dashboard:stats');
        cacheService.remove('dashboard:recent');
        cacheService.remove('analytics:data');
        navigate('/applications');
      } catch (error) {
        console.error('Failed to delete application:', error);
      }
    }
  };

  const handleGenerateFollowUp = async () => {
    try {
      setGeneratingDraft(true);
      await applicationApi.generateFollowUpDraft(Number(id));
      fetchData(true);
    } catch (error) {
      console.error('Failed to generate follow-up:', error);
    } finally {
      setGeneratingDraft(false);
    }
  };

  const handleCopyDraft = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedDraft(true);
    setTimeout(() => setCopiedDraft(false), 2000);
  };

  if (loading) {
    return (
      <div className="space-y-6 pb-12">
        <div className="flex gap-4">
          <SkeletonLine className="w-12 h-12 rounded-2xl" />
          <div className="space-y-2 flex-1 max-w-sm">
            <SkeletonLine className="h-8 w-full" />
            <SkeletonLine className="h-4 w-1/2" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <div className="space-y-6">
            <SkeletonCard />
          </div>
        </div>
      </div>
    );
  }

  if (!application) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center p-8">
        <EmptyState 
          icon={Briefcase}
          title="Application not found"
          description="The application you're looking for doesn't exist or may have been deleted."
          action={
            <Link to="/applications" className="btn btn-primary mt-4">
              <ArrowLeft size={16} /> Back to Applications
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-12">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link to="/applications" className="p-2.5 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition-colors">
            <ArrowLeft size={18} />
          </Link>
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-100 dark:border-indigo-900/50 text-indigo-600 dark:text-indigo-400 font-black text-lg flex items-center justify-center shadow-sm shrink-0">
              {application.company.charAt(0).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-2xl font-black text-slate-900 dark:text-slate-100 tracking-tight">{application.company}</h1>
                <StatusBadge status={application.current_status} />
              </div>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{application.job_title}</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          <button onClick={handleDelete} className="btn btn-danger text-xs">
            <Trash2 size={15} />
            <span>Delete</span>
          </button>
        </div>
      </div>

      {/* Detail Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8 items-start">
        {/* Left 2 Cols: Details, Timeline, Notes */}
        <div className="lg:col-span-2 space-y-6">
          {/* Metadata Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <div className="card p-4">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 flex items-center gap-1.5 mb-1">
                <Calendar size={13} /> Applied Date
              </span>
              <p className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {new Date(application.application_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
              </p>
            </div>

            <div className="card p-4">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 flex items-center gap-1.5 mb-1">
                <MapPin size={13} /> Location
              </span>
              <p className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">
                {application.location || 'Remote / Unspecified'}
              </p>
            </div>

            <div className="card p-4">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 flex items-center gap-1.5 mb-1">
                <Globe size={13} /> Source
              </span>
              <p className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {application.source || 'Direct'}
              </p>
            </div>
          </div>

          {/* Job URL if present */}
          {application.job_url && (
            <div className="card p-4 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 min-w-0">
                <LinkIcon size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
                <span className="text-xs text-slate-600 dark:text-slate-300 truncate">{application.job_url}</span>
              </div>
              <a 
                href={application.job_url} 
                target="_blank" 
                rel="noopener noreferrer" 
                className="btn btn-secondary text-xs shrink-0 py-1 px-3"
              >
                Open Posting
              </a>
            </div>
          )}

          {/* Notes Section */}
          <div className="card p-6 space-y-3">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <AlignLeft size={16} className="text-indigo-600 dark:text-indigo-400" />
              Notes & Information
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">
              {application.notes || 'No additional notes provided for this application.'}
            </p>
          </div>

          {/* Status Progression Timeline */}
          <div className="card p-6 space-y-4">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Clock size={16} className="text-indigo-600 dark:text-indigo-400" />
              Status Progression Timeline
            </h2>

            {statusHistory.length === 0 ? (
              <p className="text-xs text-slate-400 py-4">No historical status updates recorded yet.</p>
            ) : (
              <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 dark:before:bg-slate-800">
                {statusHistory.map((history, idx) => (
                  <div key={idx} className="relative flex items-start gap-3.5">
                    <div className="absolute -left-6 top-1 w-3 h-3 rounded-full bg-indigo-600 ring-4 ring-white dark:ring-slate-900 shrink-0" />
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-bold text-slate-900 dark:text-slate-100">
                          {history.previous_status ? `${history.previous_status} → ${history.new_status}` : history.new_status}
                        </span>
                        <span className="text-xs text-slate-400">
                          {new Date(history.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      {history.source && (
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Source: {history.source}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Col: AI Follow-Up Assistant */}
        <div className="space-y-6">
          <div className="card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Sparkles size={16} className="text-indigo-600 dark:text-indigo-400" />
                AI Follow-up Assistant
              </h2>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              Generate a personalized, polite recruiter follow-up email tailored to this application status and company.
            </p>

            <button
              onClick={handleGenerateFollowUp}
              disabled={generatingDraft}
              className="btn btn-primary w-full text-xs shadow-sm"
            >
              <Sparkles size={14} className={generatingDraft ? 'animate-spin' : ''} />
              <span>{generatingDraft ? 'Generating Draft...' : 'Generate Follow-up Draft'}</span>
            </button>

            {followUps.length > 0 && (
              <div className="pt-4 border-t border-slate-100 dark:border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-700 dark:text-slate-300">Latest Draft</span>
                  <button
                    onClick={() => handleCopyDraft(followUps[0].draft_body)}
                    className="inline-flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-semibold"
                  >
                    {copiedDraft ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
                    <span>{copiedDraft ? 'Copied!' : 'Copy to Clipboard'}</span>
                  </button>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto">
                  <p className="font-bold text-slate-900 dark:text-slate-100 mb-1">{followUps[0].draft_subject}</p>
                  {followUps[0].draft_body}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
