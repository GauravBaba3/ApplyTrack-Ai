import React from 'react';
import { BarChart3, RefreshCw, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';

interface AnalyticsEmptyStateProps {
  onSync: () => void;
  isSyncing: boolean;
}

export default function AnalyticsEmptyState({ onSync, isSyncing }: AnalyticsEmptyStateProps) {
  return (
    <div className="glass-2 p-8 sm:p-14 rounded-3xl text-center max-w-lg mx-auto my-8 space-y-5">
      <div className="w-14 h-14 rounded-3xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mx-auto shadow-md border border-indigo-500/20">
        <BarChart3 size={28} />
      </div>

      <div className="space-y-1.5">
        <h2 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
          No Application Data Yet
        </h2>
        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto leading-relaxed">
          Sync your Gmail inbox to discover recruiter emails or record your first job application to populate your intelligence metrics and conversion funnel.
        </p>
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
        <button
          onClick={onSync}
          disabled={isSyncing}
          className="btn btn-primary text-xs shadow-md shadow-indigo-500/25 w-full sm:w-auto justify-center"
        >
          <RefreshCw size={14} className={isSyncing ? 'animate-spin' : ''} />
          <span>{isSyncing ? 'Syncing...' : 'Sync Gmail Mailbox'}</span>
        </button>

        <Link
          to="/applications?add=true"
          className="btn btn-secondary text-xs w-full sm:w-auto justify-center"
        >
          <Plus size={14} />
          <span>Add First Application</span>
        </Link>
      </div>
    </div>
  );
}
