import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  ShieldCheck, Lock, EyeOff, FileText, CheckCircle2, 
  Mail, Server, UserCheck, AlertCircle, Trash2, ArrowLeft 
} from 'lucide-react';

export default function PrivacyPage() {
  useEffect(() => {
    document.title = 'ApplyTrack AI | Privacy Policy';
    window.scrollTo(0, 0);
  }, []);

  const lastUpdated = 'August 28, 2026';

  return (
    <div className="py-8 sm:py-14 max-w-4xl mx-auto px-4 sm:px-6 space-y-10">
      {/* Header Banner */}
      <div className="space-y-4 text-center sm:text-left pb-6 border-b border-slate-200 dark:border-slate-800">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800/80 text-indigo-700 dark:text-indigo-300 text-xs font-bold tracking-wide uppercase">
          <ShieldCheck size={14} className="text-indigo-600 dark:text-indigo-400" />
          <span>Security & Compliance</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-black text-slate-900 dark:text-slate-100 tracking-tight">
          Privacy Policy
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Last updated: <span className="font-semibold text-slate-700 dark:text-slate-300">{lastUpdated}</span>
        </p>
      </div>

      {/* Summary Highlight Card */}
      <div className="card p-6 sm:p-7 bg-gradient-to-br from-indigo-50/60 via-white to-blue-50/40 dark:from-slate-900 dark:via-slate-900/90 dark:to-slate-800/60 border-indigo-100 dark:border-slate-800 space-y-4">
        <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <Lock size={18} className="text-indigo-600 dark:text-indigo-400" />
          Our Privacy Commitments at a Glance
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs text-slate-600 dark:text-slate-300">
          <div className="flex items-start gap-2.5">
            <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
            <span><strong>Read-Only Gmail Scope:</strong> We never send, modify, or delete your emails.</span>
          </div>
          <div className="flex items-start gap-2.5">
            <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
            <span><strong>No Ad Targeting:</strong> Your email data is never used or sold for advertising.</span>
          </div>
          <div className="flex items-start gap-2.5">
            <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
            <span><strong>Ephemeral Email Processing:</strong> Message bodies are filtered in-memory for job tracking and never retained permanently.</span>
          </div>
          <div className="flex items-start gap-2.5">
            <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
            <span><strong>User Controlled:</strong> Disconnect Gmail or delete your tracking history at any time.</span>
          </div>
        </div>
      </div>

      {/* Policy Content Sections */}
      <div className="space-y-10 text-slate-700 dark:text-slate-300 text-sm leading-relaxed">
        
        {/* Section 1 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">1. Introduction</h2>
          <p>
            ApplyTrack AI ("we", "us", or "our") operates the web application located at <a href="https://applytrackai.netlify.app" className="text-indigo-600 dark:text-indigo-400 font-semibold hover:underline">https://applytrackai.netlify.app</a>. ApplyTrack AI is an automated job application management platform designed to help job seekers organize their career pipeline by automatically identifying job application confirmations, assessment requests, interview invitations, and status updates directly from recruiter emails.
          </p>
          <p>
            This Privacy Policy explains what information we collect, how we access and process your data, how we store application information, and your choices and rights regarding your personal information.
          </p>
        </section>

        {/* Section 2 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">2. Google Account Information Used</h2>
          <p>
            When you sign in to ApplyTrack AI using Google OAuth 2.0, we receive basic profile information from Google to establish and maintain your authenticated session:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm">
            <li><strong>Email Address:</strong> Used as your unique account identifier and to associate your application tracker records with your profile.</li>
            <li><strong>Name (First Name and Last Name):</strong> Used for personalizing your dashboard interface.</li>
            <li><strong>Google User ID:</strong> Used for secure session management and authentication verification.</li>
          </ul>
        </section>

        {/* Section 3 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">3. Gmail Data Accessed & Read-Only Scope</h2>
          <p>
            With your explicit consent via Google OAuth authorization, ApplyTrack AI requests access to the read-only Gmail scope:
          </p>
          <div className="p-3.5 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 font-mono text-xs text-indigo-700 dark:text-indigo-300">
            https://www.googleapis.com/auth/gmail.readonly
          </div>
          <p>
            <strong>What this allows:</strong> ApplyTrack AI accesses message metadata (headers, subject, sender, timestamp, and message snippets) to scan your mailbox for job application-related correspondence.
          </p>
          <p>
            <strong>What this strictly prohibits:</strong>
          </p>
          <ul className="list-disc pl-5 space-y-1 text-xs sm:text-sm text-slate-600 dark:text-slate-400">
            <li>ApplyTrack AI <strong>cannot</strong> compose, send, forward, or draft emails from your account.</li>
            <li>ApplyTrack AI <strong>cannot</strong> modify, label, archive, or delete any of your Gmail messages or threads.</li>
            <li>ApplyTrack AI <strong>cannot</strong> access your contacts, calendar, or Google Drive files.</li>
          </ul>
        </section>

        {/* Section 4 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">4. How Gmail Data is Processed & AI Classification</h2>
          <p>
            When synchronization runs (either via manual trigger or periodic 10-minute background checks while you are active on the application):
          </p>
          <ol className="list-decimal pl-5 space-y-2 text-xs sm:text-sm">
            <li>
              <strong>Keyword & Sender Filtering:</strong> We scan recent message headers and snippets for job-related signals (e.g., confirmation notices from LinkedIn, Greenhouse, Lever, Workday, Indeed, or recruiter domains). Non-job personal and financial emails are ignored immediately.
            </li>
            <li>
              <strong>Classification Engine:</strong> For detected job-related emails, our backend classification engine extracts the company name, job role, and event type (such as <em>application confirmation</em>, <em>coding assessment</em>, <em>interview invitation</em>, <em>offer</em>, or <em>rejection</em>).
            </li>
            <li>
              <strong>Application Matching & Status Updates:</strong> The extracted event is matched to an existing application or used to initialize a new application record in your personal dashboard.
            </li>
            <li>
              <strong>Metadata Storage:</strong> We only store the parsed metadata needed for the service (company name, role, detected status, message date, sender, subject line, and classification status). <strong>Raw full-text email bodies are not stored permanently in our database.</strong>
            </li>
          </ol>
        </section>

        {/* Section 5 - Google API Limited Use Policy */}
        <section className="space-y-3 p-5 rounded-2xl bg-indigo-50/50 dark:bg-indigo-950/30 border border-indigo-200/80 dark:border-indigo-800/60">
          <h2 className="text-base font-bold text-indigo-900 dark:text-indigo-200 flex items-center gap-2">
            <ShieldCheck size={18} className="text-indigo-600 dark:text-indigo-400" />
            5. Google API Limited Use Disclosure
          </h2>
          <p className="text-xs sm:text-sm text-indigo-950 dark:text-indigo-100 leading-relaxed font-medium">
            ApplyTrack AI's use and transfer of information received from Google APIs to any other app will adhere to the{' '}
            <a 
              href="https://developers.google.com/terms/api-services-user-data-policy" 
              target="_blank" 
              rel="noopener noreferrer"
              className="underline font-bold text-indigo-600 dark:text-indigo-300 hover:text-indigo-800"
            >
              Google API Services User Data Policy
            </a>
            , including the Limited Use requirements.
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-xs text-indigo-900 dark:text-indigo-200">
            <li>We only use data to provide and improve user-facing features that are prominent in the user interface (automated job application tracking).</li>
            <li>We do not transfer data to third parties, except as necessary to provide the service, comply with applicable laws, or as part of a merger/acquisition.</li>
            <li>We do not use or transfer user data for serving advertisements, including retargeting, personalized, or interest-based advertising.</li>
            <li>We do not allow humans to read user data unless we have obtained your affirmative agreement for specific messages, doing so is necessary for security purposes (such as investigating a bug or abuse), or to comply with applicable law.</li>
          </ul>
        </section>

        {/* Section 6 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">6. Data Storage & Security Practices</h2>
          <p>
            We implement robust administrative, technical, and physical security safeguards to protect your personal information:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm">
            <li><strong>Encryption in Transit:</strong> All communications between your browser, our backend server, and Google API servers are encrypted using Transport Layer Security (TLS/HTTPS).</li>
            <li><strong>Token Security:</strong> OAuth access and refresh tokens are securely encrypted and managed through server-side session authentication cookies with <code>HttpOnly</code>, <code>SameSite</code>, and <code>Secure</code> flags enabled.</li>
            <li><strong>User Isolation:</strong> Database queries and application records are strictly partitioned by authenticated user IDs. No user can view or query another user's applications or email logs.</li>
            <li><strong>Database Hosting:</strong> Our PostgreSQL database is hosted on secure, compliant cloud infrastructure with automated backups and encrypted storage volumes.</li>
          </ul>
        </section>

        {/* Section 7 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">7. Data Sharing & Third-Party Services</h2>
          <p>
            <strong>We do not sell, rent, or trade your personal information or Gmail data to any third party under any circumstances.</strong>
          </p>
          <p>
            We only interact with the following trusted infrastructure providers to operate the application:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-xs sm:text-sm">
            <li><strong>Google Cloud Platform:</strong> For OAuth 2.0 user authentication and Gmail API read-only data access.</li>
            <li><strong>Groq AI:</strong> For stateless, real-time natural language classification of job-related email subject lines and snippets without retaining or training on your data.</li>
            <li><strong>Cloud Hosting & Database:</strong> For hosting our secure Django API backend and encrypted PostgreSQL database.</li>
          </ul>
        </section>

        {/* Section 8 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">8. User Rights, Gmail Disconnect & Data Deletion</h2>
          <p>
            You retain full ownership and control over your personal data:
          </p>
          <ul className="list-disc pl-5 space-y-2 text-xs sm:text-sm">
            <li>
              <strong>Disconnect Gmail:</strong> You can disconnect your Gmail integration at any time directly from the <strong>Settings</strong> page in your dashboard or by revoking ApplyTrack AI's access in your <a href="https://myaccount.google.com/permissions" target="_blank" rel="noopener noreferrer" className="text-indigo-600 dark:text-indigo-400 underline">Google Security Settings</a>. Once disconnected, all active sync tokens are invalidated immediately.
            </li>
            <li>
              <strong>Delete Applications:</strong> You can delete individual application records or clear your email activity log directly from the user interface.
            </li>
            <li>
              <strong>Complete Account & Data Purge:</strong> To permanently delete your account and all associated application tracking data, you can submit a request to our support email at <span className="font-semibold text-slate-900 dark:text-slate-100">support@applytrackai.com</span>. All user records will be deleted from our database within 7 business days.
            </li>
          </ul>
        </section>

        {/* Section 9 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">9. Changes to This Privacy Policy</h2>
          <p>
            We may update this Privacy Policy from time to time to reflect changes in our legal obligations, features, or data processing practices. Any changes will be posted on this page with an updated "Last updated" date. We encourage you to review this page periodically.
          </p>
        </section>

        {/* Section 10 */}
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">10. Contact Information</h2>
          <p>
            If you have questions, concerns, or requests regarding this Privacy Policy or our data privacy practices, please contact us at:
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
          <Link to="/terms" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">Terms of Service</Link>
          <span>&bull;</span>
          <Link to="/login" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">Sign In</Link>
        </div>
      </div>
    </div>
  );
}
