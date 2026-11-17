import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Container,
  Title,
  Text,
  Group,
  Stack,
  Button,
  TextInput,
  Select,
  Table,
  Badge,
  Card,
  Pagination,
  Box,
  ActionIcon,
  Loader,
  Center,
  Paper,
  Divider,
} from '@mantine/core';
import {
  IconSearch,
  IconPlus,
  IconEye,
  IconClipboardCheck,
} from '@tabler/icons-react';
import { fetchLeads, fetchLeadSources, fetchUsers } from '../api/client';
import { NewLeadModal } from '../components/modals/NewLeadModal';
import { LogOutcomeModal } from '../components/modals/LogOutcomeModal';
import type { Lead, LeadSource, User } from '../api/types';

export const LeadsListPage: React.FC = () => {
  const navigate = useNavigate();

  // Search & Filter state
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [sourceFilter, setSourceFilter] = useState<string | null>(null);
  const [assigneeFilter, setAssigneeFilter] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Modals state
  const [newLeadModalOpen, setNewLeadModalOpen] = useState(false);
  const [outcomeModalOpen, setOutcomeModalOpen] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  // Queries
  const { data: sources = [] } = useQuery<LeadSource[]>({
    queryKey: ['lead-sources'],
    queryFn: fetchLeadSources,
  });

  const { data: users = [] } = useQuery<User[]>({
    queryKey: ['users'],
    queryFn: fetchUsers,
  });

  const { data: leadsData, isLoading, refetch } = useQuery<{ results: Lead[]; count: number }>({
    queryKey: ['leads', { search, status: statusFilter, source: sourceFilter, assigned_to: assigneeFilter, page }],
    queryFn: () => {
      const params: Record<string, any> = {
        page,
        page_size: pageSize,
      };
      if (search.trim()) params.search = search.trim();
      if (statusFilter) params.status = statusFilter;
      if (sourceFilter) params.source = sourceFilter;
      if (assigneeFilter) params.assigned_to = assigneeFilter;
      return fetchLeads(params);
    },
  });

  const leads = leadsData?.results || [];
  const totalCount = leadsData?.count || 0;
  const totalPages = Math.ceil(totalCount / pageSize);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Won':
        return 'green';
      case 'Lost':
      case 'Invalid contact':
      case 'Do not contact':
        return 'red';
      case 'Interested':
      case 'Quote sent':
      case 'Negotiation':
        return 'yellow';
      case 'Survey scheduled':
      case 'Survey to schedule':
      case 'Design pending':
        return 'teal';
      case 'New':
      case 'Attempting contact':
      case 'Callback scheduled':
        return 'blue';
      default:
        return 'gray';
    }
  };

  const handleOpenOutcome = (lead: Lead) => {
    setSelectedLead(lead);
    setOutcomeModalOpen(true);
  };

  return (
    <Container size="xl" py="md">
      <Stack gap="md">
        {/* Header */}
        <Group justify="space-between" align="center">
          <div>
            <Title order={3}>All Leads ({totalCount})</Title>
            <Text size="xs" c="dimmed">
              Manage prospective solar clients, filter by stage, and log follow-ups
            </Text>
          </div>
          <Button
            color="yellow"
            leftSection={<IconPlus size={16} />}
            onClick={() => setNewLeadModalOpen(true)}
          >
            New Lead
          </Button>
        </Group>

        {/* Filters Bar */}
        <Paper p="sm" withBorder radius="md">
          <Group gap="sm" wrap="wrap">
            <TextInput
              placeholder="Search by name, phone or city..."
              leftSection={<IconSearch size={16} />}
              value={search}
              onChange={(e) => {
                setSearch(e.currentTarget.value);
                setPage(1);
              }}
              style={{ flex: 1, minWidth: 200 }}
            />

            <Select
              placeholder="Filter by Status"
              clearable
              data={[
                { value: 'New', label: 'New' },
                { value: 'Attempting contact', label: 'Attempting contact' },
                { value: 'Callback scheduled', label: 'Callback scheduled' },
                { value: 'Interested', label: 'Interested' },
                { value: 'Survey to schedule', label: 'Survey to schedule' },
                { value: 'Survey scheduled', label: 'Survey scheduled' },
                { value: 'Design pending', label: 'Design pending' },
                { value: 'Quote sent', label: 'Quote sent' },
                { value: 'Revising quote', label: 'Revising quote' },
                { value: 'Negotiation', label: 'Negotiation' },
                { value: 'Won', label: 'Won' },
                { value: 'Lost', label: 'Lost' },
                { value: 'Nurture', label: 'Nurture' },
                { value: 'Unreachable', label: 'Unreachable' },
                { value: 'Do not contact', label: 'Do not contact' },
                { value: 'Merged', label: 'Merged' },
              ]}
              value={statusFilter}
              onChange={(val) => {
                setStatusFilter(val);
                setPage(1);
              }}
              style={{ minWidth: 170 }}
            />

            <Select
              placeholder="Filter by Source"
              clearable
              data={sources.map((s) => ({ value: String(s.id), label: s.name }))}
              value={sourceFilter}
              onChange={(val) => {
                setSourceFilter(val);
                setPage(1);
              }}
              style={{ minWidth: 150 }}
            />

            <Select
              placeholder="Filter by Assignee"
              clearable
              data={users.map((u) => ({
                value: String(u.id),
                label: `${u.first_name || u.username} (${u.role})`,
              }))}
              value={assigneeFilter}
              onChange={(val) => {
                setAssigneeFilter(val);
                setPage(1);
              }}
              style={{ minWidth: 160 }}
            />
          </Group>
        </Paper>

        {/* Content Table / Cards */}
        {isLoading ? (
          <Center py="xl">
            <Loader color="yellow" />
          </Center>
        ) : leads.length === 0 ? (
          <Paper p="xl" withBorder radius="md" ta="center">
            <Text size="sm" c="dimmed">
              No leads match your search criteria.
            </Text>
          </Paper>
        ) : (
          <>
            {/* Desktop Table View */}
            <Box visibleFrom="sm">
              <Paper withBorder radius="md" style={{ overflow: 'hidden' }}>
                <Table highlightOnHover verticalSpacing="sm">
                  <Table.Thead bg="var(--mantine-color-gray-0)">
                    <Table.Tr>
                      <Table.Th>Name & ID</Table.Th>
                      <Table.Th>Phone / City</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Next Action</Table.Th>
                      <Table.Th>Next Follow-up</Table.Th>
                      <Table.Th>Assigned To</Table.Th>
                      <Table.Th ta="right">Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {leads.map((lead) => (
                      <Table.Tr key={lead.id}>
                        <Table.Td>
                          <Group gap="xs">
                            <Text
                              fw={600}
                              size="sm"
                              style={{ cursor: 'pointer' }}
                              c="yellow.9"
                              onClick={() => navigate(`/leads/${lead.id}`)}
                            >
                              {lead.name}
                            </Text>
                            <Badge size="xs" variant="outline" color="gray">
                              #{lead.id}
                            </Badge>
                          </Group>
                          <Text size="10px" c="dimmed">
                            {lead.property_type || 'Residential'} • {lead.roof_type || 'RCC'}
                          </Text>
                        </Table.Td>

                        <Table.Td>
                          <Text size="xs" fw={500}>
                            {lead.phone}
                          </Text>
                          <Text size="10px" c="dimmed">
                            {lead.city}
                          </Text>
                        </Table.Td>

                        <Table.Td>
                          <Badge color={getStatusColor(lead.status)} variant="light">
                            {lead.status}
                          </Badge>
                        </Table.Td>

                        <Table.Td>
                          <Text size="xs" lineClamp={1}>
                            {lead.next_action || '—'}
                          </Text>
                        </Table.Td>

                        <Table.Td>
                          {lead.next_followup_at ? (
                            <Text size="xs">
                              {new Date(lead.next_followup_at).toLocaleString([], {
                                dateStyle: 'short',
                                timeStyle: 'short',
                              })}
                            </Text>
                          ) : (
                            <Text size="xs" c="dimmed">
                              —
                            </Text>
                          )}
                        </Table.Td>

                        <Table.Td>
                          <Text size="xs">{lead.assigned_to_name || 'Unassigned'}</Text>
                        </Table.Td>

                        <Table.Td ta="right">
                          <Group gap="xs" justify="flex-end">
                            <Button
                              size="xs"
                              variant="light"
                              color="yellow"
                              leftSection={<IconClipboardCheck size={14} />}
                              onClick={() => handleOpenOutcome(lead)}
                            >
                              Log
                            </Button>
                            <ActionIcon
                              variant="subtle"
                              color="gray"
                              onClick={() => navigate(`/leads/${lead.id}`)}
                              title="View lead"
                            >
                              <IconEye size={16} />
                            </ActionIcon>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Paper>
            </Box>

            {/* Mobile Card Stack */}
            <Stack hiddenFrom="sm" gap="sm">
              {leads.map((lead) => (
                <Card key={lead.id} shadow="xs" padding="sm" radius="md" withBorder>
                  <Stack gap="xs">
                    <Group justify="space-between" align="flex-start">
                      <div>
                        <Text
                          fw={600}
                          size="sm"
                          style={{ cursor: 'pointer' }}
                          onClick={() => navigate(`/leads/${lead.id}`)}
                        >
                          {lead.name}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {lead.phone} • {lead.city}
                        </Text>
                      </div>
                      <Badge color={getStatusColor(lead.status)} variant="light" size="sm">
                        {lead.status}
                      </Badge>
                    </Group>

                    {lead.next_action && (
                      <Text size="xs">
                        <strong>Action:</strong> {lead.next_action}
                      </Text>
                    )}

                    {lead.next_followup_at && (
                      <Text size="xs" c="dimmed">
                        <strong>Follow-up:</strong>{' '}
                        {new Date(lead.next_followup_at).toLocaleString([], {
                          dateStyle: 'short',
                          timeStyle: 'short',
                        })}
                      </Text>
                    )}

                    <Divider />

                    <Group justify="space-between">
                      <Button
                        size="xs"
                        variant="light"
                        color="yellow"
                        leftSection={<IconClipboardCheck size={14} />}
                        onClick={() => handleOpenOutcome(lead)}
                      >
                        Log Outcome
                      </Button>
                      <Button
                        size="xs"
                        variant="subtle"
                        rightSection={<IconEye size={14} />}
                        onClick={() => navigate(`/leads/${lead.id}`)}
                      >
                        Details
                      </Button>
                    </Group>
                  </Stack>
                </Card>
              ))}
            </Stack>

            {/* Pagination */}
            {totalPages > 1 && (
              <Group justify="center" mt="md">
                <Pagination value={page} onChange={setPage} total={totalPages} color="yellow" />
              </Group>
            )}
          </>
        )}
      </Stack>

      {/* Modals */}
      <NewLeadModal
        opened={newLeadModalOpen}
        onClose={() => setNewLeadModalOpen(false)}
        onLeadCreated={(id: number) => {
          refetch();
          navigate(`/leads/${id}`);
        }}
      />

      <LogOutcomeModal
        opened={outcomeModalOpen}
        onClose={() => setOutcomeModalOpen(false)}
        lead={selectedLead}
        onSuccess={() => refetch()}
      />
    </Container>
  );
};
