import React, { createContext, useContext, useState, useEffect, useRef, useCallback, ReactNode } from 'react';
import { gmailApi, authApi } from '../services/api';
import { SyncSummary, User } from '../types';
import { useToast } from './ToastContext';

import { cacheService } from '../services/cacheService';

const GMAIL_AUTO_SYNC_INTERVAL_MS = 10 * 60 * 1000; // 10 minutes

interface SyncContextType {
  isSyncing: boolean;
  syncStatus: 'idle' | 'running' | 'completed' | 'failed';
  progress: SyncSummary | null;
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
  const [progress, setProgress] = useState<SyncSummary | null>(() => cacheService.get<SyncSummary>('sync:progress'));
  const [lastSync, setLastSync] = useState<string | null>(() => cacheService.get<string>('sync:last_sync'));
  const [error, setError] = useState<string | null>(null);
  const [dataVersion, setDataVersion] = useState(0);

  const isLoopRunning = useRef(false);
  const isMounted = useRef(true);
  const lastSyncAttemptTime = useRef<number>(Date.now());

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  const runSyncLoop = useCallback(
    async (reset: boolean = false) => {
      if (isLoopRunning.current) return;
      isLoopRunning.current = true;
      lastSyncAttemptTime.current = Date.now();
      setIsSyncing(true);
      setSyncStatus('running');
      setError(null);

      let isReset = reset;
      let hasShownStartToast = false;

      try {
        while (isMounted.current) {
          const response = await gmailApi.sync({ reset: isReset });
          isReset = false;
          const data: SyncSummary = response.data;

          if (!isMounted.current) break;

          setProgress(data);
          cacheService.set('sync:progress', data);

          // Increment dataVersion to notify open pages to re-fetch reactively
          setDataVersion((prev) => prev + 1);

          // Show "Gmail sync started" toast only once per sync session
          if (!hasShownStartToast) {
            info('Gmail sync started', "We're processing your emails in the background.");
            hasShownStartToast = true;
          }

          // Check for completion or termination
          if (!data.has_more || data.status === 'completed' || data.status === 'failed') {
            setSyncStatus(data.status || 'completed');
            if (data.status === 'failed') {
              const errMsg = data.message || 'Sync encountered an error';
              setError(errMsg);
              toastError('Gmail sync failed', errMsg);
            } else {
              // Successfully completed whole sync cycle
              const cumulative = data.cumulative || {
                emails_scanned: data.emails_scanned || 0,
                job_related_emails: data.job_related_emails || 0,
                applications_updated: data.applications_updated || 0,
                new_applications: data.new_applications || 0,
              };

              const msg =
                cumulative.emails_scanned > 0
                  ? `${cumulative.emails_scanned} emails imported and queued for processing.`
                  : 'Mailbox is up to date.';

              success('Gmail sync completed', msg);
              const nowIso = new Date().toISOString();
              setLastSync(nowIso);
              cacheService.set('sync:last_sync', nowIso);

              // Invalidate cached datasets so pages fetch latest server state
              cacheService.remove('dashboard:stats');
              cacheService.remove('dashboard:analytics');
              cacheService.remove('dashboard:recent');
              cacheService.remove('applications:list');
              cacheService.remove('emails:list');
              cacheService.remove('analytics:data');
              cacheService.remove('settings:user');
            }
            break;
          }

          // Controlled delay between batches (1.5 seconds)
          await new Promise((resolve) => setTimeout(resolve, 1500));
        }
      } catch (err: any) {
        if (isMounted.current) {
          console.error('Global background Gmail sync failed:', err);
          const errMsg = err.response?.data?.error || err.message || 'Sync failed';
          setError(errMsg);
          setSyncStatus('failed');
          toastError('Gmail sync failed', errMsg);
        }
      } finally {
        if (isMounted.current) {
          setIsSyncing(false);
        }
        isLoopRunning.current = false;
      }
    },
    [info, success, toastError]
  );

  // Check sync status and set user on application mount
  useEffect(() => {
    let cancel = false;

    const checkAndAutoSync = async () => {
      try {
        const meRes = await authApi.getMe();
        if (cancel) return;
        const user: User = meRes.data;

        if (!user) return;

        // Scope cacheService to this user
        cacheService.setUser(user.id);

        if (!user.gmail_connected) {
          return;
        }

        if (user.gmail_last_sync) {
          setLastSync(user.gmail_last_sync);
          cacheService.set('sync:last_sync', user.gmail_last_sync);
        }

        const lastSyncDate = user.gmail_last_sync ? new Date(user.gmail_last_sync) : null;
        const now = new Date();

        // If never synced: auto-trigger initial sync
        // If last sync was > 10 minutes ago: auto-trigger lightweight incremental sync
        const isNeverSynced = !lastSyncDate;
        const isDue = lastSyncDate && now.getTime() - lastSyncDate.getTime() > GMAIL_AUTO_SYNC_INTERVAL_MS;

        if (isNeverSynced || isDue) {
          runSyncLoop(false);
        }
      } catch (err) {
        console.debug('Auto-sync check skipped:', err);
      }
    };

    checkAndAutoSync();
    return () => {
      cancel = true;
    };
  }, [runSyncLoop]);

  // Periodic 10-minute incremental sync interval
  useEffect(() => {
    const intervalId = setInterval(() => {
      if (!isLoopRunning.current) {
        runSyncLoop(false);
      }
    }, GMAIL_AUTO_SYNC_INTERVAL_MS);

    return () => {
      clearInterval(intervalId);
    };
  }, [runSyncLoop]);

  // Visibility and online listeners for smart sync recovery
  useEffect(() => {
    const handleVisibilityOrOnline = () => {
      if (document.visibilityState === 'visible' && navigator.onLine) {
        const now = Date.now();
        // Cooldown: at least 10 minutes since last attempt before auto-triggering on tab focus
        if (now - lastSyncAttemptTime.current > GMAIL_AUTO_SYNC_INTERVAL_MS && !isLoopRunning.current) {
          runSyncLoop(false);
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityOrOnline);
    window.addEventListener('online', handleVisibilityOrOnline);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityOrOnline);
      window.removeEventListener('online', handleVisibilityOrOnline);
    };
  }, [runSyncLoop]);

  const triggerSync = useCallback(
    async (reset: boolean = true) => {
      return runSyncLoop(reset);
    },
    [runSyncLoop]
  );

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
