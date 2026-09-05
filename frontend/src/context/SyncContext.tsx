import React, { createContext, useContext, useState, useEffect, useRef, useCallback, ReactNode } from 'react';
import { gmailApi, authApi } from '../services/api';
import { SyncStatus, User, CurrentSyncMetrics, GlobalMailboxTotals } from '../types';
import { useToast } from './ToastContext';
import { cacheService } from '../services/cacheService';

/**
 * SyncContext — server-authoritative sync state.
 *
 * Design change: the browser no longer drives the Gmail fetch loop.
 * Instead:
 *  1. triggerSync() calls POST /api/gmail/sync/start/ which returns 202 immediately
 *     and starts a background thread on the server.
 *  2. startPolling() polls GET /api/gmail/sync/status/ every POLL_INTERVAL_MS.
 *  3. On every poll tick dataVersion is bumped so all data-consuming components
 *     (Dashboard, Applications, Email Activity) re-fetch their data automatically.
 *  4. Polling stops when the backend reports status !== 'running' AND the queue
 *     is no longer active.
 *
 * Result: closing / refreshing the browser does NOT stop the sync.  The frontend
 * simply reconnects and picks up the current backend state.
 */

const POLL_INTERVAL_MS = 3000;   // Poll status every 3 seconds during active sync
const IDLE_POLL_MS = 30000;      // Poll every 30 seconds to catch background queue activity
const AUTO_SYNC_INTERVAL_MS = 10 * 60 * 1000; // Trigger a new sync every 10 minutes

// Progress shape exposed through context
export interface SyncProgress {
  status: string;
  sync?: CurrentSyncMetrics;
  global?: GlobalMailboxTotals;
  emails_fetched: number;
  emails_stored: number;
  emails_queued: number;
  emails_processing: number;
  emails_processed: number;
  emails_pending: number;
  job_related: number;
  applications_updated: number;
  new_applications: number;
  page: number;
  has_more: boolean;
  queue: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
    is_active: boolean;
    total_applications: number;
  };
}

interface SyncContextType {
  isSyncing: boolean;
  syncStatus: 'idle' | 'running' | 'completed' | 'failed';
  progress: SyncProgress | null;
  lastSync: string | null;
  error: string | null;
  dataVersion: number;
  triggerSync: (reset?: boolean) => Promise<void>;
}

const SyncContext = createContext<SyncContextType | undefined>(undefined);

