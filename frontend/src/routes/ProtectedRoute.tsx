import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Center, Loader, Container, Text, Paper, Button } from '@mantine/core';
import { useAuth } from '../context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: Array<'admin' | 'manager' | 'salesperson' | 'surveyor'>;
  permission?: string;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles, permission }) => {
  const { user, isAuthenticated, isLoading, can } = useAuth();
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

  const roleDenied = allowedRoles && user && !allowedRoles.includes(user.role);
  const permissionDenied = permission && !can(permission);

  if (roleDenied || permissionDenied) {
    return (
      <Container size="sm" py="xl">
        <Paper withBorder p="xl" radius="md" style={{ textAlign: 'center' }}>
          <Text size="lg" fw={600} c="red" mb="sm">
            Access Denied
          </Text>
          <Text size="sm" c="dimmed" mb="md">
            Your role ({user?.role}) does not have permission to access this work area.
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
