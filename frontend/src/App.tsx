import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider, createTheme } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';

import { AuthProvider } from './context/AuthContext';
import { RegionProvider } from './context/RegionContext';
import { ProtectedRoute } from './routes/ProtectedRoute';
import { AppLayout } from './components/layout/AppLayout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { TodayPage } from './pages/TodayPage';
import { LeadsListPage } from './pages/LeadsListPage';
import { LeadDetailPage } from './pages/LeadDetailPage';
import { SurveysPage } from './pages/SurveysPage';
import { QuotesPage } from './pages/QuotesPage';
import { ImportLeadsPage } from './pages/ImportLeadsPage';
import { AdminPage } from './pages/AdminPage';
import { HealthPage } from './pages/HealthPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const theme = createTheme({
  primaryColor: 'yellow',
  fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={theme} defaultColorScheme="light">
        <Notifications position="top-right" />
        <BrowserRouter>
          <AuthProvider>
            <RegionProvider>
              <Routes>
                {/* Public route */}
                <Route path="/login" element={<LoginPage />} />

                {/* Protected routes wrapped in AppLayout */}
                <Route
                  element={
                    <ProtectedRoute>
                      <AppLayout />
                    </ProtectedRoute>
                  }
                >
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/today" element={<TodayPage />} />
                  <Route path="/leads" element={<LeadsListPage />} />
                  <Route path="/leads/:id" element={<LeadDetailPage />} />
                  <Route path="/import-leads" element={<ImportLeadsPage />} />
                  <Route path="/surveys" element={<SurveysPage />} />
                  <Route path="/quotes" element={<QuotesPage />} />
                  <Route
                    path="/admin"
                    element={
                      <ProtectedRoute allowedRoles={['admin', 'manager']}>
                        <AdminPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route path="/health" element={<HealthPage />} />
                </Route>

                {/* Fallback */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </RegionProvider>
          </AuthProvider>
        </BrowserRouter>
      </MantineProvider>
    </QueryClientProvider>
  );
};

export default App;