export function SyncProvider({ children }: { children: ReactNode }) {
  const { info, success, error: toastError } = useToast();

  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const [progress, setProgress] = useState<SyncProgress | null>(null);
  const [lastSync, setLastSync] = useState<string | null>(
    () => cacheService.get<string>('sync:last_sync')
  );
  const [error, setError] = useState<string | null>(null);
  const [dataVersion, setDataVersion] = useState(0);

  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isMounted = useRef(true);
  const isPolling = useRef(false);
  const hasShownStartToast = useRef(false);
  const lastSyncAttemptTime = useRef<number>(0);

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  const invalidateDatasets = useCallback(() => {
    cacheService.remove('dashboard:stats');
    cacheService.remove('dashboard:analytics');
    cacheService.remove('dashboard:recent');
    cacheService.remove('applications:list');
    cacheService.remove('emails:list');
    cacheService.remove('analytics:data');
    cacheService.remove('analytics:stats');
    cacheService.remove('settings:user');
    setDataVersion((prev) => prev + 1);
  }, []);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    isPolling.current = false;
  }, []);

  /**
   * Poll /api/gmail/sync/status/ and update UI state.
   * Returns true if sync is still running (caller should keep polling).
   */
  const pollStatus = useCallback(async (): Promise<boolean> => {
    if (!isMounted.current) return false;
    try {
      const res = await gmailApi.getStatus();
      const data: SyncStatus = res.data;
      if (!isMounted.current) return false;

      const backendStatus = data?.status || 'idle';
      const isRunning = backendStatus === 'running';
      const queueActive = data?.queue?.is_active === true;

      const syncMetrics = data?.sync;
      const globalTotals = data?.global;

      // Build progress from the richer status fields
      const prog: SyncProgress = {
        status: backendStatus,
        sync: syncMetrics,
        global: globalTotals,
        emails_fetched: syncMetrics?.fetched ?? (data as any).emails_fetched ?? data?.stats?.emails_scanned ?? 0,
        emails_stored: syncMetrics?.stored ?? (data as any).emails_stored ?? 0,
        emails_queued: syncMetrics?.queued ?? (data as any).emails_queued ?? 0,
        emails_processing: syncMetrics?.processing ?? (data as any).emails_processing ?? (data?.queue?.processing ?? 0),
        emails_processed: syncMetrics?.processed ?? (data as any).emails_processed ?? (data?.queue?.completed ?? 0),
        emails_pending: syncMetrics?.pending ?? (data as any).emails_pending ?? (data?.queue?.pending ?? 0),
        job_related: syncMetrics?.job_related ?? (data as any).job_related ?? data?.stats?.job_related_emails ?? 0,
        applications_updated: syncMetrics?.applications_updated ?? (data as any).applications_updated ?? data?.stats?.applications_updated ?? 0,
        new_applications: syncMetrics?.new_applications ?? (data as any).new_applications ?? data?.stats?.new_applications ?? 0,
        page: syncMetrics?.page ?? data?.page ?? 0,
        has_more: syncMetrics?.has_more ?? data?.has_more ?? false,
        queue: data?.queue ?? {
          pending: 0, processing: 0, completed: 0, failed: 0,
          is_active: false, total_applications: 0,
        },
      };

      setProgress(prog);
      setIsSyncing(isRunning || queueActive);

      if (isRunning || queueActive) {
        setSyncStatus('running');
        // Invalidate cache on every poll tick so UI counters increment in real-time
        invalidateDatasets();

        if (!hasShownStartToast.current) {
          info('Gmail sync running', 'Importing and processing emails in the background...');
          hasShownStartToast.current = true;
        }
        return true; // keep polling
      } else {
        // Sync is no longer active
        setSyncStatus(backendStatus === 'failed' ? 'failed' : 'completed');
        invalidateDatasets();

        if (data?.last_sync) {
          const nowIso = typeof data.last_sync === 'string' ? data.last_sync : new Date(data.last_sync).toISOString();
          setLastSync(nowIso);
          cacheService.set('sync:last_sync', nowIso);
        }

        if (backendStatus === 'failed') {
          setError('Sync encountered an error. Will retry automatically.');
          toastError('Gmail sync failed', 'Check your connection and try again.');
        } else if (hasShownStartToast.current) {
          // Only show completion toast if we previously showed a start toast
          const processed = prog.emails_processed;
          const apps = prog.applications_updated || prog.new_applications;
          success(
            'Sync complete',
            processed > 0
              ? `${processed} emails processed${apps > 0 ? `, ${apps} applications updated` : ''}.`
              : 'Mailbox is up to date.'
          );
          hasShownStartToast.current = false;
        }

        return false; // stop polling
      }
    } catch {
      // Transient network error — keep polling (don't abort sync watch)
      return isMounted.current;
    }
  }, [info, success, toastError, invalidateDatasets]);

  /**
   * Start polling the status endpoint.
   * Uses an interval so it keeps running regardless of React component lifecycle.
   */
  const startPolling = useCallback(() => {
    if (isPolling.current) return;
    isPolling.current = true;

    // Poll immediately, then set up interval
    pollStatus();

    pollTimerRef.current = setInterval(async () => {
      if (!isMounted.current) {
        stopPolling();
        return;
      }
      const stillRunning = await pollStatus();
      if (!stillRunning) {
        stopPolling();
        // Switch to slow idle polling to catch any future queue activity
        pollTimerRef.current = setInterval(async () => {
          if (!isMounted.current) {
            stopPolling();
            return;
          }
          const res = await gmailApi.getStatus().catch(() => null);
          if (res?.data?.queue?.is_active) {
            stopPolling();
            startPolling(); // re-enter fast polling
          }
        }, IDLE_POLL_MS);
      }
    }, POLL_INTERVAL_MS);
  }, [pollStatus, stopPolling]);

  /**
   * Trigger a Gmail sync.
   * Calls POST /api/gmail/sync/start/ which returns 202 immediately.
   * The actual sync runs server-side in a background thread.
   */
  const triggerSync = useCallback(async (reset: boolean = true) => {
    lastSyncAttemptTime.current = Date.now();
    setError(null);

    try {
      // Tell the server to start (or resume) a sync
      await gmailApi.start({ reset });

      if (!isMounted.current) return;

      setSyncStatus('running');
      setIsSyncing(true);

      // Start / ensure we're polling for updates
      stopPolling();
      hasShownStartToast.current = false;
      startPolling();
    } catch (err: any) {
      if (isMounted.current) {
        const errMsg = err.response?.data?.error || err.message || 'Sync failed to start';
        setError(errMsg);
        toastError('Sync failed', errMsg);
      }
    }
  }, [startPolling, stopPolling, toastError]);

  // On mount: check current backend sync state and resume polling if needed
  useEffect(() => {
    let cancelled = false;

    const checkAndResume = async () => {
      try {
        const meRes = await authApi.getMe();
        if (cancelled || !isMounted.current) return;
        const user: User = meRes.data;
        if (!user || !user.gmail_connected) return;

        // Scope cache to this user
        cacheService.setUser(user.id);

        if (user.gmail_last_sync) {
          setLastSync(user.gmail_last_sync);
          cacheService.set('sync:last_sync', user.gmail_last_sync);
        }

        // Check current backend state
        const statusRes = await gmailApi.getStatus();
        if (cancelled || !isMounted.current) return;
        const statusData: SyncStatus = statusRes.data;

        if (statusData?.status === 'running' || statusData?.queue?.is_active) {
          // Sync is running on the server — start polling immediately
          setSyncStatus('running');
          setIsSyncing(true);
          startPolling();
          return;
        }

        // Not currently running. Auto-trigger if never synced or overdue.
        const lastSyncDate = user.gmail_last_sync ? new Date(user.gmail_last_sync) : null;
        const isNeverSynced = !lastSyncDate;
        const isDue = lastSyncDate && (Date.now() - lastSyncDate.getTime()) > AUTO_SYNC_INTERVAL_MS;

        if (isNeverSynced || isDue) {
          triggerSync(false);
        } else {
          // Start slow idle polling to catch any background queue activity
          startPolling();
        }
      } catch {
        // Silently skip — user may not be logged in yet
      }
    };

    checkAndResume();
    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Periodic 10-minute auto sync
  useEffect(() => {
    const id = setInterval(() => {
      if (!isSyncing && isMounted.current) {
        triggerSync(false);
      }
    }, AUTO_SYNC_INTERVAL_MS);
    return () => clearInterval(id);
  }, [isSyncing, triggerSync]);

  // Smart visibility / online recovery
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible' && navigator.onLine && isMounted.current) {
        const cooldown = AUTO_SYNC_INTERVAL_MS;
        if (Date.now() - lastSyncAttemptTime.current > cooldown) {
          triggerSync(false);
        } else if (!isPolling.current) {
          // Even if not overdue, resume polling to pick up server-side progress
          startPolling();
        }
      }
    };

    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('online', onVisible);
    return () => {
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('online', onVisible);
    };
  }, [triggerSync, startPolling]);

  return (
    <SyncContext.Provider
      value={{
        isSyncing,
        syncStatus,
        progress,
        lastSync,
        error,
        dataVersion,
        triggerSync,
      }}
    >
      {children}
    </SyncContext.Provider>
  );
}

export function useSync() {
  const context = useContext(SyncContext);
  if (!context) {
    throw new Error('useSync must be used within a SyncProvider');
  }
  return context;
}
