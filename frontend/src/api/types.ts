export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'admin' | 'manager' | 'salesperson' | 'surveyor';
  phone: string;
  is_active: boolean;
  date_joined: string;
}

export interface TokenResponse {
  access: string;
  refresh: string;
}

export interface Outcome {
  id: number;
  stage: 'call' | 'survey' | 'quote';
  name: string;
  default_status: string;
  default_next_action: string;
  default_followup_days: number | null;
  followup_date_required_manually: boolean;
  is_terminal: boolean;
  requires_lost_reason: boolean;
  requires_nurture_reason: boolean;
  sort_order: number;
  is_active: boolean;
}

export interface LostReason {
  id: number;
  name: string;
  sort_order: number;
  is_active: boolean;
}

export interface NurtureReason {
  id: number;
  name: string;
  sort_order: number;
  is_active: boolean;
}

export interface LeadSource {
  id: number;
  name: string;
  sort_order: number;
  is_active: boolean;
}

export interface PolicySettings {
  id: number;
  max_call_attempts_before_unreachable: number;
  unreachable_followup_days: number;
  nurture_default_days: number;
  who_can_mark_lost: string;
}

export interface LeadStatusHistory {
  id: number;
  lead: number;
  old_status: string;
  new_status: string;
  changed_by: number | null;
  changed_by_name?: string;
  changed_at: string;
  note: string;
  remark?: string;
}

export interface Lead {
  id: number;
  name: string;
  phone: string;
  alt_phone?: string;
  email?: string;
  address?: string;
  city: string;
  pincode?: string;
  source?: number | null;
  source_name?: string;
  property_type?: string;
  monthly_bill?: number | null;
  roof_type?: string;
  owner_or_tenant?: string;
  assigned_to?: number | null;
  assigned_to_name?: string;
  status: string;
  next_action?: string;
  next_followup_at?: string | null;
  lost_reason?: number | null;
  lost_reason_name?: string;
  nurture_reason?: number | null;
  nurture_reason_name?: string;
  do_not_contact: boolean;
  attempt_count: number;
  won_at?: string | null;
  import_batch?: number | null;
  remark?: string;
  status_history?: LeadStatusHistory[];
  created_at: string;
  updated_at: string;
}

export interface Activity {
  id: number;
  lead: number;
  lead_name?: string;
  type: 'call' | 'whatsapp' | 'visit' | 'note';
  outcome?: number | null;
  outcome_name?: string;
  notes: string;
  remark?: string;
  status_after: string;
  next_action: string;
  next_followup_at?: string | null;
  created_by?: number | null;
  created_by_name?: string;
  created_at: string;
}

export interface SurveyPhoto {
  id: number;
  survey: number;
  image: string;
  caption?: string;
  uploaded_at: string;
}

export interface Survey {
  id: number;
  lead: number;
  lead_name?: string;
  scheduled_at: string;
  surveyor?: number | null;
  surveyor_name?: string;
  status: 'booked' | 'rescheduled' | 'missed' | 'done' | 'cancelled';
  site_suitable?: boolean | null;
  notes?: string;
  remark?: string;
  reschedule_count: number;
  photos?: SurveyPhoto[];
  created_at: string;
  updated_at: string;
}

export interface Quote {
  id: number;
  lead: number;
  lead_name?: string;
  version: number;
  system_size_kw: number;
  brand: string;
  price: number;
  subsidy_amount?: number | null;
  status: 'draft' | 'sent' | 'revised' | 'accepted' | 'rejected';
  notes?: string;
  remark?: string;
  created_by?: number | null;
  created_by_name?: string;
  created_at: string;
}

export interface Notification {
  id: number;
  user: number;
  message: string;
  link?: string;
  is_read: boolean;
  created_at: string;
}

export interface MessageTemplate {
  id: number;
  name: string;
  description?: string;
  body: string;
  is_active: boolean;
  created_at: string;
}

export interface MessageLog {
  id: number;
  phone: string;
  lead?: number | null;
  template_name?: string;
  params: Record<string, any>;
  message_text: string;
  status: 'sent' | 'blocked' | 'failed';
  error_message?: string;
  created_at: string;
}

export interface DashboardData {
  status_counts: Record<string, number>;
  funnel: {
    new: number;
    interested: number;
    survey: number;
    quote_sent: number;
    won: number;
  };
  overdue_followups: number;
  leads_per_source: Array<{ source: string; count: number }>;
  won_this_month: number;
  total_active_leads: number;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  database: 'connected' | 'disconnected';
  service?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Phase 6 CSV Import & Batch Types
export interface ImportBatch {
  id: number;
  file_name: string;
  imported_by?: number | null;
  imported_by_name?: string;
  imported_at: string;
  total_rows: number;
  imported_count: number;
  skipped_count: number;
  duplicate_count: number;
  failed_count: number;
  is_reverted: boolean;
  reverted_at?: string | null;
  reverted_by?: number | null;
  reverted_by_name?: string;
  failed_rows_json?: Array<{
    row: number;
    name?: string;
    phone?: string;
    error: string;
  }>;
}

export interface CsvPreviewResponse {
  headers: string[];
  suggested_mapping: Record<string, string>;
  preview_rows: Array<Record<string, string>>;
  total_rows: number;
}

export interface CsvImportResponse {
  batch_id: number;
  total_rows: number;
  imported_count: number;
  skipped_count: number;
  duplicate_count: number;
  failed_count: number;
  errors: Array<{
    row: number;
    name?: string;
    phone?: string;
    error: string;
  }>;
}
