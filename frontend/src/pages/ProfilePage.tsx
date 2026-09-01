import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  User as UserIcon, Mail, ShieldCheck, CheckCircle2, XCircle, 
  RefreshCw, LogOut, Lock, Calendar, ExternalLink, Sparkles 
} from 'lucide-react';
import { authApi } from '../services/api';
import { User } from '../types';
import { useSync } from '../context/SyncContext';
import { useToast } from '../context/ToastContext';
import { SkeletonCard } from '../components/LoadingSkeleton';
import { cacheService, CACHE_TTL } from '../services/cacheService';

export default function ProfilePage() {
  const navigate = useNavigate();
  const { info } = useToast();
  const [user, setUser] = useState<User | null>(() => 
    cacheService.get<User>('settings:user', CACHE_TTL.SETTINGS)
  );
  const [loading, setLoading] = useState(!user);
  const { dataVersion, lastSync, triggerSync, isSyncing } = useSync();

  const fetchUserData = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const response = await authApi.getMe();
      if (response.data) {
        setUser(response.data);
        cacheService.set('settings:user', response.data);
      }
    } catch (error) {
      console.error('Failed to fetch user profile:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUserData(Boolean(user));
  }, [fetchUserData, dataVersion]);

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Proceed with local logout regardless of network error
    } finally {
      cacheService.clearAll();
      window.location.href = '/login';
    }
  };

  const handleSync = async () => {
    await triggerSync(true);
    info('Gmail Sync Initiated', 'Scanning your mailbox for latest recruiter communications.');
  };

  if (loading) {
    return (
      <div className="space-y-4 sm:space-y-6 pb-12 w-full max-w-4xl">
        <div>
          <h1 className="text-page-title text-slate-900 dark:text-slate-100">User Profile</h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">Your account identity and integration status</p>
        </div>
        <div className="space-y-4">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  const username = user?.email?.split('@')[0] || 'User';
  const initial = user?.email?.charAt(0).toUpperCase() || 'U';

  return (
    <div className="space-y-4 sm:space-y-6 pb-12 w-full max-w-4xl min-w-0 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
        <div>
          <h1 className="text-page-title text-slate-900 dark:text-slate-100">
            Profile & Account
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-0.5 max-w-2xl font-normal leading-relaxed">
            View your verified Google identity, mailbox connection state, and active security scopes.
          </p>
        </div>
        <button
          onClick={handleLogout}
          className="btn btn-secondary text-xs shadow-sm hover:text-rose-600 dark:hover:text-rose-400 w-full sm:w-auto justify-center"
        >
          <LogOut size={14} />
          <span>Sign Out</span>
        </button>
      </div>

      {/* Main Identity Banner Card */}
      <div className="glass-2 p-4 sm:p-7 rounded-2xl sm:rounded-3xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-bl from-indigo-500/10 via-purple-500/5 to-transparent rounded-full blur-2xl pointer-events-none" />
        
        <div className="relative z-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 sm:gap-6">
          <div className="flex items-center gap-3.5 sm:gap-5 min-w-0">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center text-white font-black text-xl sm:text-2xl shadow-lg shadow-indigo-500/30 ring-4 ring-white/10 shrink-0">
              {initial}
            </div>
            <div className="space-y-0.5 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-lg sm:text-xl font-black text-slate-900 dark:text-slate-100 tracking-tight truncate">
                  {username}
                </h2>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] sm:text-xs font-semibold bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-500/20 backdrop-blur-md">
                  <Sparkles size={11} /> Pro
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 font-medium flex items-center gap-1.5 truncate">
                <Mail size={13} className="text-slate-400 shrink-0" />
                <span className="truncate">{user?.email}</span>
              </p>
            </div>
          </div>

          <div className="w-full sm:w-auto self-stretch sm:self-auto shrink-0">
            <button
              onClick={handleSync}
              disabled={isSyncing}
              className="btn btn-primary text-xs shadow-md shadow-indigo-500/20 w-full sm:w-auto justify-center"
            >
              <RefreshCw size={14} className={isSyncing ? 'animate-spin' : ''} />
              <span>{isSyncing ? 'Syncing...' : 'Sync Mailbox'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Grid: Connected Accounts & Security Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        {/* Connected Google Account */}
        <div className="glass-2 p-4 sm:p-6 rounded-2xl sm:rounded-3xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-white/[0.06]">
            <h3 className="text-card-title flex items-center gap-2">
              <ShieldCheck size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
              Connected Identity
            </h3>
            {user?.gmail_connected ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 shrink-0">
                <CheckCircle2 size={12} className="text-emerald-500" /> Active
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-700 dark:text-rose-300 border border-rose-500/20 shrink-0">
                <XCircle size={12} className="text-rose-500" /> Disconnected
              </span>
            )}
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="flex flex-col sm:flex-row sm:justify-between gap-0.5 py-0.5">
              <span className="text-slate-500 dark:text-slate-400">Auth Provider</span>
              <span className="font-bold text-slate-800 dark:text-slate-200">Google OAuth 2.0 PKCE</span>
            </div>
            <div className="flex flex-col sm:flex-row sm:justify-between gap-0.5 py-0.5">
              <span className="text-slate-500 dark:text-slate-400">Email</span>
              <span className="font-semibold text-slate-800 dark:text-slate-200 truncate">{user?.email}</span>
            </div>
            <div className="flex flex-col sm:flex-row sm:justify-between gap-0.5 py-0.5">
              <span className="text-slate-500 dark:text-slate-400">Last Sync</span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {lastSync || user?.gmail_last_sync ? new Date(lastSync || user?.gmail_last_sync!).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Never'}
              </span>
            </div>
          </div>
        </div>

        {/* Security & Access Scope */}
        <div className="glass-2 p-4 sm:p-6 rounded-2xl sm:rounded-3xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-white/[0.06]">
            <h3 className="text-card-title flex items-center gap-2">
              <Lock size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
              Security Scopes
            </h3>
            <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 shrink-0">
              Read-Only
            </span>
          </div>

          <div className="space-y-2.5 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            <div className="p-3 rounded-xl bg-white/40 dark:bg-white/[0.02] border border-slate-200/70 dark:border-white/[0.05] space-y-0.5">
              <p className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 text-xs">
                <CheckCircle2 size={12} className="text-emerald-500 shrink-0" /> Scope: gmail.readonly
              </p>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                ApplyTrack AI can only read incoming messages for application matching. It cannot compose or modify emails.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-white/40 dark:bg-white/[0.02] border border-slate-200/70 dark:border-white/[0.05] space-y-0.5">
              <p className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 text-xs">
                <CheckCircle2 size={12} className="text-emerald-500 shrink-0" /> In-Memory Pipeline Processing
              </p>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Email bodies are parsed securely in-memory. Only job metadata and interview events are stored.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
