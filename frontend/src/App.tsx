import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider, createTheme } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import '@mantine/core/styles.css';
import '@mantine/dates/styles.css';
import '@mantine/notifications/styles.css';

import { AuthProvider } from './context/AuthContext';
import { RegionProvider } from './context/RegionContext';
import { ProtectedRoute } from './routes/ProtectedRoute';
import { AppLayout } from './components/layout/AppLayout';
import { LoginPage } from './pages/LoginPage';
import { ResetPasswordPage } from './pages/ResetPasswordPage';
import { DashboardPage } from './pages/DashboardPage';
import { TodayPage } from './pages/TodayPage';
import { LeadsListPage } from './pages/LeadsListPage';
import { LeadDetailPage } from './pages/LeadDetailPage';
import { SurveysPage } from './pages/SurveysPage';
import { QuotesPage } from './pages/QuotesPage';
import { ImportLeadsPage } from './pages/ImportLeadsPage';
import { AdminPage } from './pages/AdminPage';
import { HealthPage } from './pages/HealthPage';
import { ManagerAttentionPage } from './pages/ManagerAttentionPage';
import { SurveyorPortalPage } from './pages/SurveyorPortalPage';
import { RolesMatrixPage } from './pages/RolesMatrixPage';

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
                {/* Public routes */}
                <Route path="/login" element={<LoginPage />} />
                <Route path="/reset-password" element={<ResetPasswordPage />} />
                <Route path="/forgot-password" element={<ResetPasswordPage />} />

                {/* Protected routes wrapped in AppLayout */}
                <Route
                  element={
                    <ProtectedRoute>
                      <AppLayout />
                    </ProtectedRoute>
                  }
                >
                  <Route path="/" element={<DashboardPage />} />
                  <Route
                    path="/today"
                    element={
                      <ProtectedRoute permission="lead.view">
                        <TodayPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/leads"
                    element={
                      <ProtectedRoute permission="lead.view">
                        <LeadsListPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/leads/:id"
                    element={
                      <ProtectedRoute permission="lead.view">
                        <LeadDetailPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/manager-attention"
                    element={
                      <ProtectedRoute allowedRoles={['admin', 'manager']}>
                        <ManagerAttentionPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/my-surveys"
                    element={
                      <ProtectedRoute>
                        <SurveyorPortalPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/roles-matrix"
                    element={
                      <ProtectedRoute allowedRoles={['admin', 'manager']}>
                        <RolesMatrixPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/import-leads"
                    element={
                      <ProtectedRoute permission="lead.import">
                        <ImportLeadsPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route path="/surveys" element={<SurveysPage />} />
                  <Route
                    path="/quotes"
                    element={
                      <ProtectedRoute permission="quote.view">
                        <QuotesPage />
                      </ProtectedRoute>
                    }
                  />
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
