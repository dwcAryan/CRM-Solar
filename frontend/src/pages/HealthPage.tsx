import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Container,
  Paper,
  Title,
  Text,
  Badge,
  Group,
  Stack,
  Button,
  Loader,
  Alert,
  ThemeIcon,
  Code,
} from '@mantine/core';
import { IconCheck, IconAlertTriangle, IconRefresh, IconServer, IconDatabase } from '@tabler/icons-react';
import { fetchHealth } from '../api/client';
import type { HealthResponse } from '../api/types';

export const HealthPage: React.FC = () => {
  const { data, error, isLoading, isError, refetch, isFetching } = useQuery<HealthResponse, Error>({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 30000,
    retry: 1,
  });

  return (
    <Container size="sm" py="xl">
      <Paper withBorder shadow="sm" p="xl" radius="md">
        <Stack gap="md">
          <Group justify="space-between">
            <Group>
              <ThemeIcon size="lg" radius="md" color="yellow" variant="light">
                <IconServer size={22} />
              </ThemeIcon>
              <div>
                <Title order={3}>Solar CRM System Health</Title>
                <Text size="xs" c="dimmed">Backend & Database Connectivity Status</Text>
              </div>
            </Group>
            <Button
              variant="light"
              size="xs"
              leftSection={<IconRefresh size={14} />}
              onClick={() => refetch()}
              loading={isFetching}
            >
              Refresh
            </Button>
          </Group>

          {isLoading ? (
            <Group justify="center" p="xl">
              <Loader size="md" />
              <Text size="sm" c="dimmed">Probing backend /api/health/...</Text>
            </Group>
          ) : isError ? (
            <Alert
              icon={<IconAlertTriangle size={16} />}
              title="Connection Error"
              color="red"
              variant="light"
            >
              <Text size="sm">Failed to connect to backend API server at {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}.</Text>
              <Text size="xs" c="dimmed" mt={4}>Details: {error?.message}</Text>
            </Alert>
          ) : data ? (
            <Stack gap="sm">
              <Paper withBorder p="md" radius="sm">
                <Group justify="space-between" mb="xs">
                  <Text size="sm" fw={500}>Overall System Status</Text>
                  <Badge color={data.status === 'ok' ? 'green' : 'orange'} variant="filled">
                    {data.status.toUpperCase()}
                  </Badge>
                </Group>

                <Group justify="space-between">
                  <Group gap="xs">
                    <IconDatabase size={16} />
                    <Text size="sm">PostgreSQL Database</Text>
                  </Group>
                  <Badge
                    leftSection={data.database === 'connected' ? <IconCheck size={12} /> : <IconAlertTriangle size={12} />}
                    color={data.database === 'connected' ? 'teal' : 'red'}
                    variant="light"
                  >
                    {data.database}
                  </Badge>
                </Group>
              </Paper>

              <Text size="xs" c="dimmed">
                Service: <Code>{data.service || 'Solar CRM Backend'}</Code>
              </Text>
            </Stack>
          ) : null}
        </Stack>
      </Paper>
    </Container>
  );
};
