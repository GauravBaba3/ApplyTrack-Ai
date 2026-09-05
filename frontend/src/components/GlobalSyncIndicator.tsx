import React from 'react';
import { RefreshCw } from 'lucide-react';
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

  const fetched = progress?.emails_fetched ?? 0;
  const processed = progress?.emails_processed ?? 0;

  if (isSyncing) {
    return (
      <div
        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-indigo-500/10 dark:bg-indigo-500/15 border border-indigo-500/25 text-indigo-700 dark:text-indigo-300 text-xs font-semibold backdrop-blur-md animate-pulse shadow-sm"
        title="Gmail background sync in progress — runs server-side, survives refresh"
      >
        <RefreshCw size={13} className="animate-spin text-indigo-600 dark:text-indigo-400 shrink-0" />
        <span className="hidden sm:inline">
          Syncing{fetched > 0 ? ` • ${fetched} fetched` : ''}
          {processed > 0 ? ` • ${processed} processed` : ''}
        </span>
        <span className="sm:hidden">Syncing...</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => triggerSync(true)}
        className="group inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-white/80 dark:hover:bg-white/[0.06] transition-all border border-transparent hover:border-slate-200/80 dark:hover:border-white/[0.08] backdrop-blur-sm"
        title="Click to manually sync Gmail"
      >
        <RefreshCw size={12} className="text-slate-400 dark:text-slate-500 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors" />
        <span className="hidden sm:inline font-medium">
          {formatRelativeTime(lastSync)}
        </span>
      </button>
    </div>
  );
}

