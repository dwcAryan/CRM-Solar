import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
  Tabs,
  Checkbox,
} from '@mantine/core';
import {
  IconSearch,
  IconPlus,
  IconEye,
  IconClipboardCheck,
  IconPhone,
  IconBrandWhatsapp,
  IconNotes,
  IconDownload,
  IconAlertTriangle,
  IconClock,
} from '@tabler/icons-react';
import {
  fetchLeads,
  fetchLeadSources,
  fetchUsers,
  bulkActionLeads,
  exportLeadsCsv,
} from '../api/client';
import { NewLeadModal } from '../components/modals/NewLeadModal';
import { LogOutcomeModal } from '../components/modals/LogOutcomeModal';
import { AddRemarkModal } from '../components/modals/AddRemarkModal';
import type { Lead, LeadSource, User } from '../api/types';

export const LeadsListPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

  // Search & Filter state
  const initialSearch = searchParams.get('search') || '';
  const initialTab = searchParams.get('tab') || 'all';

  const [search, setSearch] = useState(initialSearch);
  const [activeTab, setActiveTab] = useState<string>(initialTab);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [sourceFilter, setSourceFilter] = useState<string | null>(null);
  const [assigneeFilter, setAssigneeFilter] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Bulk actions state
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [bulkAssignee, setBulkAssignee] = useState<string | null>(null);
  const [bulkSource, setBulkSource] = useState<string | null>(null);

  // Modals state
  const [newLeadModalOpen, setNewLeadModalOpen] = useState(false);
  const [outcomeModalOpen, setOutcomeModalOpen] = useState(false);
  const [remarkModalOpen, setRemarkModalOpen] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  // Sync search param when updated from global search
  React.useEffect(() => {
    const s = searchParams.get('search');
    if (s !== null && s !== search) {
      setSearch(s);
      setPage(1);
    }
  }, [searchParams]);

  // Queries
  const { data: sources = [] } = useQuery<LeadSource[]>({
    queryKey: ['lead-sources'],
    queryFn: fetchLeadSources,
  });

  const { data: users = [] } = useQuery<User[]>({
    queryKey: ['users'],
    queryFn: fetchUsers,
  });

  const queryParams: Record<string, any> = {
    page,
    page_size: pageSize,
  };
  if (search.trim()) queryParams.search = search.trim();
  if (activeTab !== 'all') queryParams.tab = activeTab;
  if (statusFilter) queryParams.status = statusFilter;
  if (sourceFilter) queryParams.source = sourceFilter;
  if (assigneeFilter) queryParams.assigned_to = assigneeFilter;

  const { data: leadsData, isLoading, refetch } = useQuery<{ results: Lead[]; count: number }>({
    queryKey: ['leads', queryParams],
    queryFn: () => fetchLeads(queryParams),
  });

  const leads = leadsData?.results || [];
  const totalCount = leadsData?.count || 0;
  const totalPages = Math.ceil(totalCount / pageSize);

  // Bulk action mutations
  const bulkMutation = useMutation({
    mutationFn: (payload: { action: 'assign' | 'change_source'; value: number }) => {
      return bulkActionLeads({
        lead_ids: selectedIds,
        action: payload.action,
        value: payload.value,
      });
    },
    onSuccess: () => {
      setSelectedIds([]);
      setBulkAssignee(null);
      setBulkSource(null);
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      refetch();
    },
  });

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(leads.map((l) => l.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectOne = (id: number, checked: boolean) => {
    if (checked) {
      setSelectedIds((prev) => [...prev, id]);
    } else {
      setSelectedIds((prev) => prev.filter((i) => i !== id));
    }
  };

  const handleExportFiltered = () => {
    const exportParams: Record<string, any> = {};
    if (search.trim()) exportParams.search = search.trim();
    if (activeTab !== 'all') exportParams.tab = activeTab;
    if (statusFilter) exportParams.status = statusFilter;
    if (sourceFilter) exportParams.source = sourceFilter;
    if (assigneeFilter) exportParams.assigned_to = assigneeFilter;
    exportLeadsCsv(exportParams);
  };

  const handleExportSelected = () => {
    if (selectedIds.length === 0) return;
    exportLeadsCsv({ lead_ids: selectedIds.join(',') });
  };

  const now = new Date();

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
      case 'Nurture':
        return 'orange';
      case 'Unreachable':
        return 'violet';
      default:
        return 'gray';
    }
  };

  const isTerminal = (status: string) => {
    return ['Won', 'Lost', 'Do not contact', 'Merged', 'Invalid contact'].includes(status);
  };

  const isOverdue = (lead: Lead) => {
    if (isTerminal(lead.status) || !lead.next_followup_at) return false;
    return new Date(lead.next_followup_at) < now;
  };

  const isNoFollowup = (lead: Lead) => {
    return !isTerminal(lead.status) && !lead.next_followup_at;
  };

  const cleanPhone = (phone: string) => phone.replace(/\D/g, '').slice(-10);

  return (
    <Container size="xl" py="md">
      <Stack gap="md">
        {/* Header */}
        <Group justify="space-between" align="center">
          <div>
            <Title order={3}>All Leads ({totalCount})</Title>
            <Text size="xs" c="dimmed">
              Filter by saved views, perform bulk team updates, and log interaction outcomes
            </Text>
          </div>
          <Group gap="xs">
            <Button
              variant="light"
              color="gray"
              size="xs"
              leftSection={<IconDownload size={14} />}
              onClick={handleExportFiltered}
            >
              Export to CSV
            </Button>
            <Button
              color="yellow"
              size="xs"
              leftSection={<IconPlus size={16} />}
              onClick={() => setNewLeadModalOpen(true)}
            >
              New Lead
            </Button>
          </Group>
        </Group>

        {/* Saved Filter Tabs */}
        <Tabs
          value={activeTab}
          onChange={(val) => {
            setActiveTab(val || 'all');
            setPage(1);
            setSearchParams((prev) => {
              const next = new URLSearchParams(prev);
              if (val && val !== 'all') {
                next.set('tab', val);
              } else {
                next.delete('tab');
              }
              return next;
            });
          }}
          color="yellow"
        >
          <Tabs.List>
            <Tabs.Tab value="all">All Leads</Tabs.Tab>
            <Tabs.Tab value="my">My Leads</Tabs.Tab>
            <Tabs.Tab value="due_today" leftSection={<IconClock size={14} />}>
              Due Today
            </Tabs.Tab>
            <Tabs.Tab
              value="overdue"
              leftSection={<IconAlertTriangle size={14} color="red" />}
            >
              Overdue
            </Tabs.Tab>
            <Tabs.Tab value="no_followup">
              No Follow-up Date
            </Tabs.Tab>
            <Tabs.Tab value="interested">Interested</Tabs.Tab>
            <Tabs.Tab value="quote_sent">Quote Sent</Tabs.Tab>
          </Tabs.List>
        </Tabs>

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

        {/* Bulk Actions Floating Bar */}
        {selectedIds.length > 0 && (
          <Paper p="xs" withBorder bg="var(--mantine-color-yellow-0)" radius="md">
            <Group justify="space-between" wrap="wrap">
              <Group gap="sm">
                <Badge color="yellow" size="lg">
                  {selectedIds.length} leads selected
                </Badge>
                <Button size="xs" variant="subtle" color="gray" onClick={() => setSelectedIds([])}>
                  Clear Selection
                </Button>
              </Group>

              <Group gap="xs" wrap="wrap">
                {/* Bulk Assign */}
                <Group gap={4}>
                  <Select
                    placeholder="Assign to..."
                    size="xs"
                    data={users.map((u) => ({
                      value: String(u.id),
                      label: `${u.first_name || u.username}`,
                    }))}
                    value={bulkAssignee}
                    onChange={setBulkAssignee}
                    style={{ width: 140 }}
                  />
                  <Button
                    size="xs"
                    color="yellow"
                    disabled={!bulkAssignee}
                    onClick={() => bulkMutation.mutate({ action: 'assign', value: Number(bulkAssignee) })}
                    loading={bulkMutation.isPending}
                  >
                    Assign
                  </Button>
                </Group>

                {/* Bulk Change Source */}
                <Group gap={4}>
                  <Select
                    placeholder="Change source..."
                    size="xs"
                    data={sources.map((s) => ({ value: String(s.id), label: s.name }))}
                    value={bulkSource}
                    onChange={setBulkSource}
                    style={{ width: 150 }}
                  />
                  <Button
                    size="xs"
                    color="yellow"
                    disabled={!bulkSource}
                    onClick={() => bulkMutation.mutate({ action: 'change_source', value: Number(bulkSource) })}
                    loading={bulkMutation.isPending}
                  >
                    Set Source
                  </Button>
                </Group>

                <Button
                  size="xs"
                  variant="light"
                  color="blue"
                  leftSection={<IconDownload size={14} />}
                  onClick={handleExportSelected}
                >
                  Export Selected
                </Button>
              </Group>
            </Group>
          </Paper>
        )}

        {/* Content Table / Cards */}
        {isLoading ? (
          <Center py="xl">
            <Loader color="yellow" />
          </Center>
        ) : leads.length === 0 ? (
          <Paper p="xl" withBorder radius="md" ta="center">
            <Text size="sm" c="dimmed">
              No leads match your current tab or filter criteria.
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
                      <Table.Th style={{ width: 40 }}>
                        <Checkbox
                          checked={leads.length > 0 && selectedIds.length === leads.length}
                          indeterminate={selectedIds.length > 0 && selectedIds.length < leads.length}
                          onChange={(e) => handleSelectAll(e.currentTarget.checked)}
                        />
                      </Table.Th>
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
                    {leads.map((lead) => {
                      const overdue = isOverdue(lead);
                      const noDate = isNoFollowup(lead);
                      return (
                        <Table.Tr key={lead.id}>
                          <Table.Td>
                            <Checkbox
                              checked={selectedIds.includes(lead.id)}
                              onChange={(e) => handleSelectOne(lead.id, e.currentTarget.checked)}
                            />
                          </Table.Td>

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
                            {lead.remark && (
                              <Text size="10px" c="gray.6" lineClamp={1}>
                                <em>Remark: {lead.remark}</em>
                              </Text>
                            )}
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
                            {overdue && (
                              <Badge color="red" variant="filled" size="xs" mb={2}>
                                OVERDUE
                              </Badge>
                            )}
                            {noDate && (
                              <Badge color="orange" variant="filled" size="xs" mb={2}>
                                ⚠️ NO FOLLOW-UP DATE
                              </Badge>
                            )}
                            {lead.next_followup_at ? (
                              <Text size="xs" c={overdue ? 'red.8' : undefined} fw={overdue ? 600 : 400}>
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
                            <Group gap={4} justify="flex-end" wrap="nowrap">
                              <ActionIcon
                                component="a"
                                href={`tel:${lead.phone}`}
                                variant="subtle"
                                color="blue"
                                title="Call"
                              >
                                <IconPhone size={14} />
                              </ActionIcon>
                              <ActionIcon
                                component="a"
                                href={`https://wa.me/91${cleanPhone(lead.phone)}?text=Namaste`}
                                target="_blank"
                                variant="subtle"
                                color="green"
                                title="WhatsApp"
                              >
                                <IconBrandWhatsapp size={14} />
                              </ActionIcon>
                              <Button
                                size="compact-xs"
                                variant="light"
                                color="yellow"
                                leftSection={<IconClipboardCheck size={12} />}
                                onClick={() => {
                                  setSelectedLead(lead);
                                  setOutcomeModalOpen(true);
                                }}
                              >
                                Log
                              </Button>
                              <ActionIcon
                                variant="subtle"
                                color="gray"
                                title="Add Remark"
                                onClick={() => {
                                  setSelectedLead(lead);
                                  setRemarkModalOpen(true);
                                }}
                              >
                                <IconNotes size={14} />
                              </ActionIcon>
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
                      );
                    })}
                  </Table.Tbody>
                </Table>
              </Paper>
            </Box>

            {/* Mobile Card Stack */}
            <Stack hiddenFrom="sm" gap="sm">
              {leads.map((lead) => {
                const overdue = isOverdue(lead);
                const noDate = isNoFollowup(lead);
                return (
                  <Card key={lead.id} shadow="xs" padding="sm" radius="md" withBorder>
                    <Stack gap="xs">
                      <Group justify="space-between" align="flex-start">
                        <Group gap="xs">
                          <Checkbox
                            checked={selectedIds.includes(lead.id)}
                            onChange={(e) => handleSelectOne(lead.id, e.currentTarget.checked)}
                          />
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
                        </Group>
                        <Badge color={getStatusColor(lead.status)} variant="light" size="sm">
                          {lead.status}
                        </Badge>
                      </Group>

                      {overdue && (
                        <Badge color="red" variant="filled" size="xs">
                          OVERDUE
                        </Badge>
                      )}
                      {noDate && (
                        <Badge color="orange" variant="filled" size="xs">
                          ⚠️ NO NEXT FOLLOW-UP DATE
                        </Badge>
                      )}

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

                      {lead.remark && (
                        <Text size="10px" c="gray.6">
                          <em>Remark: {lead.remark}</em>
                        </Text>
                      )}

                      <Divider />

                      <Group justify="space-between">
                        <Group gap="xs">
                          <Button
                            component="a"
                            href={`tel:${lead.phone}`}
                            size="compact-xs"
                            variant="light"
                            color="blue"
                            leftSection={<IconPhone size={12} />}
                          >
                            Call
                          </Button>
                          <Button
                            component="a"
                            href={`https://wa.me/91${cleanPhone(lead.phone)}?text=Namaste`}
                            target="_blank"
                            size="compact-xs"
                            variant="light"
                            color="green"
                            leftSection={<IconBrandWhatsapp size={12} />}
                          >
                            WA
                          </Button>
                          <ActionIcon
                            size="sm"
                            variant="subtle"
                            color="gray"
                            onClick={() => {
                              setSelectedLead(lead);
                              setRemarkModalOpen(true);
                            }}
                          >
                            <IconNotes size={14} />
                          </ActionIcon>
                        </Group>

                        <Group gap="xs">
                          <Button
                            size="xs"
                            variant="light"
                            color="yellow"
                            leftSection={<IconClipboardCheck size={14} />}
                            onClick={() => {
                              setSelectedLead(lead);
                              setOutcomeModalOpen(true);
                            }}
                          >
                            Log Outcome
                          </Button>
                          <Button
                            size="xs"
                            variant="subtle"
                            onClick={() => navigate(`/leads/${lead.id}`)}
                          >
                            Details
                          </Button>
                        </Group>
                      </Group>
                    </Stack>
                  </Card>
                );
              })}
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

      <AddRemarkModal
        opened={remarkModalOpen}
        onClose={() => setRemarkModalOpen(false)}
        lead={selectedLead}
        onSuccess={() => refetch()}
      />
    </Container>
  );
};
