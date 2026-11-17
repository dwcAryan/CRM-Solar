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

export const fetchDashboard = async (): Promise<DashboardData> => {
  const res = await apiClient.get<DashboardData>('/api/dashboard/');
  return res.data;
};

export const fetchTodayLeads = async (): Promise<Lead[]> => {
  const res = await apiClient.get<Lead[] | { results: Lead[] }>('/api/leads/today/');
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
  status?: string;
  next_action?: string;
  next_followup_at?: string | null;
  lost_reason_id?: number | null;
  nurture_reason_id?: number | null;
}): Promise<{ message: string; activity_id: number; lead: Lead }> => {
  const res = await apiClient.post(`/api/leads/${leadId}/log-activity/`, data);
  return res.data;
};

export const mergeLead = async (duplicateId: number, targetLeadId: number, note?: string): Promise<any> => {
  const res = await apiClient.post(`/api/leads/${duplicateId}/merge/`, {
    target_lead_id: targetLeadId,
    note: note || '',
  });
  return res.data;
};

export const importCsvLeads = async (formData: FormData): Promise<{ created_count: number; error_count: number; errors: Array<{ row: number; error: string }> }> => {
  const res = await apiClient.post('/api/leads/import-csv/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
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
}): Promise<Survey> => {
  const res = await apiClient.post<Survey>('/api/surveys/book/', data);
  return res.data;
};

export const rescheduleSurvey = async (id: number, data: { scheduled_at: string; notes?: string }): Promise<Survey> => {
  const res = await apiClient.post<Survey>(`/api/surveys/${id}/reschedule/`, data);
  return res.data;
};

export const markSurveyMissed = async (id: number, notes?: string): Promise<Survey> => {
  const res = await apiClient.post<Survey>(`/api/surveys/${id}/mark-missed/`, { notes: notes || '' });
  return res.data;
};

export const cancelSurveyBySurveyor = async (id: number, notes?: string): Promise<Survey> => {
  const res = await apiClient.post<Survey>(`/api/surveys/${id}/cancel-by-surveyor/`, { notes: notes || '' });
  return res.data;
};

export const markSurveyDone = async (id: number, data: { site_suitable: boolean; notes?: string; lost_reason_id?: number | null }): Promise<Survey> => {
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
  brand: string;
  price: number;
  subsidy_amount?: number | null;
  notes?: string;
}): Promise<Quote> => {
  const res = await apiClient.post<Quote>('/api/quotes/', data);
  return res.data;
};

export const markQuoteSent = async (id: number, notes?: string): Promise<Quote> => {
  const res = await apiClient.post<Quote>(`/api/quotes/${id}/mark-sent/`, { notes: notes || '' });
  return res.data;
};

export const reviseQuote = async (id: number, data: {
  system_size_kw: number;
  brand: string;
  price: number;
  subsidy_amount?: number | null;
  notes?: string;
}): Promise<Quote> => {
  const res = await apiClient.post<Quote>(`/api/quotes/${id}/revise/`, data);
  return res.data;
};

export const acceptQuote = async (id: number, notes?: string): Promise<Quote> => {
  const res = await apiClient.post<Quote>(`/api/quotes/${id}/accept/`, { notes: notes || '' });
  return res.data;
};

export const rejectQuote = async (id: number, lost_reason_id: number, notes?: string): Promise<Quote> => {
  const res = await apiClient.post<Quote>(`/api/quotes/${id}/reject/`, { lost_reason_id, notes: notes || '' });
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

export const fetchUsers = async (): Promise<User[]> => {
  const res = await apiClient.get<any>('/api/users/');
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
