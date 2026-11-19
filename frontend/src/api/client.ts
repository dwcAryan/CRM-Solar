import axios from 'axios';
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import type {
  TokenResponse,
  User,
  DashboardData,
  Lead,
  Outcome,
  LostReason,
  NurtureReason,
  LeadSource,
  PolicySettings,
  Survey,
  Quote,
  Notification,
  MessageTemplate,
  HealthResponse,
  ImportBatch,
  CsvPreviewResponse,
  CsvImportResponse,
  AISuggestion,
  Region,
  State,
  RoofType,
  PropertyType,
} from './types';

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

export const getAccessToken = (): string | null => localStorage.getItem('access_token');
export const getRefreshToken = (): string | null => localStorage.getItem('refresh_token');

export const setTokens = (access: string, refresh?: string): void => {
  localStorage.setItem('access_token', access);
  if (refresh) {
    localStorage.setItem('refresh_token', refresh);
  }
};

export const clearTokens = (): void => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
};

// Request interceptor
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    const currentLang = localStorage.getItem('solar_crm_lang') || 'en';
    if (config.headers) {
      config.headers['X-App-Language'] = currentLang;
      config.headers['Accept-Language'] = currentLang;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for automatic JWT token refresh
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: any) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/api/token/')) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refresh = getRefreshToken();
      if (!refresh) {
        clearTokens();
        isRefreshing = false;
        return Promise.reject(error);
      }

      try {
        const response = await axios.post<TokenResponse>(`${API_BASE_URL}/api/token/refresh/`, {
          refresh,
        });
        const newAccess = response.data.access;
        setTokens(newAccess, response.data.refresh);
        apiClient.defaults.headers.common.Authorization = `Bearer ${newAccess}`;
        originalRequest.headers.Authorization = `Bearer ${newAccess}`;
        processQueue(null, newAccess);
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        clearTokens();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// --- Typed API Methods ---

export const fetchHealth = async (): Promise<HealthResponse> => {
  const res = await apiClient.get<HealthResponse>('/api/health/');
  return res.data;
};

export const apiLogin = async (credentials: { username: string; password: string }): Promise<TokenResponse> => {
  const res = await apiClient.post<TokenResponse>('/api/token/', credentials);
  setTokens(res.data.access, res.data.refresh);
  return res.data;
};

export const fetchMe = async (): Promise<User> => {
  const res = await apiClient.get<User>('/api/me/');
  return res.data;
};

export const fetchDashboard = async (params?: Record<string, any>): Promise<DashboardData> => {
  const res = await apiClient.get<DashboardData>('/api/dashboard/', { params });
  return res.data;
};

export const fetchTodayLeads = async (region?: string): Promise<Lead[]> => {
  const params = region ? { region } : undefined;
  const res = await apiClient.get<Lead[] | { results: Lead[] }>('/api/leads/today/', { params });
  if (Array.isArray(res.data)) return res.data;
  return res.data.results || [];
};

export const fetchLeads = async (params?: Record<string, any>): Promise<{ results: Lead[]; count: number }> => {
  const res = await apiClient.get<any>('/api/leads/', { params });
  if (Array.isArray(res.data)) {
    return { results: res.data, count: res.data.length };
  }
  return { results: res.data.results || [], count: res.data.count || 0 };
};

export const fetchLead = async (id: number): Promise<Lead> => {
  const res = await apiClient.get<Lead>(`/api/leads/${id}/`);
  return res.data;
};

export const fetchActivities = async (params?: Record<string, any>): Promise<any[]> => {
  const res = await apiClient.get<any>('/api/activities/', { params });
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const createLead = async (data: Partial<Lead>, force: boolean = false): Promise<Lead> => {
  const url = force ? '/api/leads/?force=true' : '/api/leads/';
  const res = await apiClient.post<Lead>(url, data);
  return res.data;
};

export const updateLead = async (id: number, data: Partial<Lead>): Promise<Lead> => {
  const res = await apiClient.patch<Lead>(`/api/leads/${id}/`, data);
  return res.data;
};

export const logActivity = async (leadId: number, data: {
  type: string;
  outcome_id?: number | null;
  notes?: string;
  remark?: string;
  status?: string;
  next_action?: string;
  next_followup_at?: string | null;
  lost_reason_id?: number | null;
  nurture_reason_id?: number | null;
}): Promise<{ message: string; activity_id: number; lead: Lead }> => {
  const res = await apiClient.post(`/api/leads/${leadId}/log-activity/`, data);
  return res.data;
};

export const addRemark = async (leadId: number, remark: string): Promise<{ message: string; activity: any; lead: Lead }> => {
  const res = await apiClient.post(`/api/leads/${leadId}/add-remark/`, { remark });
  return res.data;
};

export const mergeLead = async (duplicateId: number, targetLeadId: number, note?: string, remark?: string): Promise<any> => {
  const res = await apiClient.post(`/api/leads/${duplicateId}/merge/`, {
    target_lead_id: targetLeadId,
    note: note || '',
    remark: remark || '',
  });
  return res.data;
};

export const bulkActionLeads = async (payload: {
  lead_ids: number[];
  action: 'assign' | 'change_source';
  value: number;
  remark?: string;
}): Promise<{ message: string; updated_count: number }> => {
  const res = await apiClient.post('/api/leads/bulk-action/', payload);
  return res.data;
};

// CSV Import & Export
export const previewCsv = async (file: File): Promise<CsvPreviewResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await apiClient.post<CsvPreviewResponse>('/api/leads/preview-csv/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const importCsvLeads = async (formData: FormData): Promise<CsvImportResponse> => {
  const res = await apiClient.post<CsvImportResponse>('/api/leads/import-csv/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const fetchImportBatches = async (): Promise<ImportBatch[]> => {
  const res = await apiClient.get<any>('/api/import-batches/');
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const undoImportBatch = async (batchId: number): Promise<{ message: string; deleted_count: number; batch: ImportBatch }> => {
  const res = await apiClient.post(`/api/import-batches/${batchId}/undo/`);
  return res.data;
};

export const downloadSampleCsv = (region?: string): void => {
  const queryStr = region ? `?region=${encodeURIComponent(region)}` : '';
  window.open(`${API_BASE_URL}/api/leads/import-sample-csv/${queryStr}`, '_blank');
};

export const downloadFailedRowsCsv = (batchId: number): void => {
  window.open(`${API_BASE_URL}/api/import-batches/${batchId}/failed-rows-csv/`, '_blank');
};

export const exportLeadsCsv = async (params?: Record<string, any>): Promise<void> => {
  const res = await apiClient.get('/api/leads/export-csv/', {
    params,
    responseType: 'blob',
  });
  const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const disposition = res.headers['content-disposition'];
  let filename = 'leads_export.csv';
  if (disposition) {
    const match = disposition.match(/filename\*?=['"]?(?:UTF-\d['"]*)?([^;\r\n"']*)['"]?/i);
    if (match && match[1]) {
      filename = decodeURIComponent(match[1]);
    }
  }
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};

export const fetchOutcomes = async (stage?: string): Promise<Outcome[]> => {
  const params = stage ? { stage } : {};
  const res = await apiClient.get<any>('/api/masters/outcomes/', { params });
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const fetchLostReasons = async (): Promise<LostReason[]> => {
  const res = await apiClient.get<any>('/api/masters/lost-reasons/');
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const fetchNurtureReasons = async (): Promise<NurtureReason[]> => {
  const res = await apiClient.get<any>('/api/masters/nurture-reasons/');
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const fetchLeadSources = async (): Promise<LeadSource[]> => {
  const res = await apiClient.get<any>('/api/masters/lead-sources/');
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const fetchPolicySettings = async (): Promise<PolicySettings> => {
  const res = await apiClient.get<any>('/api/masters/policy-settings/');
  const list = Array.isArray(res.data) ? res.data : (res.data.results || []);
  return list[0];
};

export const updatePolicySettings = async (id: number, data: Partial<PolicySettings>): Promise<PolicySettings> => {
  const res = await apiClient.patch<PolicySettings>(`/api/masters/policy-settings/${id}/`, data);
  return res.data;
};

export const fetchSurveys = async (params?: Record<string, any>): Promise<Survey[]> => {
  const res = await apiClient.get<any>('/api/surveys/', { params });
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const bookSurvey = async (data: {
  lead_id: number;
  scheduled_at: string;
  surveyor_id?: number | null;
  notes?: string;
  remark?: string;
}): Promise<Survey> => {
  const res = await apiClient.post<Survey>('/api/surveys/book/', data);
  return res.data;
};

export const rescheduleSurvey = async (id: number, data: { scheduled_at: string; notes?: string; remark?: string }): Promise<Survey> => {
  const res = await apiClient.post<Survey>(`/api/surveys/${id}/reschedule/`, data);
  return res.data;
};

export const markSurveyMissed = async (id: number, notes?: string, remark?: string): Promise<Survey> => {
  const res = await apiClient.post<Survey>(`/api/surveys/${id}/mark-missed/`, { notes: notes || '', remark: remark || '' });
  return res.data;
};

export const cancelSurveyBySurveyor = async (id: number, notes?: string, remark?: string): Promise<Survey> => {
  const res = await apiClient.post<Survey>(`/api/surveys/${id}/cancel-by-surveyor/`, { notes: notes || '', remark: remark || '' });
  return res.data;
};

export const markSurveyDone = async (id: number, data: {
  site_suitable: boolean;
  notes?: string;
  remark?: string;
  lost_reason_id?: number | null;
}): Promise<Survey> => {
  const res = await apiClient.post<Survey>(`/api/surveys/${id}/mark-done/`, data);
  return res.data;
};

export const fetchQuotes = async (params?: Record<string, any>): Promise<Quote[]> => {
  const res = await apiClient.get<any>('/api/quotes/', { params });
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const createQuote = async (data: {
  lead_id: number;
  system_size_kw: number;
  battery_kwh?: number | null;
  brand: string;
  price: number;
  subsidy_amount?: number | null;
  notes?: string;
  remark?: string;
}): Promise<Quote> => {
  const res = await apiClient.post<Quote>('/api/quotes/', data);
  return res.data;
};

export const markQuoteSent = async (id: number, notes?: string, remark?: string): Promise<Quote> => {
  const res = await apiClient.post<Quote>(`/api/quotes/${id}/mark-sent/`, { notes: notes || '', remark: remark || '' });
  return res.data;
};

export const reviseQuote = async (id: number, data: {
  system_size_kw: number;
  battery_kwh?: number | null;
  brand: string;
  price: number;
  subsidy_amount?: number | null;
  notes?: string;
  remark?: string;
}): Promise<Quote> => {
  const res = await apiClient.post<Quote>(`/api/quotes/${id}/revise/`, data);
  return res.data;
};

export const acceptQuote = async (id: number, notes?: string, remark?: string): Promise<Quote> => {
  const res = await apiClient.post<Quote>(`/api/quotes/${id}/accept/`, { notes: notes || '', remark: remark || '' });
  return res.data;
};

export const rejectQuote = async (id: number, lost_reason_id: number, notes?: string, remark?: string): Promise<Quote> => {
  const res = await apiClient.post<Quote>(`/api/quotes/${id}/reject/`, { lost_reason_id, notes: notes || '', remark: remark || '' });
  return res.data;
};

export const fetchNotifications = async (): Promise<Notification[]> => {
  const res = await apiClient.get<any>('/api/notifications/');
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const markNotificationRead = async (id: number): Promise<Notification> => {
  const res = await apiClient.post<Notification>(`/api/notifications/${id}/mark-read/`);
  return res.data;
};

export const markAllNotificationsRead = async (): Promise<{ count: number }> => {
  const res = await apiClient.post<{ count: number }>('/api/notifications/mark-all-read/');
  return res.data;
};

export const fetchUnreadNotificationCount = async (): Promise<number> => {
  const res = await apiClient.get<{ unread_count: number }>('/api/notifications/unread-count/');
  return res.data.unread_count;
};

export const fetchUsers = async (params?: Record<string, any>): Promise<User[]> => {
  const res = await apiClient.get<any>('/api/users/', { params });
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const fetchTemplates = async (): Promise<MessageTemplate[]> => {
  return [
    { id: 1, name: 'survey_confirmation', body: 'Namaste {customer_name}! Your solar site survey with Solar CRM has been confirmed for {time}. Our solar engineer will visit your property at {address}.', is_active: true, created_at: '' },
    { id: 2, name: 'survey_reminder', body: 'Namaste {customer_name}, this is a gentle reminder that your solar site survey is scheduled for tomorrow at {time}. Our engineer will inspect your roof space and electrical setup at {address}.', is_active: true, created_at: '' },
    { id: 3, name: 'brochure_and_savings', body: 'Namaste {customer_name}! Thank you for your interest in rooftop solar. You can save up to 80% on your electricity bill.', is_active: true, created_at: '' },
    { id: 4, name: 'quote_sent', body: 'Namaste {customer_name}! Your customized solar proposal for a {system_size_kw} kW system ({brand}) amounting to ₹{price} is ready.', is_active: true, created_at: '' },
  ];
};

// Phase 7 AI Suggestions
export const fetchAISuggestion = async (leadId: number, refresh: boolean = false): Promise<AISuggestion> => {
  const res = await apiClient.get<any>(`/api/leads/${leadId}/ai-suggestions/`, {
    params: refresh ? { refresh: 'true' } : undefined,
  });
  return res.data.suggestion || res.data;
};

export const generateAISuggestion = async (leadId: number, refresh: boolean = true): Promise<AISuggestion> => {
  const res = await apiClient.post<any>(`/api/leads/${leadId}/ai-suggestions/`, { refresh });
  return res.data.suggestion || res.data;
};

// Multi-Country Masters
export const fetchRegions = async (): Promise<Region[]> => {
  const res = await apiClient.get<any>('/api/masters/regions/');
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const fetchStates = async (region?: string): Promise<State[]> => {
  const res = await apiClient.get<any>('/api/masters/states/', { params: region ? { region } : undefined });
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const fetchRoofTypes = async (region?: string): Promise<RoofType[]> => {
  const res = await apiClient.get<any>('/api/masters/roof-types/', { params: region ? { region } : undefined });
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const fetchPropertyTypes = async (region?: string): Promise<PropertyType[]> => {
  const res = await apiClient.get<any>('/api/masters/property-types/', { params: region ? { region } : undefined });
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const fetchAuditLogs = async (params?: Record<string, any>): Promise<any> => {
  const res = await apiClient.get<any>('/api/audit-logs/', { params });
  return res.data;
};

// Privacy & Compliance
export const fetchLeadPrivacyDossier = async (leadId: number, format: 'json' | 'pdf' = 'json'): Promise<any> => {
  if (format === 'pdf') {
    const res = await apiClient.get(`/api/leads/${leadId}/privacy-export/?format=pdf`, {
      responseType: 'blob',
    });
    return res.data;
  }
  const res = await apiClient.get(`/api/leads/${leadId}/privacy-export/?format=json`);
  return res.data;
};

export const anonymizeLead = async (leadId: number, reason: string): Promise<{ message: string; lead: Lead }> => {
  const res = await apiClient.post(`/api/leads/${leadId}/anonymize/`, { reason });
  return res.data;
};

export const correctLeadData = async (leadId: number, updates: Record<string, any>, reason: string): Promise<{ message: string; lead: Lead }> => {
  const res = await apiClient.post(`/api/leads/${leadId}/privacy-correct/`, { updates, reason });
  return res.data;
};

export const checkLeadDncr = async (leadId: number, dncr_status?: string, notes?: string): Promise<{ message: string; lead: Lead }> => {
  const res = await apiClient.post(`/api/leads/${leadId}/check-dncr/`, { dncr_status, notes });
  return res.data;
};

// Phase 9: RBAC & Work Areas
export const fetchUnassignedLeads = async (): Promise<Lead[]> => {
  const res = await apiClient.get<any>('/api/leads/unassigned/');
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const fetchLostApprovals = async (): Promise<Lead[]> => {
  const res = await apiClient.get<any>('/api/leads/lost-approvals/');
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const approveLostLead = async (leadId: number, data?: { notes?: string; remark?: string }): Promise<any> => {
  const res = await apiClient.post(`/api/leads/${leadId}/approve-lost/`, data || {});
  return res.data;
};

export const rejectLostLead = async (
  leadId: number,
  data: { reason: string; next_followup_at: string }
): Promise<any> => {
  const res = await apiClient.post(`/api/leads/${leadId}/reject-lost/`, data);
  return res.data;
};

export const assignLead = async (leadId: number, userId: number, reason?: string): Promise<any> => {
  const res = await apiClient.post(`/api/leads/${leadId}/assign/`, { assigned_to_id: userId, reason });
  return res.data;
};

export const bulkAssignLeads = async (leadIds: number[], userId: number, reason?: string): Promise<any> => {
  const res = await apiClient.post('/api/leads/bulk-assign/', {
    lead_ids: leadIds,
    assigned_to_id: userId,
    reason,
  });
  return res.data;
};

export const autoDistributeLeads = async (leadIds?: number[], salespersonIds?: number[]): Promise<any> => {
  const res = await apiClient.post('/api/leads/auto-distribute/', {
    lead_ids: leadIds,
    salesperson_ids: salespersonIds,
  });
  return res.data;
};

export const assignSurveyor = async (surveyId: number, surveyorId: number): Promise<any> => {
  const res = await apiClient.post(`/api/surveys/${surveyId}/assign-surveyor/`, {
    surveyor_id: surveyorId,
  });
  return res.data;
};

export const fetchMySurveys = async (params?: Record<string, any>): Promise<Survey[]> => {
  const res = await apiClient.get<any>('/api/surveys/my-surveys/', { params });
  return Array.isArray(res.data) ? res.data : (res.data.results || []);
};

export const uploadSurveyPhoto = async (surveyId: number, file: File, caption?: string): Promise<any> => {
  const formData = new FormData();
  formData.append('survey', String(surveyId));
  formData.append('image', file);
  if (caption) formData.append('caption', caption);
  const res = await apiClient.post('/api/surveys/photos/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const fetchRolesMatrix = async (): Promise<Record<string, Record<string, string>>> => {
  const res = await apiClient.get<Record<string, Record<string, string>>>('/api/roles-matrix/');
  return res.data;
};

export const softDeleteLead = async (leadId: number, reason: string): Promise<any> => {
  const res = await apiClient.delete(`/api/leads/${leadId}/`, { data: { reason } });
  return res.data;
};

export const manualChangeStatus = async (
  leadId: number,
  data: { status: string; reason: string; next_action?: string; next_followup_at?: string }
): Promise<any> => {
  const res = await apiClient.post(`/api/leads/${leadId}/manual-status/`, data);
  return res.data;
};

// Phase 12 Email Settings & Password Reset
export const fetchEmailSettings = async (): Promise<import('./types').EmailSettingsResponse> => {
  const res = await apiClient.get<import('./types').EmailSettingsResponse>('/api/notifications/email-settings/');
  return res.data;
};

export const sendTestEmail = async (to?: string): Promise<{ status: string; message?: string; error?: string }> => {
  const res = await apiClient.post('/api/notifications/email-test/', { to });
  return res.data;
};

export const requestPasswordReset = async (email: string): Promise<{ message: string }> => {
  const res = await apiClient.post<{ message: string }>('/api/auth/password-reset/', { email });
  return res.data;
};

export const confirmPasswordReset = async (data: {
  uid: string;
  token: string;
  new_password: string;
}): Promise<{ message: string }> => {
  const res = await apiClient.post<{ message: string }>('/api/auth/password-reset/confirm/', data);
  return res.data;
};

// Phase 13 Tour & Helpbot API
export const fetchTourState = async (): Promise<import('./types').UserTourState> => {
  const res = await apiClient.get<import('./types').UserTourState>('/api/me/tour/');
  return res.data;
};

export const updateTourState = async (
  data: Partial<import('./types').UserTourState>
): Promise<import('./types').UserTourState> => {
  const res = await apiClient.patch<import('./types').UserTourState>('/api/me/tour/', data);
  return res.data;
};

export const resetTourState = async (): Promise<{ status: string }> => {
  const res = await apiClient.post<{ status: string }>('/api/me/tour/', { action: 'reset' });
  return res.data;
};

export interface OnboardingState {
  visible: boolean;
  items: Array<{ id: string; label: string; done: boolean }>;
  completed_at: string | null;
  dismissed_at: string | null;
  is_collapsed: boolean;
  just_completed?: boolean;
}

export const fetchOnboardingState = async (): Promise<OnboardingState> => {
  const res = await apiClient.get<OnboardingState>('/api/me/onboarding/');
  return res.data;
};

export const recordOnboardingEvent = async (event: string): Promise<OnboardingState> => {
  const res = await apiClient.post<OnboardingState>('/api/me/onboarding/', { action: 'event', event });
  return res.data;
};

export const dismissOnboarding = async (): Promise<OnboardingState> => {
  const res = await apiClient.post<OnboardingState>('/api/me/onboarding/', { action: 'dismiss' });
  return res.data;
};

export const toggleCollapseOnboarding = async (is_collapsed?: boolean): Promise<{ is_collapsed: boolean }> => {
  const res = await apiClient.post<{ is_collapsed: boolean }>('/api/me/onboarding/', { action: 'collapse', is_collapsed });
  return res.data;
};

export const completeOnboarding = async (): Promise<OnboardingState> => {
  const res = await apiClient.post<OnboardingState>('/api/me/onboarding/', { action: 'complete' });
  return res.data;
};

export const askHelpbot = async (
  query: string,
  context?: Record<string, any>
): Promise<import('./types').HelpbotAskResponse> => {
  const res = await apiClient.post<import('./types').HelpbotAskResponse>('/api/helpbot/ask/', {
    query,
    context: context || {},
  });
  return res.data;
};

export const fetchHelpbotSuggestions = async (): Promise<string[]> => {
  const res = await apiClient.get<import('./types').HelpbotSuggestionsResponse>('/api/helpbot/suggestions/');
  return res.data.suggestions;
};

export const submitHelpbotFeedback = async (
  payload: import('./types').HelpbotFeedbackPayload
): Promise<{ status: string }> => {
  const res = await apiClient.post<{ status: string }>('/api/helpbot/feedback/', payload);
  return res.data;
};

export const fetchHelpbotStats = async (): Promise<import('./types').HelpbotStatsResponse> => {
  const res = await apiClient.get<import('./types').HelpbotStatsResponse>('/api/helpbot/stats/');
  return res.data;
};

export const fetchHelpbotUnanswered = async (resolved?: boolean): Promise<import('./types').HelpbotUnansweredItem[]> => {
  const params = resolved !== undefined ? { resolved } : {};
  const res = await apiClient.get<import('./types').HelpbotUnansweredItem[]>('/api/helpbot/unanswered/', { params });
  return res.data;
};

export const updateHelpbotUnanswered = async (
  id: number,
  resolved: boolean
): Promise<{ status: string }> => {
  const res = await apiClient.patch<{ status: string }>(`/api/helpbot/unanswered/${id}/`, { resolved });
  return res.data;
};

export const triggerHelpbotReindex = async (): Promise<{ status: string; message: string }> => {
  const res = await apiClient.post<{ status: string; message: string }>('/api/helpbot/rebuild-index/');
  return res.data;
};

export const changePassword = async (data: {
  old_password?: string;
  new_password: string;
}): Promise<{ status: string; message: string }> => {
  const res = await apiClient.post<{ status: string; message: string }>('/api/auth/change-password/', data);
  return res.data;
};


