export interface Region {
  code: string;
  name: string;
  currency: string;
  currency_symbol: string;
  default_timezone: string;
  phone_country_code: string;
  locale: string;
  tax_label: string;
  tax_rate: number;
  incentive_label: string;
  electricity_provider_label: string;
  preferred_channels: string;
  calling_hours_policy: 'warn' | 'block';
  calling_hours_start: string;
  calling_hours_end_weekday: string;
  calling_hours_end_saturday: string;
  sunday_calling_allowed: boolean;
  dncr_validity_days: number;
  opt_out_line_text: string;
  privacy_notice_text: string;
  region_notes: string;
  is_active: boolean;
  sort_order: number;
}

export interface State {
  id: number;
  region: string;
  code: string;
  name: string;
  default_timezone: string;
  is_active: boolean;
  sort_order: number;
}

export interface RoofType {
  id: number;
  region: string;
  name: string;
  is_active: boolean;
  sort_order: number;
}

export interface PropertyType {
  id: number;
  region: string;
  name: string;
  is_active: boolean;
  sort_order: number;
}

export interface PublicHoliday {
  id: number;
  region: string;
  name: string;
  date: string;
  notes?: string;
}

export interface AuditLog {
  id: number;
  user?: number | null;
  user_name?: string;
  action: string;
  timestamp: string;
  lead?: number | null;
  lead_id_recorded?: number | null;
  reason: string;
  details: Record<string, any>;
  ip_address?: string;
}

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
  allowed_regions?: Region[] | string[];
  default_region?: string | null;
  default_timezone?: string;
  permissions?: string[];
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
  phone_e164?: string;
  phone_display?: string;
  phone_raw_backup?: string;
  alt_phone?: string;
  alt_phone_e164?: string;
  alt_phone_display?: string;
  email?: string;
  region?: string;
  region_code?: string;
  state?: string;
  city: string;
  suburb?: string;
  pincode?: string;
  postcode?: string;
  address?: string;
  timezone?: string;
  currency?: string;
  currency_symbol?: string;
  source?: number | null;
  source_name?: string;
  property_type?: string;
  monthly_bill?: number | null;
  bill_amount?: number | null;
  bill_period?: 'monthly' | 'two_monthly' | 'quarterly' | 'annual' | string;
  normalized_monthly_bill?: number | null;
  electricity_provider?: string;
  roof_type?: string;
  owner_or_tenant?: string;
  assigned_to?: number | null;
  assigned_to_name?: string;
  status: string;
  next_action?: string;
  next_followup_at?: string | null;
  next_followup_display?: string;
  user_next_followup_display?: string;
  lost_reason?: number | null;
  lost_reason_name?: string;
  lost_pending_reason?: number | null;
  lost_pending_reason_name?: string | null;
  lost_pending_notes?: string | null;
  nurture_reason?: number | null;
  nurture_reason_name?: string;
  do_not_contact: boolean;
  attempt_count: number;
  won_at?: string | null;
  consent_status?: 'consented' | 'unknown' | 'withdrawn' | string;
  consent_source?: string;
  consent_date?: string | null;
  opt_out_calls?: boolean;
  opt_out_sms?: boolean;
  opt_out_whatsapp?: boolean;
  opt_out_email?: boolean;
  dncr_status?: 'not_on_register' | 'on_register' | 'exempt' | string;
  dncr_checked_at?: string | null;
  dncr_checked_by?: number | null;
  dncr_checked_by_name?: string | null;
  is_within_calling_hours?: boolean;
  calling_hours_reason?: string;
  whatsapp_url?: string;
  tel_url?: string;
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
  type: 'call' | 'whatsapp' | 'sms' | 'visit' | 'note';
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
  region?: string;
  region_code?: string;
  currency?: string;
  currency_symbol?: string;
  tax_included?: boolean;
  tax_rate?: number | null;
  tax_amount?: number | null;
  incentive_label?: string;
  incentive_amount?: number | null;
  subsidy_amount?: number | null;
  battery_kwh?: number | null;
  total_amount?: number;
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

export interface AttentionLead {
  id: number;
  name: string;
  phone: string;
  city: string;
  status: string;
  risk_level: 'low' | 'medium' | 'high';
  reason: string;
  next_followup_at?: string | null;
  assigned_to_name?: string;
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
  won_value_by_currency?: Record<string, number>;
  total_active_leads: number;
  needs_attention?: AttentionLead[];
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

export interface HelpQueryResponse {
  matched: boolean;
  id?: string;
  title: string;
  category: string;
  answer: string;
  action?: { label: string; path: string };
  related?: string[];
}

export interface HelpFaqItem {
  id: string;
  title: string;
  category: string;
  action?: { label: string; path: string };
}

// Phase 7 AI Suggestions Types
export interface AIOnjectionReply {
  objection: string;
  reply: string;
}

export interface AISuggestionOutput {
  situation_summary: string;
  risk_level: 'low' | 'medium' | 'high';
  risk_reason: string;
  best_next_action: string;
  suggested_follow_up_timing: string;
  suggested_outcome_to_log: string;
  talking_points: string[];
  suggested_whatsapp_message: string;
  objections_to_expect: AIOnjectionReply[];
}

export interface AISuggestion {
  id: number;
  lead: number;
  generated_by?: number | null;
  generated_by_name?: string;
  generated_at: string;
  provider: string;
  model: string;
  input_hash: string;
  output_json: AISuggestionOutput;
  tokens_used: number;
  is_fallback: boolean;
  error_message?: string;
}
