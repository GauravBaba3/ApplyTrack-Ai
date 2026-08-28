import React from 'react';
import { RefreshCw, CheckCircle2, Clock } from 'lucide-react';
import { useSync } from '../context/SyncContext';

function formatRelativeTime(dateString: string | null): string {
  if (!dateString) return 'Never synced';
  const date = new Date(dateString);
  const now = new Date();
  const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));

  if (diffInMinutes < 1) return 'Just now';
  if (diffInMinutes === 1) return '1 min ago';
  if (diffInMinutes < 60) return `${diffInMinutes} mins ago`;
  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours === 1) return '1 hr ago';
  if (diffInHours < 24) return `${diffInHours} hrs ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export default function GlobalSyncIndicator() {
  const { isSyncing, progress, lastSync, triggerSync } = useSync();

  const cumulative = progress?.cumulative || {
    emails_scanned: progress?.emails_scanned || 0,
    new_applications: progress?.new_applications || 0,
  };

  if (isSyncing) {
    return (
      <div
        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/70 border border-indigo-200 dark:border-indigo-800/80 text-indigo-900 dark:text-indigo-200 text-xs font-semibold shadow-sm animate-pulse"
        title="Gmail background sync in progress"
      >
        <RefreshCw size={13} className="animate-spin text-indigo-600 dark:text-indigo-400 shrink-0" />
        <span className="hidden sm:inline">
          Syncing... {progress?.page ? `(Page ${progress.page}` : ''}
          {cumulative.emails_scanned > 0 ? ` • ${cumulative.emails_scanned} scanned` : ''}
          {progress?.page ? ')' : ''}
        </span>
        <span className="sm:hidden">Syncing...</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => triggerSync(true)}
        className="group inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors border border-transparent hover:border-slate-200 dark:hover:border-slate-700"
        title="Click to manually sync Gmail"
      >
        <RefreshCw size={12} className="text-slate-400 dark:text-slate-500 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors" />
        <span className="hidden sm:inline">
          {formatRelativeTime(lastSync)}
        </span>
      </button>
    </div>
  );
}
