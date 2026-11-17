export interface HealthResponse {
  status: 'ok' | 'degraded';
  database: 'connected' | 'disconnected';
  service?: string;
  error?: string;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
}
