import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowRight, CheckCircle2, Mail, Zap, Shield, Sparkles, Activity, 
  TrendingUp, Clock, Bot, Inbox, Check, X, ChevronRight, Lock, 
  ShieldCheck, Eye, Layers, Cpu, Compass, Sliders, ArrowUpRight,
  Database, UserCheck, RefreshCw, Star
} from 'lucide-react';

export default function LandingPage() {
  const workflowSteps = [
    {
      id: '01',
      title: 'Gmail Read-Only Sync',
      badge: 'Zero Email Modification',
      desc: 'Secure OAuth 2.0 PKCE connection reads recruiter emails without access to edit, compose, or delete messages.',
      icon: Mail,
      accent: 'from-blue-500 to-indigo-600',
    },
    {
      id: '02',
      title: 'AI Signal Parsing',
      badge: 'Rule Engine + LLM Cascade',
      desc: 'Dual-layer extraction identifies company name, job title, event type, and confidence score with zero hallucinations.',
      icon: Cpu,
      accent: 'from-indigo-500 to-purple-600',
    },
    {
      id: '03',
      title: 'Autonomous Pipeline Update',
      badge: 'Instant Sync',
      desc: 'Matched against your active opportunities. Status advances from "Applied" to "Interview" with complete audit history.',
      icon: Layers,
      accent: 'from-purple-500 to-cyan-600',
    },
    {
      id: '04',
      title: 'Follow-ups & Conversion Analytics',
      badge: 'Recruiter Assistant',
      desc: 'Track response latency, interview conversion rates, and generate tailored, polite follow-up drafts on demand.',
      icon: TrendingUp,
      accent: 'from-cyan-500 to-emerald-600',
    }
  ];

  return (
    <div className="space-y-16 sm:space-y-24 lg:space-y-32 py-6 sm:py-16 max-w-6xl mx-auto px-3.5 sm:px-6 animate-fade-in selection:bg-indigo-500/20 w-full max-w-full overflow-x-hidden">
      
      {/* =========================================================================
          HERO SECTION
          ========================================================================= */}
      <section className="text-center space-y-5 sm:space-y-8 max-w-4xl mx-auto relative pt-2 sm:pt-8">
        {/* Glow ambient background */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[38rem] h-[22rem] max-w-full bg-indigo-500/15 dark:bg-indigo-600/[0.12] rounded-full blur-3xl pointer-events-none -z-10" />

        {/* Top Badge */}
        <div className="inline-flex items-center gap-2 px-3 sm:px-4 py-1.5 rounded-full bg-indigo-500/10 dark:bg-indigo-500/15 border border-indigo-500/25 text-indigo-700 dark:text-indigo-300 text-[11px] sm:text-xs font-bold tracking-wide uppercase shadow-sm backdrop-blur-md">
          <Sparkles size={13} className="text-indigo-600 dark:text-indigo-400 animate-pulse shrink-0" />
          <span>AI-Powered Job Application Command Center</span>
        </div>

        {/* Hero Title */}
        <h1 className="text-hero text-slate-900 dark:text-slate-100 text-balance">
          Stop manually updating job search spreadsheets.{' '}
          <span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 dark:from-blue-400 dark:via-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
            Let AI track your pipeline.
          </span>
        </h1>

        {/* Hero Subtitle */}
        <p className="text-sm sm:text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto leading-relaxed font-normal">
          ApplyTrack AI connects safely to your Gmail, discovers application confirmations, recruiter replies, and interview invitations, and organizes your job hunt in real time.
        </p>

        {/* Primary CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-3 sm:gap-4 pt-2">
          <Link
            to="/login"
            className="btn btn-primary text-sm sm:text-base px-6 sm:px-8 py-3 sm:py-3.5 shadow-lg shadow-indigo-500/25 w-full sm:w-auto justify-center"
          >
            <span>Connect Gmail & Get Started</span>
            <ArrowRight size={17} />
          </Link>
          <a
            href="#how-it-works"
            className="btn btn-secondary text-xs sm:text-sm px-5 sm:px-6 py-3 sm:py-3.5 w-full sm:w-auto justify-center"
          >
            <span>Explore How It Works</span>
          </a>
        </div>

        {/* Trust Badges */}
        <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-8 pt-2 sm:pt-4 text-xs font-semibold text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1.5">
            <ShieldCheck size={15} className="text-emerald-500 shrink-0" /> Read-Only Gmail Scope
          </span>
          <span className="flex items-center gap-1.5">
            <CheckCircle2 size={15} className="text-emerald-500 shrink-0" /> In-Memory Parsing
          </span>
          <span className="flex items-center gap-1.5">
            <CheckCircle2 size={15} className="text-emerald-500 shrink-0" /> Human Review in the Loop
          </span>
        </div>
      </section>

      {/* =========================================================================
          HERO INTERACTIVE PIPELINE PREVIEW MOCKUP
          ========================================================================= */}
      <section className="relative glass-2 p-2.5 sm:p-5 rounded-2xl sm:rounded-3xl shadow-glass-3 w-full">
        <div className="glass-3 rounded-xl sm:rounded-2xl overflow-hidden border border-slate-200/80 dark:border-white/[0.08]">
          {/* Mockup Top Window Bar */}
          <div className="px-3.5 sm:px-5 py-2.5 sm:py-3.5 border-b border-slate-100 dark:border-white/[0.06] flex items-center justify-between bg-slate-50/50 dark:bg-white/[0.02]">
            <div className="flex items-center gap-1.5 sm:gap-2">
              <div className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full bg-rose-400/80" />
              <div className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full bg-amber-400/80" />
              <div className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full bg-emerald-400/80" />
            </div>
            <div className="text-[10px] sm:text-xs font-semibold text-slate-400 dark:text-slate-500 flex items-center gap-1.5 bg-white/80 dark:bg-[#070c18] px-2.5 sm:px-3.5 py-1 rounded-xl border border-slate-200/60 dark:border-white/[0.06] truncate max-w-[180px] sm:max-w-none">
              <Lock size={11} className="text-emerald-500 shrink-0" /> app.applytrack.ai/dashboard
            </div>
            <div className="text-[10px] sm:text-xs font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5 shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Live Ingestion
            </div>
          </div>

          {/* Mockup Dashboard Content */}
          <div className="p-4 sm:p-8 space-y-4 sm:space-y-6">
            {/* Metric KPI Row */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-4">
              <div className="p-3 sm:p-4 rounded-xl sm:rounded-2xl bg-white/60 dark:bg-white/[0.03] border border-slate-200/70 dark:border-white/[0.06]">
                <span className="text-[10px] sm:text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Total Tracked</span>
                <p className="text-xl sm:text-3xl font-black text-slate-900 dark:text-slate-100 mt-0.5 sm:mt-1">42</p>
                <span className="text-[10px] sm:text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold">+6 this week</span>
              </div>
              <div className="p-3 sm:p-4 rounded-xl sm:rounded-2xl bg-blue-500/10 border border-blue-500/20">
                <span className="text-[10px] sm:text-[11px] font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider block">Under Review</span>
                <p className="text-xl sm:text-3xl font-black text-blue-700 dark:text-blue-300 mt-0.5 sm:mt-1">18</p>
                <span className="text-[10px] sm:text-[11px] text-blue-600 dark:text-blue-400 font-semibold">Active recruiter reviews</span>
              </div>
              <div className="p-3 sm:p-4 rounded-xl sm:rounded-2xl bg-emerald-500/10 border border-emerald-500/20">
                <span className="text-[10px] sm:text-[11px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider block">Interviews</span>
                <p className="text-xl sm:text-3xl font-black text-emerald-700 dark:text-emerald-300 mt-0.5 sm:mt-1">7</p>
                <span className="text-[10px] sm:text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold">4 rounds this week</span>
              </div>
              <div className="p-3 sm:p-4 rounded-xl sm:rounded-2xl bg-cyan-500/10 border border-cyan-500/20">
                <span className="text-[10px] sm:text-[11px] font-bold text-cyan-600 dark:text-cyan-400 uppercase tracking-wider block">Offers</span>
                <p className="text-xl sm:text-3xl font-black text-cyan-700 dark:text-cyan-300 mt-0.5 sm:mt-1">2</p>
                <span className="text-[10px] sm:text-[11px] text-cyan-600 dark:text-cyan-400 font-semibold">Pending decision</span>
              </div>
            </div>

            {/* Email Auto-Parser Simulation Strip */}
            <div className="p-3.5 sm:p-4 rounded-xl sm:rounded-2xl bg-indigo-500/10 dark:bg-indigo-500/15 border border-indigo-500/25 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 sm:gap-4">
              <div className="flex items-start sm:items-center gap-3 min-w-0">
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl sm:rounded-2xl bg-indigo-600 text-white flex items-center justify-center font-bold text-xs sm:text-sm shadow-md shadow-indigo-500/30 shrink-0 mt-0.5 sm:mt-0">
                  <Bot size={18} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
                    <span className="text-xs font-black text-indigo-700 dark:text-indigo-300">Stripe Recruiter Communication</span>
                    <span className="px-2 py-0.5 text-[9px] sm:text-[10px] font-black rounded-full bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/25">
                      Interview Invitation Detected
                    </span>
                  </div>
                  <p className="text-[11px] sm:text-xs text-slate-600 dark:text-slate-300 mt-0.5 leading-relaxed">
                    "Invitation to Technical Round 2" &bull; Automatically updated status to <span className="font-bold text-emerald-600 dark:text-emerald-400">Interview</span>
                  </p>
                </div>
              </div>
              <span className="text-[10px] sm:text-xs font-semibold text-slate-400 dark:text-slate-500 shrink-0">Just now</span>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION: HOW IT WORKS (4 STEPS)
          ========================================================================= */}
      <section id="how-it-works" className="space-y-8 sm:space-y-12 text-center w-full">
        <div className="space-y-2 sm:space-y-3">
          <h2 className="text-xs font-black uppercase tracking-widest text-indigo-600 dark:text-indigo-400">
            Intelligent Automation Workflow
          </h2>
          <p className="text-2xl sm:text-4xl font-black text-slate-900 dark:text-slate-100 tracking-tight text-balance">
            From inbox clutter to an actionable command center.
          </p>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-xl mx-auto font-normal leading-relaxed">
            No browser extensions. No manual spreadsheets. ApplyTrack AI handles data extraction in the background.
          </p>
        </div>

        {/* 4 Steps Interactive Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-5 text-left">
          {workflowSteps.map((step) => {
            const Icon = step.icon;
            return (
              <div
                key={step.id}
                className="glass-2 p-4 sm:p-6 rounded-2xl sm:rounded-3xl space-y-3 hover:border-indigo-500/40 transition-all group"
              >
                <div className="flex items-center justify-between">
                  <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl sm:rounded-2xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-black text-sm border border-indigo-500/20 group-hover:scale-105 transition-transform shrink-0">
                    <Icon size={18} />
                  </div>
                  <span className="text-xs font-black text-slate-300 dark:text-slate-700">
                    {step.id}
                  </span>
                </div>

                <div className="space-y-1">
                  <h3 className="text-card-title text-slate-900 dark:text-slate-100">
                    {step.title}
                  </h3>
                  <span className="inline-block text-[10px] font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                    {step.badge}
                  </span>
                  <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed font-normal">
                    {step.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* =========================================================================
          SECTION: 3 CORE PILLARS
          ========================================================================= */}
      <section className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 w-full">
        <div className="glass-2 p-5 sm:p-7 rounded-2xl sm:rounded-3xl space-y-3">
          <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center shadow-sm shrink-0">
            <Zap size={20} />
          </div>
          <h3 className="text-card-title text-slate-900 dark:text-slate-100">Zero Manual Entry</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
            Forget copying recruiter emails. Confirmations and interview requests update your dashboard automatically.
          </p>
        </div>

        <div className="glass-2 p-5 sm:p-7 rounded-2xl sm:rounded-3xl space-y-3">
          <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center shadow-sm shrink-0">
            <UserCheck size={20} />
          </div>
          <h3 className="text-card-title text-slate-900 dark:text-slate-100">Human Oversight</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
            Ambiguous recruiter updates are flagged with clear evidence badges for one-click review and confirmation.
          </p>
        </div>

        <div className="glass-2 p-5 sm:p-7 rounded-2xl sm:rounded-3xl space-y-3">
          <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shadow-sm shrink-0">
            <ShieldCheck size={20} />
          </div>
          <h3 className="text-card-title text-slate-900 dark:text-slate-100">Privacy-First Architecture</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
            Read-only OAuth scope means we can never compose, send, or delete emails. Parsed securely in-memory.
          </p>
        </div>
      </section>

      {/* =========================================================================
          SECTION: CONVERSION CTA FOOTER
          ========================================================================= */}
      <section className="glass-3 p-6 sm:p-12 rounded-2xl sm:rounded-3xl text-center space-y-4 sm:space-y-6 relative overflow-hidden w-full">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600/10 via-indigo-600/10 to-purple-600/10 pointer-events-none" />
        
        <div className="relative z-10 max-w-2xl mx-auto space-y-3 sm:space-y-4">
          <h2 className="text-2xl sm:text-4xl font-black text-slate-900 dark:text-slate-100 tracking-tight text-balance">
            Take command of your job search today.
          </h2>
          <p className="text-xs sm:text-base text-slate-600 dark:text-slate-300 font-normal leading-relaxed">
            Connect your Gmail inbox in 10 seconds and watch your scattered applications assemble into a clean command center.
          </p>
          <div className="pt-2">
            <Link
              to="/login"
              className="btn btn-primary text-sm sm:text-base px-6 sm:px-8 py-3 sm:py-3.5 shadow-lg shadow-indigo-500/25 w-full sm:w-auto justify-center"
            >
              <span>Get Started with Google OAuth</span>
              <ArrowRight size={17} />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
