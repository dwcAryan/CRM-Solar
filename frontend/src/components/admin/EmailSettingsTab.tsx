import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Paper,
  Stack,
  Title,
  Text,
  Group,
  Badge,
  Button,
  TextInput,
  Table,
  Alert,
  Loader,
  Card,
  SimpleGrid,
  ThemeIcon,
  Tooltip,
} from '@mantine/core';
import {
  IconCheck,
  IconAlertTriangle,
  IconServer,
  IconSend,
  IconLock,
  IconRefresh,
} from '@tabler/icons-react';
import { fetchEmailSettings, sendTestEmail } from '../../api/client';
import type { EmailLog } from '../../api/types';

export const EmailSettingsTab: React.FC = () => {
  const queryClient = useQueryClient();
  const [testRecipient, setTestRecipient] = useState('');
  const [testSuccess, setTestSuccess] = useState<string | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['email-settings'],
    queryFn: fetchEmailSettings,
    refetchInterval: 30000,
  });

  const testMutation = useMutation({
    mutationFn: (toEmail: string) => sendTestEmail(toEmail || undefined),
    onSuccess: (res) => {
      setTestSuccess(res.message || 'Test email dispatched successfully!');
      setTestError(null);
      queryClient.invalidateQueries({ queryKey: ['email-settings'] });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.error || err.message || 'Failed to send test email.';
      setTestError(msg);
      setTestSuccess(null);
      queryClient.invalidateQueries({ queryKey: ['email-settings'] });
    },
  });

  const handleSendTest = (e: React.FormEvent) => {
    e.preventDefault();
    setTestSuccess(null);
    setTestError(null);
    testMutation.mutate(testRecipient.trim());
  };

  if (isLoading) {
    return (
      <Paper p="xl" withBorder radius="md">
        <Group justify="center" p="xl">
          <Loader size="md" color="yellow" />
          <Text size="sm" c="dimmed">
            Inspecting SMTP connectivity and loading audit logs...
          </Text>
        </Group>
      </Paper>
    );
  }

  if (error || !data) {
    return (
      <Alert icon={<IconAlertTriangle size={18} />} title="Failed to Load Email Settings" color="red">
        {(error as any)?.message || 'Could not retrieve email settings.'}
      </Alert>
    );
  }

  const { settings, diagnostics, logs } = data;
  const isSmtpHealthy = diagnostics.overall_status === 'pass';

  return (
    <Stack gap="lg">
      {/* 1. SMTP DIAGNOSTICS & STATUS CARD */}
      <Card withBorder radius="md" p="lg">
        <Group justify="space-between" mb="md" wrap="nowrap">
          <Group gap="sm">
            <ThemeIcon size={36} radius="md" color={isSmtpHealthy ? 'green' : 'red'} variant="light">
              <IconServer size={20} />
            </ThemeIcon>
            <div>
              <Title order={4}>SMTP Connection Status</Title>
              <Text size="xs" c="dimmed">
                Backend: <strong>{settings.backend}</strong> • Server: <strong>{settings.host || 'localhost'}:{settings.port}</strong>
              </Text>
            </div>
          </Group>
          <Group gap="xs">
            <Badge size="lg" color={isSmtpHealthy ? 'green' : 'red'} variant="filled">
              {isSmtpHealthy ? 'Connected & Verified' : 'Check Required'}
            </Badge>
            <Button
              size="xs"
              variant="default"
              leftSection={<IconRefresh size={14} />}
              onClick={() => refetch()}
              loading={isFetching}
            >
              Run Diagnostic
            </Button>
          </Group>
        </Group>

        {/* Step-by-step diagnostic breakdown */}
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="sm" mt="xs">
          {diagnostics.steps.map((step, idx) => (
            <Paper key={idx} p="xs" withBorder radius="sm" bg="var(--mantine-color-gray-0)">
              <Group gap="xs" wrap="nowrap">
                <ThemeIcon size={20} radius="xl" color={step.status === 'pass' ? 'green' : 'red'}>
                  {step.status === 'pass' ? <IconCheck size={12} /> : <IconAlertTriangle size={12} />}
                </ThemeIcon>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Text size="xs" fw={600} truncate>
                    {step.name}
                  </Text>
                  <Tooltip label={step.message} multiline w={260}>
                    <Text size="11px" c="dimmed" truncate>
                      {step.message}
                    </Text>
                  </Tooltip>
                </div>
              </Group>
            </Paper>
          ))}
        </SimpleGrid>
      </Card>

      {/* 2. SERVER CONFIGURATION & TEST DISPATCHER */}
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
        {/* Active Configuration (Credentials masked, in .env) */}
        <Paper withBorder radius="md" p="md">
          <Title order={5} mb="xs">
            Active Email Configuration
          </Title>
          <Text size="xs" c="dimmed" mb="md">
            Credentials are loaded securely from <code>backend/.env</code> and never stored in the database.
          </Text>

          <Stack gap="xs">
            <Group justify="space-between">
              <Text size="xs" c="dimmed">Host User (SMTP Account):</Text>
              <Text size="xs" fw={500}>{settings.host_user || 'None configured'}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="xs" c="dimmed">SMTP Password:</Text>
              <Group gap={4}>
                <IconLock size={13} color="gray" />
                <Text size="xs" fw={500}>{settings.host_password_masked || '••••••••'}</Text>
              </Group>
            </Group>
            <Group justify="space-between">
              <Text size="xs" c="dimmed">Default From Header:</Text>
              <Text size="xs" fw={500}>{settings.default_from_email}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="xs" c="dimmed">Security Protocol:</Text>
              <Badge size="sm" variant="light" color={settings.use_tls ? 'blue' : (settings.use_ssl ? 'indigo' : 'gray')}>
                {settings.use_tls ? 'STARTTLS (Port 587)' : (settings.use_ssl ? 'SSL (Port 465)' : 'Plain')}
              </Badge>
            </Group>
            <Group justify="space-between">
              <Text size="xs" c="dimmed">Network Timeout:</Text>
              <Text size="xs" fw={500}>{settings.timeout}s</Text>
            </Group>
          </Stack>
        </Paper>

        {/* Live Test Dispatcher */}
        <Paper withBorder radius="md" p="md">
          <Title order={5} mb="xs">
            Send Live Test Email
          </Title>
          <Text size="xs" c="dimmed" mb="md">
            Verify real SMTP transmission with an immediate HTML test notification.
          </Text>

          {testSuccess && (
            <Alert icon={<IconCheck size={16} />} title="Delivery Succeeded" color="green" mb="sm">
              {testSuccess}
            </Alert>
          )}

          {testError && (
            <Alert icon={<IconAlertTriangle size={16} />} title="Delivery Failed" color="red" mb="sm">
              <Text size="xs" style={{ wordBreak: 'break-word' }}>{testError}</Text>
            </Alert>
          )}

          <form onSubmit={handleSendTest}>
            <Stack gap="sm">
              <TextInput
                label="Recipient Email Address"
                placeholder="name@example.com (leave blank for your email)"
                value={testRecipient}
                onChange={(e) => setTestRecipient(e.currentTarget.value)}
                size="sm"
              />
              <Button
                type="submit"
                color="yellow"
                leftSection={<IconSend size={16} />}
                loading={testMutation.isPending}
              >
                Send Test Email
              </Button>
            </Stack>
          </form>
        </Paper>
      </SimpleGrid>

      {/* 3. RECENT EMAIL AUDIT LOG (LAST 50) */}
      <Paper withBorder radius="md" p="md">
        <Group justify="space-between" mb="md">
          <div>
            <Title order={5}>Outgoing Email Log (Last 50 Entries)</Title>
            <Text size="xs" c="dimmed">
              Immutable audit history of outgoing follow-up digests, survey reminders, and system alerts.
            </Text>
          </div>
          <Badge variant="light" color="gray">
            {logs.length} logged
          </Badge>
        </Group>

        {logs.length === 0 ? (
          <Text size="sm" c="dimmed" ta="center" py="xl">
            No emails recorded yet. Send a test email above or wait for automated morning digests.
          </Text>
        ) : (
          <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Timestamp</Table.Th>
                <Table.Th>Recipient</Table.Th>
                <Table.Th>Subject</Table.Th>
                <Table.Th>Template</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Error / Reason</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {logs.map((log: EmailLog) => {
                const statusColor =
                  log.status === 'sent' ? 'green' : log.status === 'failed' ? 'red' : 'gray';

                return (
                  <Table.Tr key={log.id}>
                    <Table.Td style={{ whiteSpace: 'nowrap', fontSize: '12px' }}>
                      {new Date(log.created_at).toLocaleString()}
                    </Table.Td>
                    <Table.Td style={{ fontSize: '12px', fontWeight: 500 }}>{log.to}</Table.Td>
                    <Table.Td style={{ fontSize: '12px' }}>
                      <div>{log.subject}</div>
                      {log.lead_name && (
                        <Text size="11px" c="dimmed">
                          Lead: {log.lead_name}
                        </Text>
                      )}
                    </Table.Td>
                    <Table.Td>
                      <Badge size="xs" variant="outline">
                        {log.template}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Badge size="xs" color={statusColor} variant="filled">
                        {log.status.toUpperCase()}
                      </Badge>
                    </Table.Td>
                    <Table.Td style={{ maxWidth: 220, fontSize: '11px', color: '#64748b' }}>
                      {log.error ? (
                        <Tooltip label={log.error} multiline w={260}>
                          <Text size="11px" c="red" truncate>
                            {log.error}
                          </Text>
                        </Tooltip>
                      ) : (
                        '-'
                      )}
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        )}
      </Paper>
    </Stack>
  );
};
