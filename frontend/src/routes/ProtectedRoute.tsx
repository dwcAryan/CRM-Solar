import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Center, Loader, Container, Text, Paper, Button } from '@mantine/core';
import { useAuth } from '../context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: Array<'admin' | 'manager' | 'salesperson' | 'surveyor'>;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <Center style={{ height: '100vh', width: '100vw' }}>
        <Loader size="lg" color="yellow" />
      </Center>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return (
      <Container size="sm" py="xl">
        <Paper withBorder p="xl" radius="md" style={{ textAlign: 'center' }}>
          <Text size="lg" fw={600} c="red" mb="sm">
            Access Denied
          </Text>
          <Text size="sm" c="dimmed" mb="md">
            Your role ({user.role}) is not authorized to access this page.
          </Text>
          <Button variant="light" onClick={() => window.history.back()}>
            Go Back
          </Button>
        </Paper>
      </Container>
    );
  }

  return <>{children}</>;
};
