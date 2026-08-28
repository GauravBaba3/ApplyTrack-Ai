import React, { useState, useEffect, useCallback } from 'react';
import { 
  Settings, Mail, Shield, Bell, Calendar, LogOut, CheckCircle2, 
  XCircle, User as UserIcon, Clock, Lock, RefreshCw, KeyRound, 
  AlertTriangle, Check, Sliders 
} from 'lucide-react';
import { authApi } from '../services/api';
import { User, UserSettings } from '../types';
import { useSync } from '../context/SyncContext';
import PageHeader from '../components/PageHeader';
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
      <div className="space-y-6 pb-12">
        <PageHeader title="Settings" description="Manage your preferences and integrations" />
        <div className="space-y-6 max-w-4xl">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-12 max-w-4xl">
      <PageHeader
        title="Settings"
        description="Manage your account preferences, Gmail OAuth integration, and automated alert thresholds."
      />

      {savedSuccess && (
        <div className="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 text-xs font-semibold flex items-center gap-2.5 animate-in fade-in">
          <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400" />
          <span>Settings saved successfully.</span>
        </div>
      )}

      {/* Account Profile Card */}
      <div className="card p-6 sm:p-7 space-y-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-black text-xl shadow-md shrink-0">
            {user?.email?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
              {user?.email?.split('@')[0] || 'User Profile'}
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{user?.email}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-slate-100 dark:border-slate-800">
          <div>
            <label className="label">Account Email</label>
            <input type="text" value={user?.email || ''} disabled className="input bg-slate-50 dark:bg-slate-800/50" />
          </div>
          <div>
            <label className="label">Account Type</label>
            <input type="text" value="Google Authenticated" disabled className="input bg-slate-50 dark:bg-slate-800/50" />
          </div>
        </div>
      </div>

      {/* Gmail Integration Card */}
      <div className="card p-6 sm:p-7 space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Mail size={18} className="text-indigo-600 dark:text-indigo-400" />
              Gmail Integration
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Automated mailbox scanning for job applications and recruiter status shifts.
            </p>
          </div>
          {user?.gmail_connected ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 shrink-0">
              <CheckCircle2 size={13} className="text-emerald-500" /> Connected
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60 shrink-0">
              <XCircle size={13} className="text-rose-500" /> Disconnected
            </span>
          )}
        </div>

        <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/70 dark:border-slate-800 space-y-3">
          <div className="flex justify-between text-xs">
            <span className="text-slate-500 dark:text-slate-400">Last Successful Sync</span>
            <span className="font-bold text-slate-900 dark:text-slate-100">
              {lastSync || user?.gmail_last_sync ? new Date(lastSync || user?.gmail_last_sync!).toLocaleString() : 'Never synced'}
            </span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-500 dark:text-slate-400">OAuth Scope Permission</span>
            <span className="font-semibold text-emerald-600 dark:text-emerald-400">https://www.googleapis.com/auth/gmail.readonly</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={() => triggerSync(true)} className="btn btn-secondary text-xs">
            <RefreshCw size={14} />
            <span>Sync Mailbox Now</span>
          </button>
        </div>
      </div>

      {/* Application Preferences Card */}
      <div className="card p-6 sm:p-7 space-y-6">
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Sliders size={18} className="text-indigo-600 dark:text-indigo-400" />
            Application Inactivity Alerts
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Configure when an application with no recruiter replies is flagged as stalled or ghosted.
          </p>
        </div>

        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <label className="label mb-0">Inactivity Threshold</label>
            <span className="text-sm font-black text-indigo-600 dark:text-indigo-400">{staleThreshold} days</span>
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
          <div className="flex justify-between text-[11px] text-slate-400">
            <span>7 days (Frequent)</span>
            <span>14 days (Recommended)</span>
            <span>60 days (Lenient)</span>
          </div>
        </div>

        <div className="pt-2">
          <button
            onClick={handleUpdateSettings}
            disabled={saving}
            className="btn btn-primary text-xs shadow-sm"
          >
            {saving ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>
      </div>

      {/* Security & Danger Zone */}
      <div className="card p-6 sm:p-7 border-rose-200/80 dark:border-rose-950/60 space-y-4">
        <div>
          <h2 className="text-base font-bold text-rose-700 dark:text-rose-400 flex items-center gap-2">
            <AlertTriangle size={18} />
            Danger Zone
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Disconnect your Gmail integration or revoke OAuth permissions.
          </p>
        </div>

        <div className="pt-2 flex flex-wrap items-center gap-3">
          <button
            onClick={handleDisconnectGmail}
            className="btn btn-danger text-xs"
          >
            <XCircle size={15} />
            <span>Disconnect Gmail Integration</span>
          </button>
        </div>
      </div>
    </div>
  );
}
