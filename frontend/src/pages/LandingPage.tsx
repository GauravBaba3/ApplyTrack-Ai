import React from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowRight, CheckCircle2, Mail, Zap, Shield, Sparkles, Activity, 
  TrendingUp, Clock, Bot, Inbox, Check, X, ChevronRight, Lock, Eye
} from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="py-10 sm:py-20 space-y-28 max-w-6xl mx-auto px-4 sm:px-6">
      {/* Hero Section */}
      <div className="text-center space-y-7 max-w-4xl mx-auto">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200/80 dark:border-indigo-800/80 text-indigo-700 dark:text-indigo-300 text-xs font-bold tracking-wide uppercase shadow-sm">
          <Sparkles size={14} className="text-indigo-600 dark:text-indigo-400 animate-pulse" />
          <span>AI-Powered Application Intelligence</span>
        </div>

        <h1 className="text-4xl sm:text-6xl md:text-7xl font-black text-slate-900 dark:text-slate-100 tracking-tight leading-[1.08] text-balance">
          Your inbox knows <span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent">where you stand.</span>
        </h1>

        <p className="text-lg sm:text-xl text-slate-600 dark:text-slate-300 max-w-2xl mx-auto leading-relaxed font-normal">
          ApplyTrack AI connects securely to Gmail, detects recruiter updates in real-time, automatically classifies status changes, and turns scattered email threads into a clear application pipeline.
        </p>

        <div className="flex items-center justify-center pt-3">
          <Link to="/login" className="btn btn-primary text-base px-8 py-3.5 shadow-lg shadow-indigo-500/20 w-full sm:w-auto">
            <span>Connect Gmail & Get Started</span>
            <ArrowRight size={18} />
          </Link>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-6 sm:gap-8 pt-4 text-xs font-semibold text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1.5">
            <CheckCircle2 size={15} className="text-emerald-600 dark:text-emerald-400" /> Read-only Gmail Scope
          </span>
          <span className="flex items-center gap-1.5">
            <CheckCircle2 size={15} className="text-emerald-600 dark:text-emerald-400" /> 100% Private & Encrypted
          </span>
          <span className="flex items-center gap-1.5">
            <CheckCircle2 size={15} className="text-emerald-600 dark:text-emerald-400" /> Zero Manual Entry
          </span>
        </div>
      </div>

      {/* Hero Interactive Product Preview Mockup */}
      <div className="relative rounded-3xl p-2 sm:p-4 bg-gradient-to-b from-slate-200/60 to-slate-100/30 dark:from-slate-800/60 dark:to-slate-900/30 border border-slate-200/80 dark:border-slate-800 shadow-2xl">
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 overflow-hidden shadow-inner">
          {/* Mockup Header */}
          <div className="px-5 py-3.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/50">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-rose-400/80" />
              <div className="w-3 h-3 rounded-full bg-amber-400/80" />
              <div className="w-3 h-3 rounded-full bg-emerald-400/80" />
            </div>
            <div className="text-xs font-semibold text-slate-400 dark:text-slate-500 flex items-center gap-1.5 bg-white dark:bg-slate-800 px-3 py-1 rounded-lg border border-slate-200/60 dark:border-slate-700/60">
              <Lock size={12} /> applytrack.ai/dashboard
            </div>
            <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" /> Live Sync
            </div>
          </div>

          {/* Mockup Dashboard Content */}
          <div className="p-6 sm:p-8 space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60">
                <p className="text-xs font-semibold text-slate-400 uppercase">Total Tracked</p>
                <p className="text-2xl font-black text-slate-900 dark:text-slate-100 mt-1">28</p>
              </div>
              <div className="p-4 rounded-xl bg-blue-50/50 dark:bg-blue-950/30 border border-blue-200/60 dark:border-blue-800/40">
                <p className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase">In Review</p>
                <p className="text-2xl font-black text-blue-700 dark:text-blue-300 mt-1">12</p>
              </div>
              <div className="p-4 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/30 border border-emerald-200/60 dark:border-emerald-800/40">
                <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase">Interviews</p>
                <p className="text-2xl font-black text-emerald-700 dark:text-emerald-300 mt-1">5</p>
              </div>
              <div className="p-4 rounded-xl bg-cyan-50/50 dark:bg-cyan-950/30 border border-cyan-200/60 dark:border-cyan-800/40">
                <p className="text-xs font-semibold text-cyan-600 dark:text-cyan-400 uppercase">Offers</p>
                <p className="text-2xl font-black text-cyan-700 dark:text-cyan-300 mt-1">2</p>
              </div>
            </div>

            {/* Email Auto-Parser preview item */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-indigo-50/80 to-purple-50/80 dark:from-indigo-950/40 dark:to-purple-950/40 border border-indigo-200/80 dark:border-indigo-800/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-sm shadow-md shrink-0">
                  <Bot size={20} />
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-bold text-indigo-700 dark:text-indigo-300">Stripe Recruiter Update</span>
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300">
                      Interview Invitation Detected
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-300 mt-0.5">
                    "Invitation to Technical Round 2 with Engineering Team" &bull; Automatically updated status to <span className="font-semibold text-emerald-600 dark:text-emerald-400">Interview</span>
                  </p>
                </div>
              </div>
              <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 shrink-0">Just now</span>
            </div>
          </div>
        </div>
      </div>

      {/* Section 2: How It Works */}
      <div className="space-y-12 text-center">
        <div className="space-y-3">
          <h2 className="text-xs font-extrabold uppercase tracking-widest text-indigo-600 dark:text-indigo-400">Workflow</h2>
          <p className="text-3xl sm:text-4xl font-black text-slate-900 dark:text-slate-100 tracking-tight">
            From inbox chaos to a clear job search.
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-xl mx-auto">
            Zero spreadsheets. Zero manual copy-pasting. ApplyTrack AI handles the bookkeeping in the background.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 text-left">
          {[
            {
              step: '01',
              title: 'Connect Gmail',
              desc: 'Link your Gmail with one click using secure Google OAuth PKCE authorization.',
              icon: Mail,
              color: 'text-blue-600 bg-blue-50 dark:bg-blue-950/50 dark:text-blue-400 border-blue-200 dark:border-blue-800/60'
            },
            {
              step: '02',
              title: 'AI Reads Signals',
              desc: 'Our extraction engine filters job confirmation, assessments, and interview invitations.',
              icon: Zap,
              color: 'text-purple-600 bg-purple-50 dark:bg-purple-950/50 dark:text-purple-400 border-purple-200 dark:border-purple-800/60'
            },
            {
              step: '03',
              title: 'Auto-Update Pipeline',
              desc: 'Applications and statuses are created, matched, and updated automatically in real-time.',
              icon: Activity,
              color: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/50 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800/60'
            },
            {
              step: '04',
              title: 'Insights & Follow-ups',
              desc: 'Track conversion ratios, response latency, and pre-draft polite recruiter follow-up emails.',
              icon: TrendingUp,
              color: 'text-cyan-600 bg-cyan-50 dark:bg-cyan-950/50 dark:text-cyan-400 border-cyan-200 dark:border-cyan-800/60'
            }
          ].map((item, idx) => (
            <div key={idx} className="card card-body p-6 relative group hover:border-slate-300 dark:hover:border-slate-700 transition-all">
              <div className={`w-11 h-11 rounded-2xl flex items-center justify-center font-bold text-sm mb-5 border shadow-sm ${item.color}`}>
                <item.icon size={20} />
              </div>
              <span className="text-xs font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Step {item.step}</span>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 mt-1 mb-2">{item.title}</h3>
              <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 leading-relaxed font-normal">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Section 3: Before vs After */}
      <div className="card card-body p-8 sm:p-12 border-slate-200/80 dark:border-slate-800">
        <div className="text-center max-w-2xl mx-auto mb-10 space-y-2">
          <h2 className="text-xs font-extrabold uppercase tracking-widest text-indigo-600 dark:text-indigo-400">Why ApplyTrack AI</h2>
          <p className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-slate-100 tracking-tight">
            The old way vs. The ApplyTrack AI way
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Old Way */}
          <div className="p-6 rounded-2xl bg-rose-50/50 dark:bg-rose-950/20 border border-rose-200/60 dark:border-rose-900/40 space-y-4">
            <div className="flex items-center gap-2 text-rose-700 dark:text-rose-400 font-bold text-sm">
              <X size={18} /> The Manual Struggle
            </div>
            <ul className="space-y-3 text-xs sm:text-sm text-slate-600 dark:text-slate-400">
              <li className="flex items-start gap-2">
                <span className="text-rose-500 font-bold">&bull;</span> Manually entering 50+ company names and dates in Excel or Notion.
              </li>
              <li className="flex items-start gap-2">
                <span className="text-rose-500 font-bold">&bull;</span> Losing track of recruiter emails buried in spam or promotions folders.
              </li>
              <li className="flex items-start gap-2">
                <span className="text-rose-500 font-bold">&bull;</span> Forgetting which stage an application is in when an interviewer calls.
              </li>
              <li className="flex items-start gap-2">
                <span className="text-rose-500 font-bold">&bull;</span> Missing optimal follow-up windows and letting opportunities go cold.
              </li>
            </ul>
          </div>

          {/* ApplyTrack AI Way */}
          <div className="p-6 rounded-2xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200/60 dark:border-emerald-900/40 space-y-4">
            <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-bold text-sm">
              <Check size={18} /> The Intelligent Automation
            </div>
            <ul className="space-y-3 text-xs sm:text-sm text-slate-700 dark:text-slate-300">
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" /> 
                Instant Gmail sync detects applications across LinkedIn, Indeed, Greenhouse, Lever.
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" /> 
                Groq AI classifies emails with zero hallucination and high precision.
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" /> 
                Automatic status progression: Applied &rarr; Assessment &rarr; Interview &rarr; Offer.
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" /> 
                One-click AI Follow-up drafts and inactivity alerts keep you in control.
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Final High-Converting CTA */}
      <div className="rounded-3xl p-8 sm:p-14 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white text-center space-y-6 shadow-2xl relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-white/20 via-transparent to-transparent pointer-events-none" />
        <h2 className="text-3xl sm:text-5xl font-black tracking-tight max-w-2xl mx-auto leading-tight">
          Stop managing your job search from your inbox.
        </h2>
        <p className="text-white/90 text-sm sm:text-base max-w-xl mx-auto font-normal">
          Connect your Gmail and let ApplyTrack AI keep your job pipeline clean, organized, and ahead of deadlines.
        </p>
        <div className="pt-2">
          <Link to="/login" className="btn bg-white text-indigo-700 hover:bg-slate-100 text-base font-bold px-8 py-3.5 shadow-lg shadow-black/10">
            <span>Connect Gmail & Get Started</span>
            <ArrowRight size={18} />
          </Link>
        </div>
      </div>

      {/* Footer */}
      <footer className="pt-8 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 dark:text-slate-400">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-md bg-indigo-600 text-white flex items-center justify-center font-bold text-[10px]">
            A
          </div>
          <span className="font-semibold text-slate-700 dark:text-slate-300">ApplyTrack AI &bull; Intelligent Job Search</span>
        </div>
        <div className="flex items-center gap-5 font-medium">
          <Link to="/privacy" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
            Privacy Policy
          </Link>
          <span>&bull;</span>
          <Link to="/terms" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
            Terms of Service
          </Link>
          <span>&bull;</span>
          <Link to="/login" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
            Sign In
          </Link>
        </div>
        <p className="text-slate-400 dark:text-slate-500">© {new Date().getFullYear()} ApplyTrack AI. All rights reserved.</p>
      </footer>
    </div>
  );
}
