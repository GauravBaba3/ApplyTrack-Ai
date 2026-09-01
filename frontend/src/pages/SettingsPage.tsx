import React, { useState, useEffect, useCallback } from 'react';
import { 
  Mail, CheckCircle2, XCircle, Clock, RefreshCw, AlertTriangle, Sliders 
} from 'lucide-react';
import { authApi } from '../services/api';
import { User, UserSettings } from '../types';
import { useSync } from '../context/SyncContext';
import { SkeletonCard } from '../components/LoadingSkeleton';
import { cacheService, CACHE_TTL } from '../services/cacheService';

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(() => 
    cacheService.get<User>('settings:user', CACHE_TTL.SETTINGS)
  );
  const [settings, setSettings] = useState<UserSettings | null>(() => 
    cacheService.get<UserSettings>('settings:data', CACHE_TTL.SETTINGS)
  );
  
  const hasCachedData = Boolean(user || settings);
  const [loading, setLoading] = useState(!hasCachedData);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [staleThreshold, setStaleThreshold] = useState<number>(user?.stale_application_threshold || 14);

  const { dataVersion, lastSync, triggerSync } = useSync();

  const fetchData = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const [userResponse, settingsResponse] = await Promise.all([
        authApi.getMe().catch(() => ({ data: null })),
        authApi.getSettings().catch(() => ({ data: null }))
      ]);

      if (userResponse.data) {
        setUser(userResponse.data);
        setStaleThreshold(userResponse.data.stale_application_threshold || 14);
        cacheService.set('settings:user', userResponse.data);
      }
      if (settingsResponse.data) {
        setSettings(settingsResponse.data);
        cacheService.set('settings:data', settingsResponse.data);
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(hasCachedData);
  }, [fetchData, dataVersion]);

  const handleUpdateSettings = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    try {
      setSaving(true);
      await authApi.updateSettings({ ...settings, stale_application_threshold: staleThreshold });
      setSavedSuccess(true);
      cacheService.remove('settings:data');
      cacheService.remove('settings:user');
      setTimeout(() => setSavedSuccess(false), 3000);
      fetchData(true);
    } catch (error) {
      console.error('Failed to update settings:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleDisconnectGmail = async () => {
    if (window.confirm('Are you sure you want to disconnect Gmail? You will need to reconnect to continue automatic sync.')) {
      try {
        await authApi.disconnectGmail();
        cacheService.clearAll();
        fetchData();
      } catch (error) {
        console.error('Failed to disconnect Gmail:', error);
      }
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 sm:space-y-6 pb-12 w-full max-w-4xl">
        <div>
          <h1 className="text-page-title text-slate-900 dark:text-slate-100">Settings</h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">Manage preferences and integrations</p>
        </div>
        <div className="space-y-4 max-w-4xl">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6 pb-12 w-full max-w-4xl min-w-0">
      <div>
        <h1 className="text-page-title text-slate-900 dark:text-slate-100">
          Settings
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-0.5 max-w-2xl font-normal leading-relaxed">
          Manage your account preferences, Gmail OAuth integration, and automated alert thresholds.
        </p>
      </div>

      {savedSuccess && (
        <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-800 dark:text-emerald-300 text-xs font-bold flex items-center gap-2.5 backdrop-blur-md animate-fade-in">
          <CheckCircle2 size={16} className="text-emerald-500 shrink-0" />
          <span>Preferences saved successfully.</span>
        </div>
      )}

      {/* Account Profile Card */}
      <div className="glass-card p-4 sm:p-6 rounded-2xl sm:rounded-3xl space-y-4">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-black text-lg shadow-md shadow-indigo-500/25 shrink-0">
            {user?.email?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="min-w-0">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 tracking-tight truncate">
              {user?.email?.split('@')[0] || 'User Profile'}
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 font-medium truncate">{user?.email}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3 border-t border-slate-100 dark:border-white/[0.06]">
          <div>
            <label className="label">Account Email</label>
            <input type="text" value={user?.email || ''} disabled className="input bg-white/40 dark:bg-white/[0.03] opacity-80" />
          </div>
          <div>
            <label className="label">Account Type</label>
            <input type="text" value="Google OAuth2 Authenticated" disabled className="input bg-white/40 dark:bg-white/[0.03] opacity-80" />
          </div>
        </div>
      </div>

      {/* Gmail Integration Card */}
      <div className="glass-card p-4 sm:p-6 rounded-2xl sm:rounded-3xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div>
            <h2 className="text-card-title flex items-center gap-2">
              <Mail size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
              Gmail Integration
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Automated mailbox scanning for job applications, recruiter replies, and status changes.
            </p>
          </div>
          {user?.gmail_connected ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 shrink-0 self-start sm:self-auto">
              <CheckCircle2 size={12} className="text-emerald-500" /> Connected
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-700 dark:text-rose-300 border border-rose-500/20 shrink-0 self-start sm:self-auto">
              <XCircle size={12} className="text-rose-500" /> Disconnected
            </span>
          )}
        </div>

        <div className="p-3.5 rounded-xl bg-white/40 dark:bg-white/[0.02] border border-slate-200/80 dark:border-white/[0.06] backdrop-blur-md space-y-2 text-xs">
          <div className="flex flex-col sm:flex-row sm:justify-between gap-0.5">
            <span className="text-slate-500 dark:text-slate-400 font-medium">Last Successful Sync</span>
            <span className="font-bold text-slate-900 dark:text-slate-100">
              {lastSync || user?.gmail_last_sync ? new Date(lastSync || user?.gmail_last_sync!).toLocaleString() : 'Never synced'}
            </span>
          </div>
          <div className="flex flex-col sm:flex-row sm:justify-between gap-0.5">
            <span className="text-slate-500 dark:text-slate-400 font-medium">Scope Permission</span>
            <span className="font-semibold text-emerald-600 dark:text-emerald-400 break-all">gmail.readonly</span>
          </div>
        </div>

        <div>
          <button onClick={() => triggerSync(true)} className="btn btn-secondary text-xs w-full sm:w-auto justify-center">
            <RefreshCw size={14} />
            <span>Sync Mailbox Now</span>
          </button>
        </div>
      </div>

      {/* Application Preferences Card */}
      <div className="glass-card p-4 sm:p-6 rounded-2xl sm:rounded-3xl space-y-4">
        <div>
          <h2 className="text-card-title flex items-center gap-2">
            <Sliders size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
            Inactivity Alert Threshold
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Configure when an application with no recruiter activity is flagged as stale.
          </p>
        </div>

        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <label className="label mb-0">Inactivity Threshold</label>
            <span className="text-xs sm:text-sm font-black text-indigo-600 dark:text-indigo-400">{staleThreshold} days</span>
          </div>
          <input
            type="range"
            min="7"
            max="60"
            step="1"
            value={staleThreshold}
            onChange={(e) => setStaleThreshold(Number(e.target.value))}
            className="w-full accent-indigo-600 cursor-pointer"
          />
          <div className="flex justify-between text-[10px] sm:text-[11px] text-slate-400 font-medium">
            <span>7 days (Frequent)</span>
            <span>14 days (Recommended)</span>
            <span>60 days (Lenient)</span>
          </div>
        </div>

        <div className="pt-1">
          <button
            onClick={handleUpdateSettings}
            disabled={saving}
            className="btn btn-primary text-xs shadow-sm w-full sm:w-auto justify-center"
          >
            {saving ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>
      </div>

      {/* Security & Danger Zone */}
      <div className="glass-card p-4 sm:p-6 rounded-2xl sm:rounded-3xl border-rose-500/25 bg-rose-500/[0.03] space-y-3">
        <div>
          <h2 className="text-card-title text-rose-700 dark:text-rose-400 flex items-center gap-2">
            <AlertTriangle size={16} shrink-0 />
            Danger Zone
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Disconnect your Gmail integration or revoke OAuth permissions.
          </p>
        </div>

        <div className="pt-1">
          <button
            onClick={handleDisconnectGmail}
            className="btn btn-danger text-xs w-full sm:w-auto justify-center"
          >
            <XCircle size={14} />
            <span>Disconnect Gmail Integration</span>
          </button>
        </div>
      </div>
    </div>
  );
}
