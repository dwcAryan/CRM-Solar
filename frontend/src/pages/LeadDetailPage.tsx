import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Container,
  Title,
  Text,
  Group,
  Stack,
  Button,
  Badge,
  Card,
  Tabs,
  Paper,
  SimpleGrid,
  Timeline,
  Table,
  Loader,
  Center,
  Alert,
  Divider,
  Box,
} from '@mantine/core';
import {
  IconPhone,
  IconBrandWhatsapp,
  IconClipboardCheck,
  IconCalendarPlus,
  IconFilePlus,
  IconGitMerge,
  IconArrowLeft,
  IconClock,
  IconBolt,
  IconCheck,
  IconX,
  IconAlertCircle,
  IconAlertTriangle,
  IconSend,
  IconRefresh,
  IconNotes,
} from '@tabler/icons-react';
import {
  fetchLead,
  fetchActivities,
  fetchSurveys,
  fetchQuotes,
  markSurveyMissed,
  markQuoteSent,
  acceptQuote,
} from '../api/client';
import { LogOutcomeModal } from '../components/modals/LogOutcomeModal';
import { BookSurveyModal } from '../components/modals/BookSurveyModal';
import { RescheduleSurveyModal } from '../components/modals/RescheduleSurveyModal';
import { MarkDoneSurveyModal } from '../components/modals/MarkDoneSurveyModal';
import { CreateQuoteModal } from '../components/modals/CreateQuoteModal';
import { ReviseQuoteModal } from '../components/modals/ReviseQuoteModal';
import { RejectQuoteModal } from '../components/modals/RejectQuoteModal';
import { MergeLeadModal } from '../components/modals/MergeLeadModal';
import { AddRemarkModal } from '../components/modals/AddRemarkModal';
import { ConfirmActionModal } from '../components/modals/ConfirmActionModal';
import type { Lead, Activity, Survey, Quote, LeadStatusHistory } from '../api/types';

