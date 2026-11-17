import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Container,
  Title,
  Text,
  Group,
  Stack,
  Card,
  Badge,
  Button,
  Tabs,
  Table,
  Paper,
  FileInput,
  Alert,
  NumberInput,
  Select,
  ThemeIcon,
  SimpleGrid,
  Code,
  Box,
} from '@mantine/core';
import {
  IconSettings,
  IconUsers,
  IconFileSpreadsheet,
  IconClipboardList,
  IconAdjustments,
  IconBrandWhatsapp,
  IconUpload,
  IconCheck,
  IconAlertTriangle,
} from '@tabler/icons-react';
import {
  fetchUsers,
  fetchOutcomes,
  fetchLostReasons,
  fetchNurtureReasons,
  fetchLeadSources,
  fetchPolicySettings,
  updatePolicySettings,
  fetchTemplates,
  importCsvLeads,
} from '../api/client';
import type {
  User,
  Outcome,
  LostReason,
  NurtureReason,
  LeadSource,
  PolicySettings,
  MessageTemplate,
} from '../api/types';

export const AdminPage: React.FC = () => {
  const queryClient = useQueryClient();

  // CSV Import State
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<{
    created_count: number;
    error_count: number;
    errors: Array<{ row: number; error: string }>;
  } | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  // Policy Settings State
  const [maxAttempts, setMaxAttempts] = useState<number>(5);
  const [unreachableDays, setUnreachableDays] = useState<number>(14);
  const [nurtureDays, setNurtureDays] = useState<number>(90);
  const [whoCanMarkLost, setWhoCanMarkLost] = useState<string>('manager');
  const [policySaved, setPolicySaved] = useState(false);

  // Queries
  const { data: users = [] } = useQuery<User[]>({
    queryKey: ['users'],
    queryFn: fetchUsers,
  });

  const { data: outcomes = [] } = useQuery<Outcome[]>({
    queryKey: ['outcomes'],
    queryFn: () => fetchOutcomes(),
  });

  const { data: lostReasons = [] } = useQuery<LostReason[]>({
    queryKey: ['lost-reasons'],
    queryFn: fetchLostReasons,
  });

  const { data: nurtureReasons = [] } = useQuery<NurtureReason[]>({
    queryKey: ['nurture-reasons'],
    queryFn: fetchNurtureReasons,
  });

  const { data: leadSources = [] } = useQuery<LeadSource[]>({
    queryKey: ['lead-sources'],
    queryFn: fetchLeadSources,
  });

  const { data: templates = [] } = useQuery<MessageTemplate[]>({
    queryKey: ['templates'],
    queryFn: fetchTemplates,
  });

  const { data: policy } = useQuery<PolicySettings>({
    queryKey: ['policy-settings'],
    queryFn: fetchPolicySettings,
  });

  // Sync policy settings when loaded
  React.useEffect(() => {
    if (policy) {
      setMaxAttempts(policy.max_call_attempts_before_unreachable);
      setUnreachableDays(policy.unreachable_followup_days);
      setNurtureDays(policy.nurture_default_days);
      setWhoCanMarkLost(policy.who_can_mark_lost);
    }
  }, [policy]);

  // Mutations
  const importMutation = useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return importCsvLeads(formData);
    },
    onSuccess: (data: any) => {
      setImportResult(data);
      setImportError(null);
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (err: any) => {
      setImportError(err.response?.data?.error || err.message || 'CSV Import failed');
    },
  });

  const policyMutation = useMutation({
    mutationFn: () => {
      if (!policy?.id) throw new Error('Policy not loaded');
      return updatePolicySettings(policy.id, {
        max_call_attempts_before_unreachable: maxAttempts,
        unreachable_followup_days: unreachableDays,
        nurture_default_days: nurtureDays,
        who_can_mark_lost: whoCanMarkLost,
      });
    },
    onSuccess: () => {
      setPolicySaved(true);
      queryClient.invalidateQueries({ queryKey: ['policy-settings'] });
      setTimeout(() => setPolicySaved(false), 3000);
    },
  });

  const handleCsvUpload = () => {
    if (!csvFile) return;
    setImportResult(null);
    setImportError(null);
    importMutation.mutate(csvFile);
  };

  return (
    <Container size="xl" py="md">
      <Stack gap="lg">
        {/* Header */}
        <Group justify="space-between" align="center">
          <Group gap="xs">
            <ThemeIcon size="lg" radius="md" color="yellow" variant="light">
              <IconSettings size={22} />
            </ThemeIcon>
            <div>
              <Title order={3}>Admin & Operations Hub</Title>
              <Text size="xs" c="dimmed">
                Configure users, interaction outcomes, reasons, CRM policies, and bulk CSV import
              </Text>
            </div>
          </Group>
        </Group>

        <Tabs defaultValue="import" color="yellow">
          <Tabs.List>
            <Tabs.Tab value="import" leftSection={<IconFileSpreadsheet size={16} />}>
              CSV Lead Import
            </Tabs.Tab>
            <Tabs.Tab value="users" leftSection={<IconUsers size={16} />}>
              Users & Roles ({users.length})
            </Tabs.Tab>
            <Tabs.Tab value="outcomes" leftSection={<IconClipboardList size={16} />}>
              Outcomes Matrix ({outcomes.length})
            </Tabs.Tab>
            <Tabs.Tab value="masters" leftSection={<IconAdjustments size={16} />}>
              Masters & Reasons
            </Tabs.Tab>
            <Tabs.Tab value="policy" leftSection={<IconSettings size={16} />}>
              Policy Settings
            </Tabs.Tab>
            <Tabs.Tab value="messaging" leftSection={<IconBrandWhatsapp size={16} />}>
              WhatsApp Templates
            </Tabs.Tab>
          </Tabs.List>

          {/* TAB 1: CSV LEAD IMPORT */}
          <Tabs.Panel value="import" pt="md">
            <Paper p="lg" withBorder radius="md">
              <Stack gap="md">
                <div>
                  <Title order={4}>Bulk Lead Import via CSV</Title>
                  <Text size="xs" c="dimmed">
                    Upload a CSV file containing solar leads. Required header: <Code>name, phone</Code>.
                    Optional headers:{' '}
                    <Code>city, address, monthly_bill, property_type, roof_type, source, email</Code>.
                  </Text>
                </div>

                {importError && (
                  <Alert icon={<IconAlertTriangle size={16} />} title="Upload Error" color="red">
                    {importError}
                  </Alert>
                )}

                {importResult && (
                  <Alert
                    icon={<IconCheck size={16} />}
                    title="Import Finished"
                    color={importResult.error_count > 0 ? 'orange' : 'green'}
                  >
                    <Text size="sm">
                      Successfully imported: <strong>{importResult.created_count}</strong> leads. Errors:{' '}
                      <strong>{importResult.error_count}</strong> rows.
                    </Text>

                    {importResult.errors.length > 0 && (
                      <Box mt="sm">
                        <Text size="xs" fw={600} mb={4}>
                          Row-by-Row Error Report:
                        </Text>
                        <Table striped withTableBorder>
                          <Table.Thead>
                            <Table.Tr>
                              <Table.Th>Row #</Table.Th>
                              <Table.Th>Error Details</Table.Th>
                            </Table.Tr>
                          </Table.Thead>
                          <Table.Tbody>
                            {importResult.errors.map((err, idx) => (
                              <Table.Tr key={idx}>
                                <Table.Td>Row {err.row}</Table.Td>
                                <Table.Td>{err.error}</Table.Td>
                              </Table.Tr>
                            ))}
                          </Table.Tbody>
                        </Table>
                      </Box>
                    )}
                  </Alert>
                )}

                <Group align="flex-end">
                  <FileInput
                    label="Select CSV file"
                    placeholder="Choose leads.csv"
                    accept=".csv"
                    value={csvFile}
                    onChange={setCsvFile}
                    style={{ flex: 1, maxWidth: 400 }}
                  />
                  <Button
                    color="yellow"
                    leftSection={<IconUpload size={16} />}
                    onClick={handleCsvUpload}
                    loading={importMutation.isPending}
                    disabled={!csvFile}
                  >
                    Upload & Process CSV
                  </Button>
                </Group>
              </Stack>
            </Paper>
          </Tabs.Panel>

          {/* TAB 2: USERS & ROLES */}
          <Tabs.Panel value="users" pt="md">
            <Paper withBorder radius="md" style={{ overflow: 'hidden' }}>
              <Table highlightOnHover verticalSpacing="sm">
                <Table.Thead bg="var(--mantine-color-gray-0)">
                  <Table.Tr>
                    <Table.Th>User</Table.Th>
                    <Table.Th>Username</Table.Th>
                    <Table.Th>Role</Table.Th>
                    <Table.Th>Phone</Table.Th>
                    <Table.Th>Status</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {users.map((u) => (
                    <Table.Tr key={u.id}>
                      <Table.Td>
                        <Text size="xs" fw={600}>
                          {u.first_name || u.last_name ? `${u.first_name} ${u.last_name}` : u.username}
                        </Text>
                        <Text size="10px" c="dimmed">
                          {u.email}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">{u.username}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge
                          color={
                            u.role === 'admin'
                              ? 'red'
                              : u.role === 'manager'
                              ? 'blue'
                              : u.role === 'surveyor'
                              ? 'teal'
                              : 'green'
                          }
                          variant="light"
                        >
                          {u.role.toUpperCase()}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">{u.phone || '—'}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge color={u.is_active ? 'green' : 'gray'} size="xs">
                          {u.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Paper>
          </Tabs.Panel>

          {/* TAB 3: OUTCOMES MATRIX */}
          <Tabs.Panel value="outcomes" pt="md">
            <Paper withBorder radius="md" style={{ overflow: 'hidden' }}>
              <Table highlightOnHover verticalSpacing="sm">
                <Table.Thead bg="var(--mantine-color-gray-0)">
                  <Table.Tr>
                    <Table.Th>Stage</Table.Th>
                    <Table.Th>Outcome Name</Table.Th>
                    <Table.Th>Default Status</Table.Th>
                    <Table.Th>Default Next Action</Table.Th>
                    <Table.Th>Follow-up Days</Table.Th>
                    <Table.Th>Flags</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {outcomes.map((o) => (
                    <Table.Tr key={o.id}>
                      <Table.Td>
                        <Badge
                          color={o.stage === 'call' ? 'blue' : o.stage === 'survey' ? 'teal' : 'yellow'}
                          size="xs"
                        >
                          {o.stage.toUpperCase()}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" fw={600}>
                          {o.name}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge color="gray" variant="light" size="xs">
                          {o.default_status}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">{o.default_next_action}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">{o.default_followup_days !== null ? `${o.default_followup_days}d` : 'Manual'}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Group gap={4}>
                          {o.is_terminal && (
                            <Badge color="red" size="xs">
                              Terminal
                            </Badge>
                          )}
                          {o.requires_lost_reason && (
                            <Badge color="orange" size="xs">
                              Lost Reason
                            </Badge>
                          )}
                          {o.requires_nurture_reason && (
                            <Badge color="cyan" size="xs">
                              Nurture Reason
                            </Badge>
                          )}
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Paper>
          </Tabs.Panel>

          {/* TAB 4: MASTERS & REASONS */}
          <Tabs.Panel value="masters" pt="md">
            <SimpleGrid cols={{ base: 1, md: 3 }} spacing="md">
              <Paper p="md" withBorder radius="md">
                <Text fw={600} size="sm" mb="xs">
                  Lost Reasons ({lostReasons.length})
                </Text>
                <Stack gap="xs">
                  {lostReasons.map((r) => (
                    <Paper key={r.id} p="xs" bg="var(--mantine-color-gray-0)" radius="sm">
                      <Text size="xs" fw={500}>
                        {r.name}
                      </Text>
                    </Paper>
                  ))}
                </Stack>
              </Paper>

              <Paper p="md" withBorder radius="md">
                <Text fw={600} size="sm" mb="xs">
                  Nurture Reasons ({nurtureReasons.length})
                </Text>
                <Stack gap="xs">
                  {nurtureReasons.map((r) => (
                    <Paper key={r.id} p="xs" bg="var(--mantine-color-gray-0)" radius="sm">
                      <Text size="xs" fw={500}>
                        {r.name}
                      </Text>
                    </Paper>
                  ))}
                </Stack>
              </Paper>

              <Paper p="md" withBorder radius="md">
                <Text fw={600} size="sm" mb="xs">
                  Lead Sources ({leadSources.length})
                </Text>
                <Stack gap="xs">
                  {leadSources.map((s) => (
                    <Paper key={s.id} p="xs" bg="var(--mantine-color-gray-0)" radius="sm">
                      <Text size="xs" fw={500}>
                        {s.name}
                      </Text>
                    </Paper>
                  ))}
                </Stack>
              </Paper>
            </SimpleGrid>
          </Tabs.Panel>

          {/* TAB 5: POLICY SETTINGS */}
          <Tabs.Panel value="policy" pt="md">
            <Paper p="lg" withBorder radius="md" style={{ maxWidth: 600 }}>
              <Stack gap="md">
                <div>
                  <Title order={4}>CRM Workflow Policies</Title>
                  <Text size="xs" c="dimmed">
                    System defaults controlling the automated retry cadences, nurture intervals, and permissions
                  </Text>
                </div>

                {policySaved && (
                  <Alert icon={<IconCheck size={16} />} title="Saved" color="green">
                    Policy settings have been successfully updated.
                  </Alert>
                )}

                <NumberInput
                  label="Max Call Attempts Before Unreachable"
                  description="Number of unanswered calls after which lead becomes Unreachable"
                  value={maxAttempts}
                  onChange={(val) => setMaxAttempts(Number(val))}
                  min={1}
                  max={20}
                />

                <NumberInput
                  label="Unreachable Follow-up Days"
                  description="Days after which unreachable leads reappear for a final check"
                  value={unreachableDays}
                  onChange={(val) => setUnreachableDays(Number(val))}
                  min={1}
                  max={90}
                />

                <NumberInput
                  label="Nurture Default Follow-up Days"
                  description="Standard incubation period for nurture leads (e.g. 90 days)"
                  value={nurtureDays}
                  onChange={(val) => setNurtureDays(Number(val))}
                  min={7}
                  max={365}
                />

                <Select
                  label="Who Can Mark Lost"
                  description="Minimum user role required to transition a lead to Lost"
                  data={[
                    { value: 'salesperson', label: 'Salesperson (and above)' },
                    { value: 'manager', label: 'Manager (and above)' },
                    { value: 'admin', label: 'Admin only' },
                  ]}
                  value={whoCanMarkLost}
                  onChange={(val) => setWhoCanMarkLost(val || 'manager')}
                />

                <Group justify="flex-end" mt="md">
                  <Button
                    color="yellow"
                    onClick={() => policyMutation.mutate()}
                    loading={policyMutation.isPending}
                  >
                    Save Policies
                  </Button>
                </Group>
              </Stack>
            </Paper>
          </Tabs.Panel>

          {/* TAB 6: WHATSAPP TEMPLATES */}
          <Tabs.Panel value="messaging" pt="md">
            <Paper p="md" withBorder radius="md">
              <Stack gap="md">
                <div>
                  <Title order={4}>WhatsApp Outreach Templates</Title>
                  <Text size="xs" c="dimmed">
                    Pre-approved customer notification templates dispatched via the WhatsApp provider
                  </Text>
                </div>

                <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
                  {templates.map((tpl) => (
                    <Card key={tpl.id} withBorder radius="md" padding="md">
                      <Group justify="space-between" mb="xs">
                        <Text fw={600} size="sm">
                          {tpl.name}
                        </Text>
                        <Badge color="green" size="xs">
                          Active
                        </Badge>
                      </Group>
                      <Paper p="xs" bg="var(--mantine-color-gray-0)" radius="sm">
                        <Text size="xs" style={{ whiteSpace: 'pre-wrap' }}>
                          {tpl.body}
                        </Text>
                      </Paper>
                    </Card>
                  ))}
                </SimpleGrid>
              </Stack>
            </Paper>
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  );
};
