import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Container,
  Title,
  Text,
  Tabs,
  Badge,
  Table,
  Button,
  Group,
  Stack,
  Card,
  Modal,
  Select,
  Textarea,
  TextInput,
  Paper,
  Loader,
  Center,
  ActionIcon,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconCheck,
  IconX,
  IconUserCheck,
  IconArrowRight,
  IconRefresh,
} from '@tabler/icons-react';
import {
  fetchUnassignedLeads,
  fetchLostApprovals,
  approveLostLead,
  rejectLostLead,
  assignLead,
  autoDistributeLeads,
  fetchSurveys,
  assignSurveyor,
  fetchUsers,
  fetchLeads,
} from '../api/client';
import { useTranslation } from 'react-i18next';
import { translateStatus } from '../i18n/formatters';
import type { Lead, Survey, User } from '../api/types';

export const ManagerAttentionPage: React.FC = () => {
  const { t, i18n } = useTranslation(['common', 'leads', 'surveys']);
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<string | null>('unassigned');

  // Modals state
  const [assignModalLead, setAssignModalLead] = useState<Lead | null>(null);
  const [selectedSalespersonId, setSelectedSalespersonId] = useState<string>('');

  const [rejectModalLead, setRejectModalLead] = useState<Lead | null>(null);
  const [rejectReason, setRejectReason] = useState<string>('');
  const [rejectFollowupAt, setRejectFollowupAt] = useState<string>('');

  const [assignSurveyModal, setAssignSurveyModal] = useState<Survey | null>(null);
  const [selectedSurveyorId, setSelectedSurveyorId] = useState<string>('');

  // 1. Fetch unassigned leads
  const { data: unassignedData, isLoading: unassignedLoading, refetch: refetchUnassigned } = useQuery({
    queryKey: ['leads-unassigned'],
    queryFn: fetchUnassignedLeads,
  });

  // 2. Fetch lost approvals
  const { data: lostApprovalsData, isLoading: lostLoading, refetch: refetchLost } = useQuery({
    queryKey: ['leads-lost-approvals'],
    queryFn: fetchLostApprovals,
  });

  // 3. Fetch surveys without surveyor
  const { data: surveysData, isLoading: surveysLoading, refetch: refetchSurveys } = useQuery({
    queryKey: ['surveys-unassigned'],
    queryFn: () => fetchSurveys({ status: 'booked' }),
  });

  // 4. Fetch overdue follow-ups
  const { data: overdueData, isLoading: overdueLoading } = useQuery({
    queryKey: ['leads-overdue-manager'],
    queryFn: () => fetchLeads({ tab: 'overdue' }),
  });

  // Fetch users for dropdowns
  const { data: usersData } = useQuery({
    queryKey: ['users-team'],
    queryFn: () => fetchUsers({ is_active: true }),
  });

  const unassignedList: Lead[] = Array.isArray(unassignedData)
    ? unassignedData
    : (unassignedData as any)?.results || [];

  const lostList: Lead[] = Array.isArray(lostApprovalsData)
    ? lostApprovalsData
    : (lostApprovalsData as any)?.results || [];

  const allSurveys: Survey[] = Array.isArray(surveysData)
    ? surveysData
    : (surveysData as any)?.results || [];

  const unassignedSurveys = allSurveys.filter((s) => !s.surveyor);

  const overdueList: Lead[] = Array.isArray(overdueData)
    ? overdueData
    : (overdueData as any)?.results || [];

  const allUsers: User[] = Array.isArray(usersData)
    ? usersData
    : (usersData as any)?.results || [];

  const salespeople = allUsers.filter((u) => u.role === 'salesperson' || u.role === 'manager');
  const surveyors = allUsers.filter((u) => u.role === 'surveyor');

  // Mutations
  const assignMutation = useMutation({
    mutationFn: ({ leadId, userId }: { leadId: number; userId: number }) =>
      assignLead(leadId, userId),
    onSuccess: () => {
      notifications.show({ title: 'Success', message: 'Lead assigned successfully.', color: 'green' });
      setAssignModalLead(null);
      queryClient.invalidateQueries({ queryKey: ['leads-unassigned'] });
    },
  });

  const autoDistributeMutation = useMutation({
    mutationFn: () => autoDistributeLeads(),
    onSuccess: (data) => {
      notifications.show({ title: 'Success', message: data.message, color: 'green' });
      queryClient.invalidateQueries({ queryKey: ['leads-unassigned'] });
    },
  });

  const approveLostMutation = useMutation({
    mutationFn: (leadId: number) => approveLostLead(leadId),
    onSuccess: () => {
      notifications.show({ title: 'Approved', message: 'Lead closed as Lost.', color: 'green' });
      queryClient.invalidateQueries({ queryKey: ['leads-lost-approvals'] });
    },
  });

  const rejectLostMutation = useMutation({
    mutationFn: ({ leadId, reason, next_followup_at }: { leadId: number; reason: string; next_followup_at: string }) =>
      rejectLostLead(leadId, { reason, next_followup_at }),
    onSuccess: () => {
      notifications.show({ title: 'Rejected', message: 'Lead returned to active queue.', color: 'blue' });
      setRejectModalLead(null);
      setRejectReason('');
      setRejectFollowupAt('');
      queryClient.invalidateQueries({ queryKey: ['leads-lost-approvals'] });
    },
  });

  const assignSurveyorMutation = useMutation({
    mutationFn: ({ surveyId, surveyorId }: { surveyId: number; surveyorId: number }) =>
      assignSurveyor(surveyId, surveyorId),
    onSuccess: () => {
      notifications.show({ title: 'Assigned', message: 'Surveyor assigned successfully.', color: 'green' });
      setAssignSurveyModal(null);
      queryClient.invalidateQueries({ queryKey: ['surveys-unassigned'] });
    },
  });

  return (
    <Container size="xl" py="md">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>{t('common:nav.manager_attention', 'Manager Attention Queue')}</Title>
          <Text size="sm" c="dimmed">
            Centralized hub for unassigned leads, pending Lost approvals, and staffing bottlenecks.
          </Text>
        </div>
        <ActionIcon
          variant="light"
          size="lg"
          onClick={() => {
            refetchUnassigned();
            refetchLost();
            refetchSurveys();
          }}
        >
          <IconRefresh size={18} />
        </ActionIcon>
      </Group>

      <Tabs value={activeTab} onChange={setActiveTab} variant="outline" radius="md">
        <Tabs.List mb="md">
          <Tabs.Tab
            value="unassigned"
            rightSection={<Badge size="xs" color="yellow">{unassignedList.length}</Badge>}
          >
            {t('leads:filters.no_followup', 'Unassigned Leads')}
          </Tabs.Tab>
          <Tabs.Tab
            value="lost-approvals"
            rightSection={<Badge size="xs" color="red">{lostList.length}</Badge>}
          >
            {translateStatus('Lost approval pending', i18n.language)}
          </Tabs.Tab>
          <Tabs.Tab
            value="unassigned-surveys"
            rightSection={<Badge size="xs" color="blue">{unassignedSurveys.length}</Badge>}
          >
            {t('surveys:title', 'Surveys Without Surveyor')}
          </Tabs.Tab>
          <Tabs.Tab
            value="overdue"
            rightSection={<Badge size="xs" color="orange">{overdueList.length}</Badge>}
          >
            {t('leads:filters.overdue', 'Overdue Follow-ups')}
          </Tabs.Tab>
        </Tabs.List>

        {/* Tab 1: Unassigned Leads */}
        <Tabs.Panel value="unassigned">
          <Paper withBorder p="md" radius="md">
            <Group justify="space-between" mb="md">
              <Text fw={600}>{unassignedList.length} leads awaiting salesperson assignment</Text>
              <Button
                size="xs"
                variant="light"
                color="yellow"
                onClick={() => autoDistributeMutation.mutate()}
                loading={autoDistributeMutation.isPending}
                disabled={unassignedList.length === 0}
              >
                Auto-Distribute All (Round-Robin)
              </Button>
            </Group>

            {unassignedLoading ? (
              <Center py="xl"><Loader /></Center>
            ) : unassignedList.length === 0 ? (
              <Text c="dimmed" ta="center" py="xl">No unassigned leads in your region.</Text>
            ) : (
              <Table.ScrollContainer minWidth={600}>
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Customer</Table.Th>
                      <Table.Th>Phone</Table.Th>
                      <Table.Th>City</Table.Th>
                      <Table.Th>Source</Table.Th>
                      <Table.Th>Created</Table.Th>
                      <Table.Th>Action</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {unassignedList.map((lead) => (
                      <Table.Tr key={lead.id}>
                        <Table.Td fw={500}>{lead.name}</Table.Td>
                        <Table.Td>{lead.phone_display || lead.phone}</Table.Td>
                        <Table.Td>{lead.city || '-'}</Table.Td>
                        <Table.Td><Badge size="xs" variant="light">{lead.source_name || 'Direct'}</Badge></Table.Td>
                        <Table.Td>{new Date(lead.created_at).toLocaleDateString()}</Table.Td>
                        <Table.Td>
                          <Button
                            size="xs"
                            variant="light"
                            leftSection={<IconUserCheck size={14} />}
                            onClick={() => {
                              setAssignModalLead(lead);
                              setSelectedSalespersonId('');
                            }}
                          >
                            Assign
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )}
          </Paper>
        </Tabs.Panel>

        {/* Tab 2: Lost Approvals */}
        <Tabs.Panel value="lost-approvals">
          <Paper withBorder p="md" radius="md">
            <Text fw={600} mb="md">{lostList.length} leads requested for Lost closure</Text>
            {lostLoading ? (
              <Center py="xl"><Loader /></Center>
            ) : lostList.length === 0 ? (
              <Text c="dimmed" ta="center" py="xl">No leads currently pending Lost approval.</Text>
            ) : (
              <Stack gap="md">
                {lostList.map((lead) => (
                  <Card key={lead.id} withBorder radius="md" p="md">
                    <Group justify="space-between" mb="xs">
                      <div>
                        <Text fw={600} size="md">{lead.name}</Text>
                        <Text size="xs" c="dimmed">
                          Salesperson: {lead.assigned_to_name || 'Unassigned'} • Phone: {lead.phone_display || lead.phone}
                        </Text>
                      </div>
                      <Badge color="red" variant="light">
                        Reason: {lead.lost_pending_reason_name || 'Price / Competitor'}
                      </Badge>
                    </Group>
                    {lead.lost_pending_notes && (
                      <Paper p="xs" withBorder bg="var(--mantine-color-gray-0)" mb="md">
                        <Text size="xs" fs="italic">"{lead.lost_pending_notes}"</Text>
                      </Paper>
                    )}
                    <Group justify="flex-end" gap="xs">
                      <Button
                        size="xs"
                        variant="subtle"
                        color="gray"
                        onClick={() => window.open(`/leads/${lead.id}`, '_blank')}
                      >
                        Inspect Lead
                      </Button>
                      <Button
                        size="xs"
                        color="red"
                        variant="light"
                        leftSection={<IconCheck size={14} />}
                        onClick={() => approveLostMutation.mutate(lead.id)}
                        loading={approveLostMutation.isPending}
                      >
                        Approve (Mark Lost)
                      </Button>
                      <Button
                        size="xs"
                        color="gray"
                        variant="light"
                        leftSection={<IconX size={14} />}
                        onClick={() => {
                          setRejectModalLead(lead);
                          setRejectReason('');
                          setRejectFollowupAt(new Date(Date.now() + 86400000).toISOString().slice(0, 16));
                        }}
                      >
                        Reject & Revert
                      </Button>
                    </Group>
                  </Card>
                ))}
              </Stack>
            )}
          </Paper>
        </Tabs.Panel>

        {/* Tab 3: Surveys Without Surveyor */}
        <Tabs.Panel value="unassigned-surveys">
          <Paper withBorder p="md" radius="md">
            <Text fw={600} mb="md">{unassignedSurveys.length} booked surveys without an assigned surveyor</Text>
            {surveysLoading ? (
              <Center py="xl"><Loader /></Center>
            ) : unassignedSurveys.length === 0 ? (
              <Text c="dimmed" ta="center" py="xl">All site surveys are properly staffed!</Text>
            ) : (
              <Table.ScrollContainer minWidth={600}>
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Customer</Table.Th>
                      <Table.Th>Scheduled Time</Table.Th>
                      <Table.Th>Address / City</Table.Th>
                      <Table.Th>Action</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {unassignedSurveys.map((survey) => (
                      <Table.Tr key={survey.id}>
                        <Table.Td fw={500}>{survey.lead_name}</Table.Td>
                        <Table.Td>{new Date(survey.scheduled_at).toLocaleString()}</Table.Td>
                        <Table.Td>{(survey as any).lead_city || '-'}</Table.Td>
                        <Table.Td>
                          <Button
                            size="xs"
                            variant="light"
                            color="blue"
                            onClick={() => {
                              setAssignSurveyModal(survey);
                              setSelectedSurveyorId('');
                            }}
                          >
                            Assign Surveyor
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )}
          </Paper>
        </Tabs.Panel>

        {/* Tab 4: Overdue Follow-ups */}
        <Tabs.Panel value="overdue">
          <Paper withBorder p="md" radius="md">
            <Text fw={600} mb="md">{overdueList.length} leads with overdue follow-ups across team</Text>
            {overdueLoading ? (
              <Center py="xl"><Loader /></Center>
            ) : overdueList.length === 0 ? (
              <Text c="dimmed" ta="center" py="xl">No overdue follow-ups! Great job team.</Text>
            ) : (
              <Table.ScrollContainer minWidth={600}>
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Customer</Table.Th>
                      <Table.Th>Assigned Salesperson</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Scheduled Follow-up</Table.Th>
                      <Table.Th>Action</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {overdueList.slice(0, 50).map((lead) => (
                      <Table.Tr key={lead.id}>
                        <Table.Td fw={500}>{lead.name}</Table.Td>
                        <Table.Td>{lead.assigned_to_name || 'Unassigned'}</Table.Td>
                        <Table.Td><Badge size="xs" variant="light">{lead.status}</Badge></Table.Td>
                        <Table.Td c="red" fw={500}>
                          {lead.next_followup_at ? new Date(lead.next_followup_at).toLocaleString() : 'Past due'}
                        </Table.Td>
                        <Table.Td>
                          <Button
                            size="xs"
                            variant="subtle"
                            rightSection={<IconArrowRight size={14} />}
                            onClick={() => window.open(`/leads/${lead.id}`, '_blank')}
                          >
                            Open
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )}
          </Paper>
        </Tabs.Panel>
      </Tabs>

      {/* Modal: Assign Single Lead */}
      <Modal
        opened={Boolean(assignModalLead)}
        onClose={() => setAssignModalLead(null)}
        title="Assign Lead to Salesperson"
        radius="md"
      >
        <Stack gap="md">
          <Text size="sm">Assign <b>{assignModalLead?.name}</b> to:</Text>
          <Select
            label="Select Salesperson"
            placeholder="Choose sales rep..."
            data={salespeople.map((u) => ({
              value: String(u.id),
              label: `${u.first_name ? `${u.first_name} ${u.last_name}` : u.username} (${u.role})`,
            }))}
            value={selectedSalespersonId}
            onChange={(val) => setSelectedSalespersonId(val || '')}
          />
          <Group justify="flex-end">
            <Button variant="light" color="gray" onClick={() => setAssignModalLead(null)}>Cancel</Button>
            <Button
              color="yellow"
              disabled={!selectedSalespersonId}
              loading={assignMutation.isPending}
              onClick={() => {
                if (assignModalLead && selectedSalespersonId) {
                  assignMutation.mutate({
                    leadId: assignModalLead.id,
                    userId: Number(selectedSalespersonId),
                  });
                }
              }}
            >
              Confirm Assignment
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Reject Lost Request */}
      <Modal
        opened={Boolean(rejectModalLead)}
        onClose={() => setRejectModalLead(null)}
        title="Reject Lost Request & Revert Lead"
        radius="md"
      >
        <Stack gap="md">
          <Text size="sm">
            Reverting <b>{rejectModalLead?.name}</b> back to active sales pipeline.
          </Text>
          <Textarea
            label="Reason for Rejecting Lost Closure"
            placeholder="e.g. Subsidy scheme updated, give them another call..."
            required
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
          />
          <TextInput
            label="Next Follow-up Date & Time"
            type="datetime-local"
            required
            value={rejectFollowupAt}
            onChange={(e) => setRejectFollowupAt(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="light" color="gray" onClick={() => setRejectModalLead(null)}>Cancel</Button>
            <Button
              color="blue"
              disabled={!rejectReason.trim() || !rejectFollowupAt}
              loading={rejectLostMutation.isPending}
              onClick={() => {
                if (rejectModalLead) {
                  rejectLostMutation.mutate({
                    leadId: rejectModalLead.id,
                    reason: rejectReason,
                    next_followup_at: rejectFollowupAt,
                  });
                }
              }}
            >
              Revert Lead
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Assign Surveyor */}
      <Modal
        opened={Boolean(assignSurveyModal)}
        onClose={() => setAssignSurveyModal(null)}
        title="Staff Site Survey"
        radius="md"
      >
        <Stack gap="md">
          <Text size="sm">
            Assign Site Surveyor for <b>{assignSurveyModal?.lead_name}</b> on{' '}
            {assignSurveyModal?.scheduled_at ? new Date(assignSurveyModal.scheduled_at).toLocaleString() : ''}:
          </Text>
          <Select
            label="Select Field Surveyor"
            placeholder="Choose surveyor..."
            data={surveyors.map((u) => ({
              value: String(u.id),
              label: `${u.first_name ? `${u.first_name} ${u.last_name}` : u.username} (${u.phone || 'No phone'})`,
            }))}
            value={selectedSurveyorId}
            onChange={(val) => setSelectedSurveyorId(val || '')}
          />
          <Group justify="flex-end">
            <Button variant="light" color="gray" onClick={() => setAssignSurveyModal(null)}>Cancel</Button>
            <Button
              color="blue"
              disabled={!selectedSurveyorId}
              loading={assignSurveyorMutation.isPending}
              onClick={() => {
                if (assignSurveyModal && selectedSurveyorId) {
                  assignSurveyorMutation.mutate({
                    surveyId: assignSurveyModal.id,
                    surveyorId: Number(selectedSurveyorId),
                  });
                }
              }}
            >
              Assign Surveyor
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
};
