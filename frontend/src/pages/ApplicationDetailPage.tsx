import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  ArrowLeft, Calendar, Link as LinkIcon, MapPin, Briefcase, Clock, 
  Trash2, Mail, Globe, AlignLeft, Sparkles, Copy, Check, ChevronRight
} from 'lucide-react';
import { applicationApi } from '../services/api';
import { Application, StatusHistory, FollowUp } from '../types';
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
      <div className="space-y-4 sm:space-y-6 pb-12 w-full max-w-full">
        <div className="flex items-center gap-3">
          <SkeletonLine className="w-10 h-10 rounded-xl" />
          <div className="space-y-1.5 flex-1 max-w-sm">
            <SkeletonLine className="h-6 w-full" />
            <SkeletonLine className="h-3.5 w-1/2" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
          <div className="lg:col-span-2 space-y-4">
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <div className="space-y-4">
            <SkeletonCard />
          </div>
        </div>
      </div>
    );
  }

  if (!application) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center p-4 text-center">
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
    <div className="space-y-5 sm:space-y-6 pb-12 animate-fade-in w-full max-w-full min-w-0">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <Link 
            to="/applications" 
            className="p-2 sm:p-2.5 rounded-xl border border-slate-200/80 dark:border-white/[0.08] hover:bg-slate-100 dark:hover:bg-white/[0.08] text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition-colors backdrop-blur-sm shrink-0 mt-0.5"
            aria-label="Back to applications"
          >
            <ArrowLeft size={16} />
          </Link>
          <div className="flex items-start gap-3 min-w-0 flex-1">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-indigo-500/10 dark:bg-indigo-500/15 border border-indigo-500/20 text-indigo-600 dark:text-indigo-400 font-black text-base sm:text-lg flex items-center justify-center shadow-sm shrink-0 backdrop-blur-md mt-0.5">
              {application.company.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100 tracking-tight truncate leading-tight">
                  {application.company}
                </h1>
                <StatusBadge status={application.current_status} />
              </div>
              <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-0.5 font-medium truncate">
                {application.job_title}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 self-stretch sm:self-auto justify-end">
          <button onClick={handleDelete} className="btn btn-danger text-xs w-full sm:w-auto justify-center">
            <Trash2 size={14} />
            <span>Delete</span>
          </button>
        </div>
      </div>

      {/* Detail Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6 items-start">
        {/* Left 2 Cols: Details, Timeline, Notes */}
        <div className="lg:col-span-2 space-y-4 sm:space-y-6 min-w-0">
          {/* Metadata Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="glass-card p-3.5 sm:p-4 rounded-2xl">
              <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 flex items-center gap-1.5 mb-1">
                <Calendar size={12} /> Applied Date
              </span>
              <p className="text-xs sm:text-sm font-bold text-slate-900 dark:text-slate-100">
                {new Date(application.application_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
              </p>
            </div>

            <div className="glass-card p-3.5 sm:p-4 rounded-2xl">
              <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 flex items-center gap-1.5 mb-1">
                <MapPin size={12} /> Location
              </span>
              <p className="text-xs sm:text-sm font-bold text-slate-900 dark:text-slate-100 truncate">
                {application.location || 'Remote / Unspecified'}
              </p>
            </div>

            <div className="glass-card p-3.5 sm:p-4 rounded-2xl">
              <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 flex items-center gap-1.5 mb-1">
                <Globe size={12} /> Source
              </span>
              <p className="text-xs sm:text-sm font-bold text-slate-900 dark:text-slate-100 truncate">
                {application.source || 'Direct'}
              </p>
            </div>
          </div>

          {/* Job URL if present */}
          {application.job_url && (
            <div className="glass-card p-3.5 sm:p-4 rounded-2xl flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                <LinkIcon size={15} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
                <span className="text-xs text-slate-600 dark:text-slate-300 truncate font-medium">{application.job_url}</span>
              </div>
              <a 
                href={application.job_url} 
                target="_blank" 
                rel="noopener noreferrer" 
                className="btn btn-secondary text-xs shrink-0 py-1.5 px-3"
              >
                Open Posting
              </a>
            </div>
          )}

          {/* Notes Section */}
          <div className="glass-card p-4 sm:p-6 rounded-2xl space-y-2.5">
            <h2 className="text-card-title flex items-center gap-2">
              <AlignLeft size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
              Notes & Information
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 whitespace-pre-wrap leading-relaxed font-normal">
              {application.notes || 'No additional notes provided for this application.'}
            </p>
          </div>

          {/* Status Progression Timeline */}
          <div className="glass-card p-4 sm:p-6 rounded-2xl space-y-3.5">
            <h2 className="text-card-title flex items-center gap-2">
              <Clock size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
              Status Timeline
            </h2>

            {statusHistory.length === 0 ? (
              <p className="text-xs text-slate-400 py-3">No historical status updates recorded yet.</p>
            ) : (
              <div className="relative pl-5 sm:pl-6 space-y-5 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 dark:before:bg-white/[0.08]">
                {statusHistory.map((history, idx) => (
                  <div key={idx} className="relative flex items-start gap-3">
                    <div className="absolute -left-5 sm:-left-6 top-1 w-2.5 h-2.5 rounded-full bg-indigo-600 ring-4 ring-white dark:ring-[#0d1424] shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs sm:text-sm font-bold text-slate-900 dark:text-slate-100">
                          {history.previous_status ? `${history.previous_status} → ${history.new_status}` : history.new_status}
                        </span>
                        <span className="text-[11px] text-slate-400 font-medium">
                          {new Date(history.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      {history.source && (
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 font-medium">Source: {history.source}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Col: AI Follow-Up Assistant */}
        <div className="space-y-4 sm:space-y-6 min-w-0">
          <div className="glass-card p-4 sm:p-6 rounded-2xl space-y-3.5">
            <h2 className="text-card-title flex items-center gap-2">
              <Sparkles size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
              AI Follow-up Assistant
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              Generate a personalized recruiter follow-up email tailored to this application status and company.
            </p>

            <button
              onClick={handleGenerateFollowUp}
              disabled={generatingDraft}
              className="btn btn-primary w-full text-xs shadow-sm justify-center"
            >
              <Sparkles size={14} className={generatingDraft ? 'animate-spin' : ''} />
              <span>{generatingDraft ? 'Generating Draft...' : 'Generate Follow-up Draft'}</span>
            </button>

            {followUps.length > 0 && (
              <div className="pt-3 border-t border-slate-100 dark:border-white/[0.06] space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-700 dark:text-slate-300">Latest Draft</span>
                  <button
                    onClick={() => handleCopyDraft(followUps[0].draft_body)}
                    className="inline-flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-semibold"
                  >
                    {copiedDraft ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                    <span>{copiedDraft ? 'Copied!' : 'Copy'}</span>
                  </button>
                </div>
                <div className="p-3.5 rounded-xl bg-white/40 dark:bg-white/[0.02] border border-slate-200/70 dark:border-white/[0.06] backdrop-blur-md text-xs text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto">
                  <p className="font-bold text-slate-900 dark:text-slate-100 mb-1.5">{followUps[0].draft_subject}</p>
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
