// Application types
export type ApplicationSource = 
  | 'LinkedIn' | 'Indeed' | 'Company Website' | 'Naukri' | 'Wellfound' 
  | 'Referral' | 'Email' | 'Other';

export type ApplicationStatus = 
  | 'Applied' | 'Under Review' | 'Assessment' | 'Interview' | 'Offer' | 'Rejected'
  | 'Withdrawn' | 'No Response' | 'Stale' | 'Ghosted' | 'Needs Review' | 'Unknown';

export type EmailEventType = 
  | 'application_confirmation' | 'application_received' | 'interview_invitation'
  | 'assessment_invitation' | 'recruiter_outreach' | 'rejection'
  | 'offer' | 'next_round' | 'hiring_manager_message' | 'coding_assessment'
  | 'interview_scheduling' | 'application_status_update' | 'position_filled'
  | 'candidate_not_selected' | 'application_withdrawn' | 'other';

export type ProcessingStatus = 
  | 'detected' | 'needs_review' | 'ignored' | 'processed' | 'failed';

// Application model
export interface Application {
  id: number;
  company: string;
  job_title: string;
  job_url?: string;
  location?: string;
  source: ApplicationSource;
  application_date: string;
  current_status: ApplicationStatus;
  status_updated_at: string;
  last_email_date?: string;
  last_activity_date?: string;
  confidence: number;
  notes?: string;
  review_reason?: string;
  recruiter_name?: string;
  recruiter_email?: string;
  is_ai_detected: boolean;
  is_manual: boolean;
  needs_review: boolean;
  created_at: string;
  updated_at: string;
}

// Application create/update DTO
export interface ApplicationCreateDTO {
  company: string;
  job_title: string;
  job_url?: string;
  location?: string;
  source: ApplicationSource;
  application_date: string;
  current_status: ApplicationStatus;
  notes?: string;
}

export type TriagePriority = 'P1' | 'P2' | 'P3';

// Processed Email model
export interface ProcessedEmail {
  id: number;
  gmail_message_id: string;
  thread_id: string;
  object_storage_key?: string;
  b2_object_key?: string;
  r2_object_key?: string;
  compressed_size_bytes?: number;
  triage_priority?: TriagePriority;
  sender: string;
  sender_domain?: string;
  subject: string;
  received_at: string;
  snippet?: string;
  is_job_related: boolean;
  company?: string;
  job_title?: string;
  detected_status?: ApplicationStatus;
  event_type?: EmailEventType;
  interview_date?: string;
  ai_confidence: number;
  processing_status: ProcessingStatus;
  application?: number;
  created_at: string;
  updated_at: string;
}

// Status History model
export interface StatusHistory {
  id: number;
  application: number;
  previous_status?: ApplicationStatus;
  new_status: ApplicationStatus;
  source: string;
  timestamp: string;
  related_email?: number;
}

// Follow-up model
export interface FollowUp {
  id: number;
  application: number;
  draft_subject: string;
  draft_body: string;
  created_at: string;
  is_sent: boolean;
}

// Sync summary
export interface SyncSummary {
  emails_scanned: number;
  job_related_emails: number;
  applications_updated: number;
  new_applications: number;
  needs_review: number;
  message: string;
  status?: 'idle' | 'running' | 'completed' | 'failed';
  has_more?: boolean;
  page?: number;
  cumulative?: {
    emails_scanned: number;
    job_related_emails: number;
    applications_updated: number;
    new_applications: number;
    needs_review: number;
    pages_processed: number;
  };
}

export interface SyncStatus {
  status: 'idle' | 'running' | 'completed' | 'failed';
  page: number;
  has_more: boolean;
  last_sync: string | null;
  started_at?: string | null;
  stats: {
    emails_scanned: number;
    job_related_emails: number;
    applications_updated: number;
    new_applications: number;
    needs_review: number;
    pages_processed: number;
  };
  // Granular pipeline counters (authoritative from DB)
  emails_fetched?: number;
  emails_stored?: number;
  emails_queued?: number;
  emails_processing?: number;
  emails_processed?: number;
  emails_pending?: number;
  job_related?: number;
  applications_updated?: number;
  new_applications?: number;
  queue?: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
    is_active: boolean;
    total_applications: number;
  };
}

// Sync log
export interface SyncLog {
  id: number;
  started_at: string;
  completed_at?: string;
  emails_scanned: number;
  job_related_emails: number;
  applications_updated: number;
  new_applications: number;
  needs_review: number;
  error_message?: string;
}

// Application stats
export interface ApplicationStats {
  total_applications: number;
  applied: number;
  assessment: number;
  interview: number;
  offer: number;
  rejected: number;
  no_response: number;
  stale: number;
  needs_review: number;
}

// User model
export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  gmail_connected: boolean;
  gmail_last_sync?: string;
  stale_application_threshold: number;
  created_at: string;
  updated_at: string;
}

// User settings
export interface UserSettings {
  notifications_enabled: boolean;
  sync_frequency: string;
}

// Analytics
export interface UserAnalytics {
  total_applications: number;
  applications_this_month: number;
  interview_rate: number;
  response_rate: number;
  offer_rate: number;
  rejection_rate: number;
  avg_days_to_response: number;
}

// API response types
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

// Auth types
export interface LoginResponse {
  user: User;
  message: string;
}