export const LeadDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const leadId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Modals state
  const [outcomeModalOpen, setOutcomeModalOpen] = useState(false);
  const [bookSurveyOpen, setBookSurveyOpen] = useState(false);
  const [rescheduleSurveyOpen, setRescheduleSurveyOpen] = useState(false);
  const [selectedSurvey, setSelectedSurvey] = useState<Survey | null>(null);
  const [markDoneSurveyOpen, setMarkDoneSurveyOpen] = useState(false);
  const [createQuoteOpen, setCreateQuoteOpen] = useState(false);
  const [reviseQuoteOpen, setReviseQuoteOpen] = useState(false);
  const [rejectQuoteOpen, setRejectQuoteOpen] = useState(false);
  const [selectedQuote, setSelectedQuote] = useState<Quote | null>(null);
  const [mergeModalOpen, setMergeModalOpen] = useState(false);
  const [addRemarkOpen, setAddRemarkOpen] = useState(false);
  const [confirmAcceptQuote, setConfirmAcceptQuote] = useState<Quote | null>(null);

  // Queries
  const { data: lead, isLoading: leadLoading, isError, refetch: refetchLead } = useQuery<Lead>({
    queryKey: ['lead', leadId],
    queryFn: () => fetchLead(leadId),
    enabled: !!leadId,
  });

  const { data: activities = [] } = useQuery<Activity[]>({
    queryKey: ['activities', leadId],
    queryFn: () => fetchActivities({ lead: leadId }),
    enabled: !!leadId,
  });

  const { data: surveys = [] } = useQuery<Survey[]>({
    queryKey: ['surveys', leadId],
    queryFn: () => fetchSurveys({ lead: leadId }),
    enabled: !!leadId,
  });

  const { data: quotes = [] } = useQuery<Quote[]>({
    queryKey: ['quotes', leadId],
    queryFn: () => fetchQuotes({ lead: leadId }),
    enabled: !!leadId,
  });

  // Action mutations
  const missedSurveyMutation = useMutation({
    mutationFn: (surveyId: number) => markSurveyMissed(surveyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['surveys', leadId] });
      queryClient.invalidateQueries({ queryKey: ['lead', leadId] });
    },
  });

  const sendQuoteMutation = useMutation({
    mutationFn: (quoteId: number) => markQuoteSent(quoteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotes', leadId] });
      queryClient.invalidateQueries({ queryKey: ['lead', leadId] });
    },
  });

  const acceptQuoteMutation = useMutation({
    mutationFn: (quoteId: number) => acceptQuote(quoteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotes', leadId] });
      queryClient.invalidateQueries({ queryKey: ['lead', leadId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  if (leadLoading) {
    return (
      <Center py="xl">
        <Loader color="yellow" />
      </Center>
    );
  }

  if (isError || !lead) {
    return (
      <Container size="md" py="xl">
        <Alert icon={<IconAlertCircle size={16} />} title="Error" color="red">
          Lead #{leadId} not found or you do not have permission to view it.
        </Alert>
        <Button mt="md" variant="subtle" onClick={() => navigate('/leads')}>
          Back to Leads
        </Button>
      </Container>
    );
  }

  const cleanPhone = lead.phone.replace(/\D/g, '').slice(-10);

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
      default:
        return 'blue';
    }
  };

  const isTerminal = ['Won', 'Lost', 'Do not contact', 'Merged', 'Invalid contact'].includes(lead.status);
  const hasNoFollowup = !isTerminal && !lead.next_followup_at;

  return (
    <Container size="xl" py="md">
      <Stack gap="lg">
        {/* Top Back bar */}
        <Group justify="space-between">
          <Button
            variant="subtle"
            color="gray"
            leftSection={<IconArrowLeft size={16} />}
            onClick={() => navigate('/leads')}
          >
            All Leads
          </Button>

          <Group gap="xs">
            <Button
              variant="outline"
              color="gray"
              size="xs"
              leftSection={<IconNotes size={14} />}
              onClick={() => setAddRemarkOpen(true)}
            >
              Add Remark
            </Button>
            <Button
              variant="outline"
              color="orange"
              size="xs"
              leftSection={<IconGitMerge size={14} />}
              onClick={() => setMergeModalOpen(true)}
            >
              Merge Duplicate
            </Button>
            <Button
              variant="outline"
              color="teal"
              size="xs"
              leftSection={<IconCalendarPlus size={14} />}
              onClick={() => setBookSurveyOpen(true)}
            >
              Book Survey
            </Button>
            <Button
              variant="outline"
              color="blue"
              size="xs"
              leftSection={<IconFilePlus size={14} />}
              onClick={() => setCreateQuoteOpen(true)}
            >
              Create Quote
            </Button>
            <Button
              color="yellow"
              size="xs"
              leftSection={<IconClipboardCheck size={14} />}
              onClick={() => setOutcomeModalOpen(true)}
            >
              Log Outcome
            </Button>
          </Group>
        </Group>

        {/* Missing Next Follow-up Warning Badge/Banner for active non-terminal leads */}
        {hasNoFollowup && (
          <Alert
            icon={<IconAlertTriangle size={18} />}
            color="red"
            variant="filled"
            title="Warning: No Next Follow-up Date Scheduled!"
            styles={{ title: { fontWeight: 700 } }}
          >
            <Text size="xs">
              This lead is active in status <strong>{lead.status}</strong>, but has no scheduled next follow-up date. The CRM workflow requires every active lead to have a pending follow-up. Please click <strong>Log Outcome</strong> to schedule a follow-up date and time.
            </Text>
          </Alert>
        )}

        {/* Lead Summary Card */}
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Stack gap="md">
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <div>
                <Group gap="xs" align="center">
                  <Title order={3}>{lead.name}</Title>
                  <Badge size="md" color="gray">
                    Lead #{lead.id}
                  </Badge>
                  {lead.do_not_contact && (
                    <Badge color="red" variant="filled">
                      DO NOT CONTACT
                    </Badge>
                  )}
                </Group>
                <Text size="xs" c="dimmed" mt={2}>
                  Created {new Date(lead.created_at).toLocaleDateString([], { dateStyle: 'medium' })} • Source:{' '}
                  {lead.source_name || 'Direct'}
                </Text>
              </div>

              <Badge size="xl" color={getStatusColor(lead.status)} variant="filled">
                {lead.status}
              </Badge>
            </Group>

            <Divider />

            <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
              <Box>
                <Text size="xs" c="dimmed">
                  Contact Phone
                </Text>
                <Text fw={600} size="sm">
                  {lead.phone}
                </Text>
                {lead.alt_phone && (
                  <Text size="xs" c="dimmed">
                    Alt: {lead.alt_phone}
                  </Text>
                )}
                <Group gap="xs" mt={4}>
                  <Button
                    component="a"
                    href={`tel:${lead.phone}`}
                    size="compact-xs"
                    variant="light"
                    color="blue"
                    leftSection={<IconPhone size={12} />}
                    disabled={lead.do_not_contact}
                  >
                    Call
                  </Button>
                  <Button
                    component="a"
                    href={`https://wa.me/91${cleanPhone}?text=${encodeURIComponent(
                      `Namaste ${lead.name}! Calling regarding your solar proposal.`
                    )}`}
                    target="_blank"
                    size="compact-xs"
                    variant="light"
                    color="green"
                    leftSection={<IconBrandWhatsapp size={12} />}
                    disabled={lead.do_not_contact}
                  >
                    WhatsApp
                  </Button>
                </Group>
              </Box>

              <Box>
                <Text size="xs" c="dimmed">
                  Location & Address
                </Text>
                <Text fw={500} size="sm">
                  {lead.city} {lead.pincode ? `(${lead.pincode})` : ''}
                </Text>
                <Text size="xs" c="dimmed" lineClamp={2}>
                  {lead.address || 'Address not recorded'}
                </Text>
              </Box>

              <Box>
                <Text size="xs" c="dimmed">
                  Property & Consumption
                </Text>
                <Text fw={500} size="sm">
                  {lead.property_type || 'Residential'} • {lead.roof_type || 'RCC'}
                </Text>
                <Text size="xs" c="dimmed">
                  Monthly Bill: ₹{lead.monthly_bill?.toLocaleString('en-IN') || '—'}
                </Text>
                <Text size="10px" c="dimmed">
                  Occupancy: {lead.owner_or_tenant || 'Owner'}
                </Text>
              </Box>

              <Box>
                <Text size="xs" c="dimmed">
                  Next Step & Follow-up
                </Text>
                <Text fw={600} size="sm" c={hasNoFollowup ? 'red.9' : 'yellow.9'}>
                  {lead.next_action || 'No action pending'}
                </Text>
                <Group gap={4} mt={2}>
                  <IconClock size={14} color={hasNoFollowup ? '#fa5252' : '#fab005'} />
                  <Text size="xs" fw={500} c={hasNoFollowup ? 'red' : undefined}>
                    {lead.next_followup_at
                      ? new Date(lead.next_followup_at).toLocaleString([], {
                          dateStyle: 'short',
                          timeStyle: 'short',
                        })
                      : 'No follow-up set'}
                  </Text>
                </Group>
                {hasNoFollowup && (
                  <Badge color="red" size="xs" variant="filled" mt={4}>
                    ⚠️ NO FOLLOW-UP DATE
                  </Badge>
                )}
                <Text size="10px" c="dimmed" mt={2}>
                  Assigned: {lead.assigned_to_name || 'Unassigned'} • Call Attempts: {lead.attempt_count}
                </Text>
              </Box>
            </SimpleGrid>

            {lead.status === 'Won' && lead.won_at && (
              <Alert icon={<IconCheck size={16} />} color="green" title="Proposal Accepted & Won!">
                <Text size="xs">
                  This lead successfully agreed to the solar proposal on{' '}
                  {new Date(lead.won_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}.
                </Text>
              </Alert>
            )}

            {lead.status === 'Lost' && (
              <Alert icon={<IconX size={16} />} color="red" title="Lead Lost">
                <Text size="xs">Reason: {lead.lost_reason_name || 'Not specified'}</Text>
              </Alert>
            )}

            {lead.status === 'Nurture' && (
              <Alert icon={<IconClock size={16} />} color="orange" title="In Nurture Queue">
                <Text size="xs">Reason: {lead.nurture_reason_name || 'Not specified'}</Text>
              </Alert>
            )}
          </Stack>
        </Card>

        {/* Detail Tabs */}
        <Tabs defaultValue="timeline" color="yellow">
          <Tabs.List>
            <Tabs.Tab value="timeline" leftSection={<IconClock size={16} />}>
              Timeline & History ({activities.length})
            </Tabs.Tab>
            <Tabs.Tab value="surveys" leftSection={<IconClipboardCheck size={16} />}>
              Site Surveys ({surveys.length})
            </Tabs.Tab>
            <Tabs.Tab value="quotes" leftSection={<IconBolt size={16} />}>
              Quotations ({quotes.length})
            </Tabs.Tab>
          </Tabs.List>

          {/* Tab 1: Activity Timeline */}
          <Tabs.Panel value="timeline" pt="md">
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
              {/* Left: Interaction Timeline */}
              <Paper p="md" withBorder radius="md">
                <Group justify="space-between" mb="md">
                  <Text fw={600} size="sm">
                    Activity Timeline
                  </Text>
                  <Group gap="xs">
                    <Button
                      size="xs"
                      color="gray"
                      variant="subtle"
                      leftSection={<IconNotes size={14} />}
                      onClick={() => setAddRemarkOpen(true)}
                    >
                      Add Remark
                    </Button>
                    <Button
                      size="xs"
                      color="yellow"
                      variant="light"
                      leftSection={<IconClipboardCheck size={14} />}
                      onClick={() => setOutcomeModalOpen(true)}
                    >
                      Log Interaction
                    </Button>
                  </Group>
                </Group>

                {activities.length === 0 ? (
                  <Text size="xs" c="dimmed" ta="center" py="xl">
                    No activities logged yet.
                  </Text>
                ) : (
                  <Timeline active={activities.length} bulletSize={24} lineWidth={2}>
                    {activities.map((act) => (
                      <Timeline.Item
                        key={act.id}
                        title={
                          <Group gap="xs">
                            <Text size="xs" fw={600}>
                              {act.type.toUpperCase()}: {act.outcome_name || 'Logged'}
                            </Text>
                            <Badge size="xs" color="yellow" variant="light">
                              {act.status_after}
                            </Badge>
                          </Group>
                        }
                      >
                        {act.notes && (
                          <Text size="xs" c="dimmed" mt={2}>
                            {act.notes}
                          </Text>
                        )}
                        {act.remark && (
                          <Paper p="xs" mt={4} withBorder bg="var(--mantine-color-gray-0)" radius="sm">
                            <Text size="xs" fw={500} c="dark">
                              💬 Remark: {act.remark}
                            </Text>
                          </Paper>
                        )}
                        <Text size="10px" c="dimmed" mt={4}>
                          Next: {act.next_action} • By: {act.created_by_name || 'System'} •{' '}
                          {new Date(act.created_at).toLocaleString([], {
                            dateStyle: 'short',
                            timeStyle: 'short',
                          })}
                        </Text>
                      </Timeline.Item>
                    ))}
                  </Timeline>
                )}
              </Paper>

              {/* Right: Status Change Audit Log */}
              <Paper p="md" withBorder radius="md">
                <Text fw={600} size="sm" mb="md">
                  Status Change History
                </Text>
                {(!lead.status_history || lead.status_history.length === 0) ? (
                  <Text size="xs" c="dimmed" ta="center" py="xl">
                    No status changes recorded.
                  </Text>
                ) : (
                  <Timeline active={lead.status_history.length} bulletSize={20} lineWidth={2}>
                    {lead.status_history.map((sh: LeadStatusHistory) => (
                      <Timeline.Item
                        key={sh.id}
                        title={
                          <Text size="xs" fw={600}>
                            {sh.old_status} → {sh.new_status}
                          </Text>
                        }
                      >
                        {sh.note && (
                          <Text size="xs" c="dimmed">
                            {sh.note}
                          </Text>
                        )}
                        {sh.remark && (
                          <Paper p="xs" mt={4} withBorder bg="var(--mantine-color-gray-0)" radius="sm">
                            <Text size="xs" fw={500} c="dark">
                              💬 Remark: {sh.remark}
                            </Text>
                          </Paper>
                        )}
                        <Text size="10px" c="dimmed" mt={2}>
                          Changed by: {sh.changed_by_name || 'System'} •{' '}
                          {new Date(sh.changed_at).toLocaleString([], {
                            dateStyle: 'short',
                            timeStyle: 'short',
                          })}
                        </Text>
                      </Timeline.Item>
                    ))}
                  </Timeline>
                )}
              </Paper>
            </SimpleGrid>
          </Tabs.Panel>

          {/* Tab 2: Site Surveys */}
          <Tabs.Panel value="surveys" pt="md">
            <Paper p="md" withBorder radius="md">
              <Group justify="space-between" mb="md">
                <Text fw={600} size="sm">
                  Site Technical Surveys
                </Text>
                <Button
                  size="xs"
                  color="yellow"
                  leftSection={<IconCalendarPlus size={14} />}
                  onClick={() => setBookSurveyOpen(true)}
                >
                  Book New Survey
                </Button>
              </Group>

              {surveys.length === 0 ? (
                <Text size="xs" c="dimmed" ta="center" py="xl">
                  No site surveys booked for this lead yet.
                </Text>
              ) : (
                <Table highlightOnHover verticalSpacing="sm">
                  <Table.Thead bg="var(--mantine-color-gray-0)">
                    <Table.Tr>
                      <Table.Th>Scheduled Date & Time</Table.Th>
                      <Table.Th>Surveyor</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Site Suitable?</Table.Th>
                      <Table.Th>Notes</Table.Th>
                      <Table.Th ta="right">Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {surveys.map((survey) => (
                      <Table.Tr key={survey.id}>
                        <Table.Td>
                          <Text size="xs" fw={600}>
                            {new Date(survey.scheduled_at).toLocaleString([], {
                              dateStyle: 'medium',
                              timeStyle: 'short',
                            })}
                          </Text>
                          {survey.reschedule_count > 0 && (
                            <Badge size="xs" color="orange" variant="outline">
                              Rescheduled {survey.reschedule_count}x
                            </Badge>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs">{survey.surveyor_name || 'Unassigned'}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge
                            color={
                              survey.status === 'done'
                                ? 'green'
                                : survey.status === 'booked'
                                ? 'blue'
                                : survey.status === 'rescheduled'
                                ? 'orange'
                                : 'red'
                            }
                            variant="light"
                          >
                            {survey.status.toUpperCase()}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          {survey.site_suitable === true ? (
                            <Badge color="green" size="xs">
                              Yes
                            </Badge>
                          ) : survey.site_suitable === false ? (
                            <Badge color="red" size="xs">
                              No
                            </Badge>
                          ) : (
                            <Text size="xs" c="dimmed">
                              Pending
                            </Text>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs" lineClamp={2}>
                            {survey.notes || '—'}
                          </Text>
                          {survey.remark && (
                            <Text size="10px" c="blue" mt={2}>
                              💬 Remark: {survey.remark}
                            </Text>
                          )}
                        </Table.Td>
                        <Table.Td ta="right">
                          {survey.status === 'booked' || survey.status === 'rescheduled' ? (
                            <Group gap="xs" justify="flex-end">
                              <Button
                                size="xs"
                                color="green"
                                variant="light"
                                onClick={() => {
                                  setSelectedSurvey(survey);
                                  setMarkDoneSurveyOpen(true);
                                }}
                              >
                                Mark Done
                              </Button>
                              <Button
                                size="xs"
                                color="orange"
                                variant="subtle"
                                onClick={() => {
                                  setSelectedSurvey(survey);
                                  setRescheduleSurveyOpen(true);
                                }}
                              >
                                Reschedule
                              </Button>
                              <Button
                                size="xs"
                                color="red"
                                variant="subtle"
                                onClick={() => missedSurveyMutation.mutate(survey.id)}
                              >
                                Missed
                              </Button>
                            </Group>
                          ) : (
                            <Text size="xs" c="dimmed">
                              Completed
                            </Text>
                          )}
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Paper>
          </Tabs.Panel>

          {/* Tab 3: Quotations */}
          <Tabs.Panel value="quotes" pt="md">
            <Paper p="md" withBorder radius="md">
              <Group justify="space-between" mb="md">
                <Text fw={600} size="sm">
                  Quotation Versions & Proposals
                </Text>
                <Button
                  size="xs"
                  color="yellow"
                  leftSection={<IconFilePlus size={14} />}
                  onClick={() => setCreateQuoteOpen(true)}
                >
                  Create New Quote
                </Button>
              </Group>

              {quotes.length === 0 ? (
                <Text size="xs" c="dimmed" ta="center" py="xl">
                  No quotes generated for this lead yet.
                </Text>
              ) : (
                <Table highlightOnHover verticalSpacing="sm">
                  <Table.Thead bg="var(--mantine-color-gray-0)">
                    <Table.Tr>
                      <Table.Th>Version</Table.Th>
                      <Table.Th>System Size</Table.Th>
                      <Table.Th>Equipment Specs</Table.Th>
                      <Table.Th>Price & Subsidy</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th ta="right">Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {quotes.map((quote) => {
                      const net = quote.price - (quote.subsidy_amount || 0);
                      return (
                        <Table.Tr key={quote.id}>
                          <Table.Td>
                            <Badge color="gray" size="md">
                              v{quote.version}
                            </Badge>
                          </Table.Td>
                          <Table.Td>
                            <Text size="xs" fw={600}>
                              {quote.system_size_kw} kW
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            <Text size="xs">{quote.brand}</Text>
                            {quote.notes && (
                              <Text size="10px" c="dimmed">
                                {quote.notes}
                              </Text>
                            )}
                            {quote.remark && (
                              <Text size="10px" c="blue" mt={2}>
                                💬 Remark: {quote.remark}
                              </Text>
                            )}
                          </Table.Td>
                          <Table.Td>
                            <Text size="xs" fw={600}>
                              ₹{quote.price.toLocaleString('en-IN')}
                            </Text>
                            {quote.subsidy_amount ? (
                              <Text size="10px" c="green">
                                Subsidy: -₹{quote.subsidy_amount.toLocaleString('en-IN')} (Net: ₹
                                {net.toLocaleString('en-IN')})
                              </Text>
                            ) : null}
                          </Table.Td>
                          <Table.Td>
                            <Badge
                              color={
                                quote.status === 'accepted'
                                  ? 'green'
                                  : quote.status === 'rejected'
                                  ? 'red'
                                  : quote.status === 'sent'
                                  ? 'blue'
                                  : quote.status === 'revised'
                                  ? 'gray'
                                  : 'yellow'
                              }
                              variant="light"
                            >
                              {quote.status.toUpperCase()}
                            </Badge>
                          </Table.Td>
                          <Table.Td ta="right">
                            <Group gap="xs" justify="flex-end">
                              {quote.status === 'draft' && (
                                <Button
                                  size="xs"
                                  color="blue"
                                  variant="light"
                                  leftSection={<IconSend size={12} />}
                                  onClick={() => sendQuoteMutation.mutate(quote.id)}
                                >
                                  Mark Sent
                                </Button>
                              )}
                              {(quote.status === 'draft' || quote.status === 'sent') && (
                                <>
                                  <Button
                                    size="xs"
                                    color="green"
                                    variant="filled"
                                    onClick={() => setConfirmAcceptQuote(quote)}
                                  >
                                    Accept (Won)
                                  </Button>
                                  <Button
                                    size="xs"
                                    color="yellow"
                                    variant="light"
                                    leftSection={<IconRefresh size={12} />}
                                    onClick={() => {
                                      setSelectedQuote(quote);
                                      setReviseQuoteOpen(true);
                                    }}
                                  >
                                    Revise
                                  </Button>
                                  <Button
                                    size="xs"
                                    color="red"
                                    variant="subtle"
                                    onClick={() => {
                                      setSelectedQuote(quote);
                                      setRejectQuoteOpen(true);
                                    }}
                                  >
                                    Reject
                                  </Button>
                                </>
                              )}
                            </Group>
                          </Table.Td>
                        </Table.Tr>
                      );
                    })}
                  </Table.Tbody>
                </Table>
              )}
            </Paper>
          </Tabs.Panel>
        </Tabs>
      </Stack>

      {/* Modals */}
      <LogOutcomeModal
        opened={outcomeModalOpen}
        onClose={() => setOutcomeModalOpen(false)}
        lead={lead}
        onSuccess={() => {
          refetchLead();
          queryClient.invalidateQueries({ queryKey: ['activities', leadId] });
        }}
      />

      <BookSurveyModal
        opened={bookSurveyOpen}
        onClose={() => setBookSurveyOpen(false)}
        lead={lead}
        onSuccess={() => {
          refetchLead();
          queryClient.invalidateQueries({ queryKey: ['surveys', leadId] });
        }}
      />

      <RescheduleSurveyModal
        opened={rescheduleSurveyOpen}
        onClose={() => {
          setRescheduleSurveyOpen(false);
          setSelectedSurvey(null);
        }}
        survey={selectedSurvey}
        onSuccess={() => {
          refetchLead();
          queryClient.invalidateQueries({ queryKey: ['surveys', leadId] });
        }}
      />

      <MarkDoneSurveyModal
        opened={markDoneSurveyOpen}
        onClose={() => {
          setMarkDoneSurveyOpen(false);
          setSelectedSurvey(null);
        }}
        survey={selectedSurvey}
        onSuccess={() => {
          refetchLead();
          queryClient.invalidateQueries({ queryKey: ['surveys', leadId] });
        }}
      />

      <CreateQuoteModal
        opened={createQuoteOpen}
        onClose={() => setCreateQuoteOpen(false)}
        lead={lead}
        onSuccess={() => {
          refetchLead();
          queryClient.invalidateQueries({ queryKey: ['quotes', leadId] });
        }}
      />

      <ReviseQuoteModal
        opened={reviseQuoteOpen}
        onClose={() => {
          setReviseQuoteOpen(false);
          setSelectedQuote(null);
        }}
        quote={selectedQuote}
        onSuccess={() => {
          refetchLead();
          queryClient.invalidateQueries({ queryKey: ['quotes', leadId] });
        }}
      />

      <RejectQuoteModal
        opened={rejectQuoteOpen}
        onClose={() => {
          setRejectQuoteOpen(false);
          setSelectedQuote(null);
        }}
        quote={selectedQuote}
        onSuccess={() => {
          refetchLead();
          queryClient.invalidateQueries({ queryKey: ['quotes', leadId] });
        }}
      />

      <MergeLeadModal
        opened={mergeModalOpen}
        onClose={() => setMergeModalOpen(false)}
        duplicateLead={lead}
        onSuccess={() => {
          refetchLead();
        }}
      />

      <AddRemarkModal
        opened={addRemarkOpen}
        onClose={() => setAddRemarkOpen(false)}
        lead={lead}
        onSuccess={() => {
          refetchLead();
          queryClient.invalidateQueries({ queryKey: ['activities', leadId] });
        }}
      />

      <ConfirmActionModal
        opened={!!confirmAcceptQuote}
        onClose={() => setConfirmAcceptQuote(null)}
        onConfirm={() => {
          if (confirmAcceptQuote) {
            acceptQuoteMutation.mutate(confirmAcceptQuote.id);
            setConfirmAcceptQuote(null);
          }
        }}
        title="Confirm Proposal Won"
        message={`Are you sure you want to accept Proposal v${confirmAcceptQuote?.version}? This marks lead "${lead.name}" as Won and successfully completes the solar sales process.`}
        confirmLabel="Confirm Proposal Won"
        confirmColor="green"
        loading={acceptQuoteMutation.isPending}
      />
    </Container>
  );
};
