import React, { createContext, useContext, useState, useEffect, useRef, useCallback, ReactNode } from 'react';
import { gmailApi, authApi } from '../services/api';
import { SyncSummary, SyncStatus, User } from '../types';
import { useToast } from './ToastContext';
import { cacheService } from '../services/cacheService';

const GMAIL_AUTO_SYNC_INTERVAL_MS = 10 * 60 * 1000; // 10 minutes
const QUEUE_POLL_INTERVAL_MS = 2500; // 2.5 seconds during active queue processing

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

  const monitorQueueProcessing = useCallback(async () => {
    // Poll queue processing until all jobs complete
    let pollCount = 0;
    const maxPolls = 60; // Up to ~2.5 minutes of continuous monitoring

    while (isMounted.current && pollCount < maxPolls) {
      pollCount++;
      await new Promise((resolve) => setTimeout(resolve, QUEUE_POLL_INTERVAL_MS));
      if (!isMounted.current) break;

      try {
        const statusRes = await gmailApi.getStatus();
        const statusData: SyncStatus = statusRes.data;

        if (statusData?.queue) {
          const { pending, processing, completed, failed, is_active, total_applications } = statusData.queue;
          
          // Invalidate cache and bump version on every poll step so UI increments in real-time
          invalidateDatasets();

          if (!is_active || (pending === 0 && processing === 0)) {
            // All background jobs completed
            success(
              'Processing completed',
              `${total_applications || 0} applications tracked and pipeline updated.`
            );
            break;
          }
        } else {
          invalidateDatasets();
          break;
        }
      } catch (err) {
        // Continue loop if a single status check has a temporary network glitch
      }
    }
  }, [invalidateDatasets, success]);

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
      let consecutiveErrors = 0;

      try {
        // Phase 1: Gmail Ingestion Loop with Automatic Resumption
        while (isMounted.current) {
          try {
            const response = await gmailApi.sync({ reset: isReset });
            isReset = false;
            consecutiveErrors = 0;
            const data: SyncSummary = response.data;

            if (!isMounted.current) break;

            setProgress(data);
            cacheService.set('sync:progress', data);
            invalidateDatasets();

            // Show "Gmail sync started" toast once per session
            if (!hasShownStartToast) {
              info('Gmail sync started', "Importing messages and processing in background...");
              hasShownStartToast = true;
            }

            // Check if ingestion finished
            if (!data.has_more || data.status === 'completed' || data.status === 'failed') {
              if (data.status === 'failed') {
                const errMsg = data.message || 'Sync encountered an error';
                setError(errMsg);
                setSyncStatus('failed');
                toastError('Gmail sync failed', errMsg);
              } else {
                setSyncStatus('completed');
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

                info('Gmail import completed', msg);
                const nowIso = new Date().toISOString();
                setLastSync(nowIso);
                cacheService.set('sync:last_sync', nowIso);
                invalidateDatasets();
              }
              break;
            }

            // Controlled delay between batches (1.5 seconds)
            await new Promise((resolve) => setTimeout(resolve, 1500));
          } catch (batchErr: any) {
            consecutiveErrors++;
            if (consecutiveErrors <= 3) {
              info('Sync interrupted', 'Retrying automatically from checkpoint...');
              await new Promise((resolve) => setTimeout(resolve, 3000));
              continue;
            }
            throw batchErr;
          }
        }

        // Phase 2: Background Worker Queue Monitoring & Progressive UI Updates
        if (isMounted.current) {
          await monitorQueueProcessing();
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
          setSyncStatus('idle');
          invalidateDatasets();
        }
        isLoopRunning.current = false;
      }
    },
    [info, success, toastError, invalidateDatasets, monitorQueueProcessing]
  );

  // Check sync status and auto-resume on application mount
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

        // Check if there is an in-progress historical sync or active queue to auto-resume
        try {
          const statusRes = await gmailApi.getStatus();
          const statusData: SyncStatus = statusRes.data;

          if (statusData?.status === 'running' || statusData?.has_more) {
            // Automatically resume interrupted sync from persisted checkpoint
            runSyncLoop(false);
            return;
          } else if (statusData?.queue?.is_active) {
            // Automatically resume observing queue processing
            monitorQueueProcessing();
          }
        } catch (statusErr) {
          // Fall through to normal interval check
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
  }, [runSyncLoop, monitorQueueProcessing]);

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
