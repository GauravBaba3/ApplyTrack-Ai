import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  FileText, Shield, AlertCircle, CheckCircle2, 
  HelpCircle, Scale, ArrowLeft 
} from 'lucide-react';

export default function TermsPage() {
  useEffect(() => {
    document.title = 'ApplyTrack AI | Terms of Service';
    window.scrollTo(0, 0);
  }, []);

  const lastUpdated = 'August 28, 2026';

  return (
    <div className="py-8 sm:py-14 max-w-4xl mx-auto px-4 sm:px-6 space-y-10">
      {/* Header Banner */}
      <div className="space-y-4 text-center sm:text-left pb-6 border-b border-slate-200 dark:border-slate-800">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800/80 text-indigo-700 dark:text-indigo-300 text-xs font-bold tracking-wide uppercase">
          <Scale size={14} className="text-indigo-600 dark:text-indigo-400" />
          <span>Legal Agreement</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-black text-slate-900 dark:text-slate-100 tracking-tight">
          Terms of Service
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Last updated: <span className="font-semibold text-slate-700 dark:text-slate-300">{lastUpdated}</span>
        </p>
      </div>

      {/* Summary Highlight Card */}
      <div className="card p-6 sm:p-7 bg-gradient-to-br from-indigo-50/60 via-white to-blue-50/40 dark:from-slate-900 dark:via-slate-900/90 dark:to-slate-800/60 border-indigo-100 dark:border-slate-800 space-y-3">
        <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <FileText size={18} className="text-indigo-600 dark:text-indigo-400" />
          Terms Overview
        </h2>
        <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
          By signing in to ApplyTrack AI or connecting your Google account, you agree to these Terms of Service. ApplyTrack AI provides autonomous, read-only job application tracking and status aggregation to help job seekers manage their career search.
        </p>
      </div>

      {/* Policy Content Sections */}
      <div className="space-y-10 text-slate-700 dark:text-slate-300 text-sm leading-relaxed">
        
        {/* Section 1 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">1. Acceptance of Terms</h2>
          <p>
            These Terms of Service ("Terms") constitute a legally binding agreement between you ("User", "you") and ApplyTrack AI ("we", "us", "our") regarding your access to and use of the ApplyTrack AI website located at <a href="https://applytrackai.netlify.app" className="text-indigo-600 dark:text-indigo-400 font-semibold hover:underline">https://applytrackai.netlify.app</a> and all associated software, APIs, and services.
          </p>
          <p>
            By accessing or using ApplyTrack AI, you acknowledge that you have read, understood, and agree to be bound by these Terms and our <Link to="/privacy" className="text-indigo-600 dark:text-indigo-400 font-semibold underline">Privacy Policy</Link>. If you do not agree to these Terms, do not use the service.
          </p>
        </section>

        {/* Section 2 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">2. Description of the Service</h2>
          <p>
            ApplyTrack AI provides automated tools for job seekers, including:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm">
            <li>Google OAuth authentication and secure session management.</li>
            <li>Read-only Gmail synchronization to scan for recruiter correspondence, application confirmations, interview invitations, coding assessments, and hiring decisions.</li>
            <li>Automated extraction, status classification, and timeline generation for job applications.</li>
            <li>Search metrics, conversion funnel analytics, and AI-assisted recruiter follow-up draft generation.</li>
          </ul>
        </section>

        {/* Section 3 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">3. Google & Gmail Integration (Read-Only)</h2>
          <p>
            To enable automated synchronization, ApplyTrack AI requests read-only access to your Gmail account via Google OAuth 2.0 (<code>https://www.googleapis.com/auth/gmail.readonly</code>). You acknowledge and agree that:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm">
            <li>Access is strictly read-only; ApplyTrack AI cannot send, modify, label, or delete emails from your account.</li>
            <li>You can revoke ApplyTrack AI's access at any time through the dashboard Settings page or via your Google Security Account dashboard.</li>
            <li>ApplyTrack AI complies with the Google API Services User Data Policy, including the Limited Use requirements.</li>
          </ul>
        </section>

        {/* Section 4 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">4. User Responsibilities & Acceptable Use</h2>
          <p>
            When using ApplyTrack AI, you agree that you will not:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-xs sm:text-sm">
            <li>Use the service for any illegal, fraudulent, or unauthorized purpose.</li>
            <li>Attempt to reverse-engineer, decompile, or compromise the security or integrity of our backend APIs and database.</li>
            <li>Impersonate any other individual or connect email accounts for which you do not possess lawful authority.</li>
            <li>Attempt to bypass rate limits, quotas, or authentication checks.</li>
          </ul>
        </section>

        {/* Section 5 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">5. AI Classifications & Draft Follow-ups Disclaimer</h2>
          <p>
            ApplyTrack AI uses machine learning and natural language processing models to classify email contents and generate suggested recruiter follow-up drafts. You acknowledge that:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm">
            <li>AI classifications are automated estimates and may occasionally miscategorize ambiguous or unstructured emails. You retain full control to edit application details or status manually at any time.</li>
            <li>AI-generated follow-up drafts are provided solely as suggestions. You are solely responsible for reviewing and editing all communication before sending it to employers. ApplyTrack AI never sends emails autonomously.</li>
          </ul>
        </section>

        {/* Section 6 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">6. Intellectual Property Rights</h2>
          <p>
            ApplyTrack AI and its original features, user interface, brand assets, code, and documentation remain the exclusive property of ApplyTrack AI and its licensors. You retain all ownership rights to your personal job applications and job search records.
          </p>
        </section>

        {/* Section 7 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">7. Disclaimer of Warranties</h2>
          <p>
            ApplyTrack AI is provided on an "AS IS" and "AS AVAILABLE" basis without warranties of any kind, whether express or implied, including but not limited to implied warranties of merchantability, fitness for a particular purpose, and non-infringement.
          </p>
          <p>
            We do not warrant that the service will be uninterrupted, error-free, completely secure, or that automated parsing will detect 100% of incoming job-related emails across all email providers and custom templates.
          </p>
        </section>

        {/* Section 8 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">8. Limitation of Liability</h2>
          <p>
            To the maximum extent permitted by applicable law, in no event shall ApplyTrack AI, its founders, directors, employees, or partners be liable for any indirect, incidental, special, consequential, or punitive damages, including loss of data, missed job opportunities, employment decisions, or loss of profits arising out of or related to your use of the service.
          </p>
        </section>

        {/* Section 9 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">9. Account Termination & Data Deletion</h2>
          <p>
            You may terminate your account at any time by disconnecting your Gmail integration in Settings or requesting account deletion at <span className="font-semibold text-slate-900 dark:text-slate-100">support@applytrackai.com</span>. We reserve the right to suspend or terminate access to accounts that violate these Terms or engage in abusive activity.
          </p>
        </section>

        {/* Section 10 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">10. Changes to Terms</h2>
          <p>
            We reserve the right to modify or replace these Terms at any time. Material modifications will be posted on this page with an updated "Last updated" date. Your continued use of the service after any changes constitutes acceptance of the new Terms.
          </p>
        </section>

        {/* Section 11 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">11. Contact Information</h2>
          <p>
            If you have any questions about these Terms of Service, please contact our team at:
          </p>
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1 text-xs sm:text-sm">
            <p className="font-bold text-slate-900 dark:text-slate-100">ApplyTrack AI Team</p>
            <p>Email: <a href="mailto:support@applytrackai.com" className="text-indigo-600 dark:text-indigo-400 font-semibold hover:underline">support@applytrackai.com</a></p>
            <p>Website: <a href="https://applytrackai.netlify.app" className="text-indigo-600 dark:text-indigo-400 font-semibold hover:underline">https://applytrackai.netlify.app</a></p>
          </div>
        </section>
      </div>

      {/* Bottom Navigation */}
      <div className="pt-6 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
        <Link to="/" className="inline-flex items-center gap-1.5 text-indigo-600 dark:text-indigo-400 font-bold hover:underline">
          <ArrowLeft size={14} /> Back to Homepage
        </Link>
        <div className="flex items-center gap-4">
          <Link to="/privacy" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">Privacy Policy</Link>
          <span>&bull;</span>
          <Link to="/login" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">Sign In</Link>
        </div>
      </div>
    </div>
  );
}
