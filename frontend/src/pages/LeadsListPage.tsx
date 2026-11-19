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
import { useTranslation } from 'react-i18next';
import { translateStatus, translateRoofType, translatePropertyType, translateRole } from '../i18n/formatters';
import { NewLeadModal } from '../components/modals/NewLeadModal';
import { LogOutcomeModal } from '../components/modals/LogOutcomeModal';
import { AddRemarkModal } from '../components/modals/AddRemarkModal';
import type { Lead, LeadSource, User } from '../api/types';
import { useRegion } from '../context/RegionContext';
import { useAuth } from '../context/AuthContext';

export const LeadsListPage: React.FC = () => {
  const { t, i18n } = useTranslation(['leads', 'common']);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const { selectedRegion } = useRegion();
  const { can, isAdminOrManager } = useAuth();

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
  if (selectedRegion) queryParams.region = selectedRegion;

  const { data: leadsData, isLoading, refetch } = useQuery<{ results: Lead[]; count: number }>({
    queryKey: ['leads', queryParams, selectedRegion],
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
            <Title order={3}>{t('title', 'All Leads')} ({totalCount})</Title>
            <Text size="xs" c="dimmed">
              {t('subtitle', 'Filter by saved views, perform bulk team updates, and log interaction outcomes')}
            </Text>
          </div>
          <Group gap="xs">
            {can('lead.export') && (
              <Button
                variant="light"
                color="gray"
                size="xs"
                leftSection={<IconDownload size={14} />}
                onClick={handleExportFiltered}
              >
                {t('export_csv', 'Export to CSV')}
              </Button>
            )}
            <Button
              color="yellow"
              size="xs"
              leftSection={<IconPlus size={16} />}
              onClick={() => setNewLeadModalOpen(true)}
            >
              {t('new_lead', 'New Lead')}
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
            <Tabs.Tab value="all">{t('filters.all', 'All Leads')}</Tabs.Tab>
            <Tabs.Tab value="my">{t('filters.my', 'My Leads')}</Tabs.Tab>
            <Tabs.Tab value="due_today" leftSection={<IconClock size={14} />}>
              {t('filters.due_today', 'Due Today')}
            </Tabs.Tab>
            <Tabs.Tab
              value="overdue"
              leftSection={<IconAlertTriangle size={14} color="red" />}
            >
              {t('filters.overdue', 'Overdue')}
            </Tabs.Tab>
            <Tabs.Tab value="no_followup">
              {t('filters.no_followup', 'No Follow-up Date')}
            </Tabs.Tab>
            <Tabs.Tab value="interested">{t('filters.interested', 'Interested')}</Tabs.Tab>
            <Tabs.Tab value="quote_sent">{t('filters.quote_sent', 'Quote Sent')}</Tabs.Tab>
          </Tabs.List>
        </Tabs>

        {/* Filters Bar */}
        <Paper p="sm" withBorder radius="md">
          <Group gap="sm" wrap="wrap">
            <TextInput
              placeholder={t('filters.search_placeholder', 'Search by name, phone or city...')}
              leftSection={<IconSearch size={16} />}
              value={search}
              onChange={(e) => {
                setSearch(e.currentTarget.value);
                setPage(1);
              }}
              style={{ flex: 1, minWidth: 200 }}
            />

            <Select
              placeholder={t('filters.status_placeholder', 'Filter by Status')}
              clearable
              data={[
                { value: 'New', label: translateStatus('New', i18n.language) },
                { value: 'Attempting contact', label: translateStatus('Attempting contact', i18n.language) },
                { value: 'Callback scheduled', label: translateStatus('Callback scheduled', i18n.language) },
                { value: 'Interested', label: translateStatus('Interested', i18n.language) },
                { value: 'Survey to schedule', label: translateStatus('Survey to schedule', i18n.language) },
                { value: 'Survey scheduled', label: translateStatus('Survey scheduled', i18n.language) },
                { value: 'Design pending', label: translateStatus('Design pending', i18n.language) },
                { value: 'Quote sent', label: translateStatus('Quote sent', i18n.language) },
                { value: 'Revising quote', label: translateStatus('Revising quote', i18n.language) },
                { value: 'Negotiation', label: translateStatus('Negotiation', i18n.language) },
                { value: 'Won', label: translateStatus('Won', i18n.language) },
                { value: 'Lost', label: translateStatus('Lost', i18n.language) },
                { value: 'Nurture', label: translateStatus('Nurture', i18n.language) },
                { value: 'Unreachable', label: translateStatus('Unreachable', i18n.language) },
                { value: 'Do not contact', label: translateStatus('Do not contact', i18n.language) },
                { value: 'Merged', label: translateStatus('Merged', i18n.language) },
              ]}
              value={statusFilter}
              onChange={(val) => {
                setStatusFilter(val);
                setPage(1);
              }}
              style={{ minWidth: 170 }}
            />

            <Select
              placeholder={t('filters.source_placeholder', 'Filter by Source')}
              clearable
              data={sources.map((s) => ({ value: String(s.id), label: s.display_name || s.name }))}
              value={sourceFilter}
              onChange={(val) => {
                setSourceFilter(val);
                setPage(1);
              }}
              style={{ minWidth: 150 }}
            />

            {(can('user.view_team') || isAdminOrManager) && (
              <Select
                placeholder={t('filters.assignee_placeholder', 'Filter by Assignee')}
                clearable
                data={users.map((u) => ({
                  value: String(u.id),
                  label: `${u.first_name || u.username} (${translateRole(u.role, i18n.language)})`,
                }))}
                value={assigneeFilter}
                onChange={(val) => {
                  setAssigneeFilter(val);
                  setPage(1);
                }}
                style={{ minWidth: 160 }}
              />
            )}
          </Group>
        </Paper>

        {/* Bulk Actions Floating Bar */}
        {selectedIds.length > 0 && (
          <Paper p="xs" withBorder bg="var(--mantine-color-yellow-0)" radius="md">
            <Group justify="space-between" wrap="wrap">
              <Group gap="sm">
                <Badge color="yellow" size="lg">
                  {t('bulk.selected', { count: selectedIds.length, defaultValue: `${selectedIds.length} leads selected` })}
                </Badge>
                <Button size="xs" variant="subtle" color="gray" onClick={() => setSelectedIds([])}>
                  {t('bulk.clear', 'Clear Selection')}
                </Button>
              </Group>

              <Group gap="xs" wrap="wrap">
                {/* Bulk Assign (Managers & Admins only) */}
                {can('lead.assign') && (
                  <Group gap={4}>
                    <Select
                      placeholder={t('bulk.assign_to', 'Assign to...')}
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
                      {t('bulk.assign_btn', 'Assign')}
                    </Button>
                  </Group>
                )}

                {/* Bulk Change Source (Managers & Admins only) */}
                {isAdminOrManager && (
                  <Group gap={4}>
                    <Select
                      placeholder={t('bulk.change_source', 'Change source...')}
                      size="xs"
                      data={sources.map((s) => ({ value: String(s.id), label: s.display_name || s.name }))}
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
                      {t('bulk.set_source_btn', 'Set Source')}
                    </Button>
                  </Group>
                )}

                {can('lead.export') && (
                  <Button
                    size="xs"
                    variant="light"
                    color="blue"
                    leftSection={<IconDownload size={14} />}
                    onClick={handleExportSelected}
                  >
                    {t('bulk.export_selected', 'Export Selected')}
                  </Button>
                )}
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
              {t('empty', 'No leads match your current tab or filter criteria.')}
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
                      <Table.Th>{t('table.name_id', 'Name & ID')}</Table.Th>
                      <Table.Th>{t('table.phone_city', 'Phone / City')}</Table.Th>
                      <Table.Th>{t('table.status', 'Status')}</Table.Th>
                      <Table.Th>{t('table.next_action', 'Next Action')}</Table.Th>
                      <Table.Th>{t('table.next_followup', 'Next Follow-up')}</Table.Th>
                      <Table.Th>{t('table.assigned_to', 'Assigned Rep')}</Table.Th>
                      <Table.Th ta="right">{t('table.actions', 'Actions')}</Table.Th>
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
                              <Badge size="xs" variant="light" color={lead.region === 'AU' ? 'blue' : 'green'}>
                                {lead.region === 'AU' ? '🇦🇺 AU' : '🇮🇳 IN'}
                              </Badge>
                            </Group>
                            <Text size="10px" c="dimmed">
                              {translatePropertyType(lead.property_type, i18n.language) || 'Residential'} • {translateRoofType(lead.roof_type, i18n.language) || 'RCC'}
                            </Text>
                            {lead.remark && (
                              <Text size="10px" c="gray.6" lineClamp={1}>
                                <em>{t('fields.remark', 'Remark')}: {lead.remark}</em>
                              </Text>
                            )}
                          </Table.Td>

                          <Table.Td>
                            <Text size="xs" fw={500}>
                              {lead.phone_display || lead.phone_e164 || lead.phone}
                            </Text>
                            <Text size="10px" c="dimmed">
                              {lead.city}{lead.suburb ? `, ${lead.suburb}` : ''} {lead.state ? `(${lead.state})` : ''}
                            </Text>
                            {lead.is_within_calling_hours === false && (
                              <Badge color="red" size="xs" variant="filled" mt={2} title={lead.calling_hours_reason}>
                                {t('outside_call_hours', 'Outside Call Hours')}
                              </Badge>
                            )}
                          </Table.Td>

                          <Table.Td>
                            <Badge color={getStatusColor(lead.status)} variant="light">
                              {translateStatus(lead.status, i18n.language)}
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
                                {t('overdue_badge', 'OVERDUE')}
                              </Badge>
                            )}
                            {noDate && (
                              <Badge color="orange" variant="filled" size="xs" mb={2}>
                                {t('no_followup_badge', '⚠️ NO FOLLOW-UP DATE')}
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
                            <Text size="xs">{lead.assigned_to_name || t('unassigned', 'Unassigned')}</Text>
                          </Table.Td>

                          <Table.Td ta="right">
                            <Group gap={4} justify="flex-end" wrap="nowrap">
                              <ActionIcon
                                component="a"
                                href={lead.tel_url || (lead.phone_e164 ? `tel:${lead.phone_e164}` : `tel:${lead.phone}`)}
                                variant="subtle"
                                color="blue"
                                title={lead.do_not_contact ? "Do Not Contact" : (lead.opt_out_calls ? "Opted Out of Calls" : t('actions.call', 'Call'))}
                                disabled={lead.do_not_contact || lead.opt_out_calls}
                              >
                                <IconPhone size={14} />
                              </ActionIcon>
                              <ActionIcon
                                component="a"
                                href={lead.whatsapp_url || (lead.phone_e164 ? `https://wa.me/${lead.phone_e164.replace(/\D/g, '')}` : `https://wa.me/${cleanPhone(lead.phone)}`)}
                                target="_blank"
                                variant="subtle"
                                color="green"
                                title={lead.do_not_contact ? "Do Not Contact" : (lead.opt_out_whatsapp ? "Opted Out of WhatsApp" : t('actions.whatsapp', 'WhatsApp'))}
                                disabled={lead.do_not_contact || lead.opt_out_whatsapp}
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
                                {t('actions.log', 'Log')}
                              </Button>
                              <ActionIcon
                                variant="subtle"
                                color="gray"
                                title={t('actions.add_remark', 'Add Remark')}
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
                                title={t('actions.view_lead', 'View lead')}
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
                            <Group gap={4}>
                              <Text
                                fw={600}
                                size="sm"
                                style={{ cursor: 'pointer' }}
                                onClick={() => navigate(`/leads/${lead.id}`)}
                              >
                                {lead.name}
                              </Text>
                              <Badge size="xs" variant="light" color={lead.region === 'AU' ? 'blue' : 'green'}>
                                {lead.region === 'AU' ? '🇦🇺 AU' : '🇮🇳 IN'}
                              </Badge>
                            </Group>
                            <Text size="xs" c="dimmed">
                              {lead.phone_display || lead.phone_e164 || lead.phone} • {lead.city}{lead.suburb ? `, ${lead.suburb}` : ''}
                            </Text>
                            {lead.is_within_calling_hours === false && (
                              <Badge color="red" size="xs" variant="filled" mt={2} title={lead.calling_hours_reason}>
                                {t('outside_call_hours', 'Outside Call Hours')}
                              </Badge>
                            )}
                          </div>
                        </Group>
                        <Badge color={getStatusColor(lead.status)} variant="light" size="sm">
                          {translateStatus(lead.status, i18n.language)}
                        </Badge>
                      </Group>

                      {overdue && (
                        <Badge color="red" variant="filled" size="xs">
                          {t('overdue_badge', 'OVERDUE')}
                        </Badge>
                      )}
                      {noDate && (
                        <Badge color="orange" variant="filled" size="xs">
                          {t('no_followup_badge', '⚠️ NO FOLLOW-UP DATE')}
                        </Badge>
                      )}

                      {lead.next_action && (
                        <Text size="xs">
                          <strong>{t('fields.next_action', 'Next Action')}:</strong> {lead.next_action}
                        </Text>
                      )}

                      {lead.next_followup_at && (
                        <Text size="xs" c="dimmed">
                          <strong>{t('fields.next_followup', 'Follow-up')}:</strong>{' '}
                          {lead.user_next_followup_display || lead.next_followup_display || new Date(lead.next_followup_at).toLocaleString([], {
                            dateStyle: 'short',
                            timeStyle: 'short',
                          })}
                        </Text>
                      )}

                      {lead.remark && (
                        <Text size="10px" c="gray.6">
                          <em>{t('fields.remark', 'Remark')}: {lead.remark}</em>
                        </Text>
                      )}

                      <Divider />

                      <Group justify="space-between">
                        <Group gap="xs">
                          <Button
                            component="a"
                            href={lead.tel_url || (lead.phone_e164 ? `tel:${lead.phone_e164}` : `tel:${lead.phone}`)}
                            size="compact-xs"
                            variant="light"
                            color="blue"
                            leftSection={<IconPhone size={12} />}
                            disabled={lead.do_not_contact || lead.opt_out_calls}
                          >
                            {t('actions.call', 'Call')}
                          </Button>
                          <Button
                            component="a"
                            href={lead.whatsapp_url || (lead.phone_e164 ? `https://wa.me/${lead.phone_e164.replace(/\D/g, '')}` : `https://wa.me/${cleanPhone(lead.phone)}`)}
                            target="_blank"
                            size="compact-xs"
                            variant="light"
                            color="green"
                            leftSection={<IconBrandWhatsapp size={12} />}
                            disabled={lead.do_not_contact || lead.opt_out_whatsapp}
                          >
                            {t('actions.whatsapp', 'WA')}
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
                            {t('actions.log_outcome', 'Log Outcome')}
                          </Button>
                          <Button
                            size="xs"
                            variant="subtle"
                            onClick={() => navigate(`/leads/${lead.id}`)}
                          >
                            {t('actions.details', 'Details')}
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
