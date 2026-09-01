import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { 
  ShieldCheck, ArrowLeft, Lock, Mail, CheckCircle2, 
  Sparkles, Layers, ArrowRight, ShieldAlert, Cpu
} from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';

export default function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const authStatus = searchParams.get('auth');
    const authError = searchParams.get('error');

    if (authStatus === 'success') {
      navigate('/dashboard');
    } else if (authStatus === 'failed') {
      setErrorMessage(authError ? decodeURIComponent(authError) : 'Authentication failed. Please try again.');
    }
  }, [searchParams, navigate]);

  const handleGoogleLogin = () => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
    window.location.href = `${baseUrl}/auth/google/`;
  };

  return (
    <div className="min-h-screen w-full flex flex-col bg-slate-50 dark:bg-[#0b0f19] text-slate-900 dark:text-slate-100 transition-colors duration-200 selection:bg-indigo-500/20">
      
      {/* Global Top Navbar: Back button on the far left, Theme toggle on the far right */}
      <header className="w-full px-6 sm:px-10 py-4 flex items-center justify-between border-b border-slate-200/80 dark:border-white/[0.07] bg-white/70 dark:bg-[#080c14]/70 backdrop-blur-xl sticky top-0 z-30">
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl border border-slate-200/80 dark:border-white/[0.08] bg-white/80 dark:bg-white/[0.05] text-xs font-semibold text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/[0.09] shadow-sm backdrop-blur-md transition-all active:scale-98"
        >
          <ArrowLeft size={14} />
          <span>Back to Home</span>
        </Link>

        <div className="flex items-center gap-2">
          <ThemeToggle />
        </div>
      </header>

      {/* Main Split-Screen Container */}
      <div className="flex-1 flex flex-col lg:flex-row w-full">
        
        {/* Left Column: Product Showcase & Simulation */}
        <div className="hidden lg:flex lg:w-1/2 relative bg-slate-100/50 dark:bg-[#090e1c]/60 border-r border-slate-200/80 dark:border-white/[0.07] flex-col justify-between p-12 xl:p-16 overflow-hidden transition-colors duration-200 backdrop-blur-sm">
          {/* Subtle ambient lighting */}
          <div className="absolute top-1/4 -left-20 w-80 h-80 bg-indigo-500/10 dark:bg-indigo-600/[0.08] rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 right-0 w-96 h-96 bg-blue-500/10 dark:bg-blue-600/[0.06] rounded-full blur-3xl pointer-events-none" />

          {/* Brand header */}
          <div className="relative z-10">
            <Link to="/" className="inline-flex items-center gap-3 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-black text-sm shadow-md shadow-indigo-500/25 group-hover:scale-105 transition-transform">
                A
              </div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg tracking-tight text-slate-900 dark:text-white">
                  ApplyTrack <span className="text-indigo-600 dark:text-indigo-400">AI</span>
                </span>
                <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-500/20 rounded-full">
                  OS
                </span>
              </div>
            </Link>
          </div>

          {/* Middle Showcase Widget: Themed Live Pipeline Card */}
          <div className="relative z-10 max-w-md my-auto space-y-6">
            <div className="space-y-3">
              <h1 className="text-3xl xl:text-4xl font-black text-slate-900 dark:text-white tracking-tight leading-tight text-balance">
                Never update a job search spreadsheet again.
              </h1>
              <p className="text-sm text-slate-600 dark:text-slate-400 font-normal leading-relaxed">
                ApplyTrack scans incoming recruiter updates, classifies hiring stages, and updates your pipeline autonomously.
              </p>
            </div>

            {/* Simulated Live Inbox Widget */}
            <div className="glass-card p-5 space-y-3.5">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-white/[0.06] text-xs">
                <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300 font-semibold">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span>Live Inbox Intelligence</span>
                </div>
                <span className="text-[11px] text-slate-400 dark:text-slate-500 font-medium">Auto-synchronized</span>
              </div>

              {/* Email update items */}
              <div className="space-y-2.5">
                <div className="p-3 rounded-xl bg-white/50 dark:bg-white/[0.03] border border-slate-200/70 dark:border-white/[0.06] flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-xs shrink-0">
                      S
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate">Stripe &bull; Technical Interview</p>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">Round 2 scheduled with Hiring Team</p>
                    </div>
                  </div>
                  <span className="badge badge-interview text-[10px]">
                    Interview
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-white/50 dark:bg-white/[0.03] border border-slate-200/70 dark:border-white/[0.06] flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold text-xs shrink-0">
                      G
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate">Google &bull; Application Confirmation</p>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">Software Engineer (L4) application received</p>
                    </div>
                  </div>
                  <span className="badge badge-applied text-[10px]">
                    Applied
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Left Footer Info */}
          <div className="relative z-10 pt-6 border-t border-slate-200/80 dark:border-white/[0.06] flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Enterprise OAuth 2.0 Security</span>
            <span>Zero Email Modification</span>
          </div>
        </div>

        {/* Right Column: Authentication Panel */}
        <div className="flex-1 flex flex-col justify-between p-6 sm:p-12 lg:p-16 bg-white dark:bg-[#080c14] transition-colors duration-200">
          
          {/* Auth Core Container */}
          <div className="w-full max-w-md mx-auto my-auto py-8 space-y-7">
            {/* Header */}
            <div className="space-y-2 text-left">
              <div className="lg:hidden flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-black text-xs shadow-sm">
                  A
                </div>
                <span className="font-extrabold text-base tracking-tight text-slate-900 dark:text-slate-100">
                  ApplyTrack <span className="text-indigo-600 dark:text-indigo-400">AI</span>
                </span>
              </div>

              <h2 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-slate-100 tracking-tight">
                Sign in to your account
              </h2>
              <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 font-normal">
                Connect your Google account to access your automated application tracker.
              </p>
            </div>

            {/* Error Message */}
            {errorMessage && (
              <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-900 dark:text-rose-200 text-xs flex items-start gap-3 animate-in fade-in">
                <ShieldAlert size={16} className="text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <p className="font-bold">Authentication failed</p>
                  <p className="opacity-90 mt-0.5">{errorMessage}</p>
                </div>
              </div>
            )}

            {/* Google SSO Button */}
            <div className="space-y-4">
              <button
                id="google-login-btn"
                onClick={handleGoogleLogin}
                className="w-full flex items-center justify-center gap-3 py-3.5 px-5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/90 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 font-bold text-sm shadow-sm hover:shadow-md transition-all active:scale-[0.99] cursor-pointer"
              >
                {/* Authentic Google Multi-Color SVG Logo */}
                <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>Continue with Google</span>
              </button>
            </div>

            {/* Privacy & Security Guarantees */}
            <div className="pt-4 border-t border-slate-100 dark:border-slate-800/80 space-y-3">
              <div className="flex items-start gap-3">
                <ShieldCheck size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-bold text-slate-800 dark:text-slate-200">Read-Only Permission</p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                    ApplyTrack only reads job application and recruiter emails. It will never send, edit, or delete messages.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Lock size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-bold text-slate-800 dark:text-slate-200">Zero In-Database Email Storage</p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                    Only metadata and application statuses are stored. Full email bodies are parsed in-memory and discarded.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Minimal Footer */}
          <div className="w-full max-w-md mx-auto pt-6 border-t border-slate-100 dark:border-slate-800/80 text-center space-y-2">
            <div className="flex items-center justify-center gap-3 text-[11px] text-slate-500 dark:text-slate-400">
              <Link to="/privacy" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                Privacy Policy
              </Link>
              <span>&bull;</span>
              <Link to="/terms" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                Terms of Service
              </Link>
            </div>
            <p className="text-[11px] text-slate-400 dark:text-slate-500 font-medium">
              Protected by Google OAuth 2.0 PKCE. Read-only Gmail Scope.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
