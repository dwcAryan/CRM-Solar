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
  ThemeIcon,
  Modal,
  Textarea,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
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
  IconDownload,
  IconShieldCheck,
  IconTrash,
} from '@tabler/icons-react';
import {
  fetchLead,
  fetchActivities,
  fetchSurveys,
  fetchQuotes,
  markSurveyMissed,
  markQuoteSent,
  acceptQuote,
  checkLeadDncr,
  softDeleteLead,
} from '../api/client';
import { useTranslation } from 'react-i18next';
import { translateStatus, translateRoofType, translatePropertyType } from '../i18n/formatters';
import { useAuth } from '../context/AuthContext';
import { LogOutcomeModal } from '../components/modals/LogOutcomeModal';
import { BookSurveyModal } from '../components/modals/BookSurveyModal';
import { RescheduleSurveyModal } from '../components/modals/RescheduleSurveyModal';
import { MarkDoneSurveyModal } from '../components/modals/MarkDoneSurveyModal';
import { CreateQuoteModal } from '../components/modals/CreateQuoteModal';
import { ReviseQuoteModal } from '../components/modals/ReviseQuoteModal';
import { RejectQuoteModal } from '../components/modals/RejectQuoteModal';
import { MergeLeadModal } from '../components/modals/MergeLeadModal';
import { downloadPdfBlob } from '../utils/downloadPdf';
import { AddRemarkModal } from '../components/modals/AddRemarkModal';
import { ConfirmActionModal } from '../components/modals/ConfirmActionModal';
import { AnonymizeLeadModal, PrivacyCorrectModal } from '../components/modals/PrivacyModals';
import { AISuggestionsCard } from '../components/ai/AISuggestionsCard';
import type { Lead, Activity, Survey, Quote, LeadStatusHistory } from '../api/types';

export const LeadDetailPage: React.FC = () => {
  const { t, i18n } = useTranslation(['leads', 'surveys', 'quotes', 'common']);
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
  const [prefilledOutcome, setPrefilledOutcome] = useState<string | null>(null);

  // Multi-country & Privacy & RBAC states
  const { isAdminOrManager, can } = useAuth();
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteReason, setDeleteReason] = useState('');
  const [anonymizeModalOpen, setAnonymizeModalOpen] = useState(false);
  const [correctModalOpen, setCorrectModalOpen] = useState(false);
  const [dncrLoading, setDncrLoading] = useState(false);

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

  const handleToggleDncr = async () => {
    if (!lead) return;
    setDncrLoading(true);
    try {
      const nextStatus = lead.dncr_status === 'on_register' ? 'not_on_register' : 'on_register';
      await checkLeadDncr(lead.id, nextStatus, 'Screened via CRM single-click action');
      queryClient.invalidateQueries({ queryKey: ['lead', leadId] });
      refetchLead();
    } catch (err: any) {
      console.error(err);
    } finally {
      setDncrLoading(false);
    }
  };

  const handleExportDossier = async (fmt: 'pdf' | 'json' = 'pdf') => {
    if (fmt === 'pdf') {
      try {
        await downloadPdfBlob(`/api/leads/${leadId}/privacy-export/?format=pdf`, `privacy_dossier_${leadId}.pdf`);
      } catch {
        // error toast handled inside downloadPdfBlob
      }
    } else {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      window.open(`${baseUrl}/api/leads/${leadId}/privacy-export/?format=${fmt}`, '_blank');
    }
  };

  const deleteMutation = useMutation({
    mutationFn: () => softDeleteLead(leadId, deleteReason),
    onSuccess: () => {
      notifications.show({ title: 'Lead Deleted', message: 'Lead has been soft-deleted.', color: 'red' });
      navigate('/leads');
    },
    onError: (err: any) => {
      notifications.show({ title: 'Error', message: err?.message || 'Failed to delete lead.', color: 'red' });
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
            {t('actions.back_to_leads', 'All Leads')}
          </Button>

          <Group gap="xs">
            <Button
              variant="outline"
              color="gray"
              size="xs"
              leftSection={<IconNotes size={14} />}
              onClick={() => setAddRemarkOpen(true)}
            >
              {t('actions.add_remark', 'Add Remark')}
            </Button>
            {can('lead.merge') && (
              <Button
                variant="outline"
                color="orange"
                size="xs"
                leftSection={<IconGitMerge size={14} />}
                onClick={() => setMergeModalOpen(true)}
              >
                {t('actions.merge', 'Merge Duplicate')}
              </Button>
            )}
            {can('survey.book') && (
              <Button
                variant="outline"
                color="teal"
                size="xs"
                leftSection={<IconCalendarPlus size={14} />}
                onClick={() => setBookSurveyOpen(true)}
              >
                {t('actions.book_survey', 'Book Survey')}
              </Button>
            )}
            {can('quote.create') && (
              <Button
                variant="outline"
                color="blue"
                size="xs"
                leftSection={<IconFilePlus size={14} />}
                onClick={() => setCreateQuoteOpen(true)}
              >
                {t('actions.create_quote', 'Create Quote')}
              </Button>
            )}
            {can('activity.log') && (
              <Button
                color="yellow"
                size="xs"
                leftSection={<IconClipboardCheck size={14} />}
                onClick={() => setOutcomeModalOpen(true)}
              >
                {t('actions.log_outcome', 'Log Outcome')}
              </Button>
            )}
            {can('lead.delete') && (
              <Button
                variant="light"
                color="red"
                size="xs"
                leftSection={<IconTrash size={14} />}
                onClick={() => {
                  setDeleteReason('');
                  setDeleteModalOpen(true);
                }}
              >
                {t('actions.soft_delete', 'Delete Lead')}
              </Button>
            )}

            {isAdminOrManager && (
              <>
                <Button
                  variant="light"
                  color="indigo"
                  size="xs"
                  leftSection={<IconDownload size={14} />}
                  onClick={() => handleExportDossier('pdf')}
                  title="Download complete compliance and privacy data subject dossier"
                >
                  {t('actions.privacy_export', 'DSAR Dossier (PDF)')}
                </Button>
                <Button
                  variant="light"
                  color="blue"
                  size="xs"
                  leftSection={<IconShieldCheck size={14} />}
                  onClick={() => setCorrectModalOpen(true)}
                  title="Rectify customer personal records with mandatory audit justification"
                >
                  {t('actions.correct_data', 'Correct Data')}
                </Button>
                <Button
                  variant="light"
                  color="red"
                  size="xs"
                  onClick={() => setAnonymizeModalOpen(true)}
                  title="Irreversibly anonymize customer identifiers"
                >
                  {t('actions.anonymize', 'Anonymize')}
                </Button>
              </>
            )}
          </Group>
        </Group>

        {/* Outside Permitted Calling Hours Alert */}
        {lead.is_within_calling_hours === false && (
          <Alert
            icon={<IconAlertTriangle size={18} />}
            color="red"
            variant="filled"
            title={`${t('alerts.outside_hours_title', 'Out of Permitted Calling Hours')} (${lead.region || 'Region'})`}
            styles={{ title: { fontWeight: 700 } }}
          >
            <Text size="xs">
              {lead.calling_hours_reason || t('alerts.outside_hours_message', 'Outbound voice calls to this customer are currently restricted by local telemarketing regulations.')}
            </Text>
          </Alert>
        )}

        {/* Missing Next Follow-up Warning Badge/Banner for active non-terminal leads */}
        {hasNoFollowup && (
          <Alert
            icon={<IconAlertTriangle size={18} />}
            color="red"
            variant="filled"
            title={t('alerts.no_followup_title', 'Warning: No Next Follow-up Date Scheduled!')}
            styles={{ title: { fontWeight: 700 } }}
          >
            <Text size="xs">
              {t('alerts.no_followup_message', 'This lead is active, but has no scheduled next follow-up date. Please click Log Outcome to schedule a date.')}
            </Text>
          </Alert>
        )}

        {/* Phase 7: AI Copilot & Next Action Suggestions */}
        {can('ai.suggest') && (
          <AISuggestionsCard
            lead={lead}
            onPreFillOutcome={(outcomeName) => {
              setPrefilledOutcome(outcomeName);
              setOutcomeModalOpen(true);
            }}
          />
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
                  <Badge size="md" variant="light" color={lead.region === 'AU' ? 'blue' : 'green'}>
                    {lead.region === 'AU' ? '🇦🇺 Australia (AU)' : '🇮🇳 India (IN)'}
                  </Badge>
                  {lead.do_not_contact && (
                    <Badge color="red" variant="filled">
                      DO NOT CONTACT
                    </Badge>
                  )}
                </Group>
                <Text size="xs" c="dimmed" mt={2}>
                  {t('fields.created_at', 'Created')}: {new Date(lead.created_at).toLocaleDateString([], { dateStyle: 'medium' })} • {t('fields.source', 'Source')}:{' '}
                  {lead.source_name || 'Direct'}
                </Text>
              </div>

              <Badge size="xl" color={getStatusColor(lead.status)} variant="filled">
                {translateStatus(lead.status, i18n.language)}
              </Badge>
            </Group>

            <Divider />

            <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
              <Box>
                <Text size="xs" c="dimmed">
                  {t('fields.phone', 'Contact Phone')}
                </Text>
                <Text fw={600} size="sm">
                  {lead.phone_display || lead.phone_e164 || lead.phone}
                </Text>
                {lead.alt_phone && (
                  <Text size="xs" c="dimmed">
                    {t('fields.alt_phone', 'Alt')}: {lead.alt_phone_display || lead.alt_phone_e164 || lead.alt_phone}
                  </Text>
                )}
                <Group gap="xs" mt={4}>
                  <Button
                    component="a"
                    href={lead.tel_url || (lead.phone_e164 ? `tel:${lead.phone_e164}` : `tel:${lead.phone}`)}
                    size="compact-xs"
                    variant="light"
                    color="blue"
                    leftSection={<IconPhone size={12} />}
                    disabled={lead.do_not_contact || lead.opt_out_calls}
                    title={lead.opt_out_calls ? "Opted Out of Voice Calls" : undefined}
                  >
                    {t('actions.call', 'Call')}
                  </Button>
                  <Button
                    component="a"
                    href={lead.whatsapp_url || (lead.phone_e164 ? `https://wa.me/${lead.phone_e164.replace(/\D/g, '')}` : `https://wa.me/${cleanPhone}`)}
                    target="_blank"
                    size="compact-xs"
                    variant="light"
                    color="green"
                    leftSection={<IconBrandWhatsapp size={12} />}
                    disabled={lead.do_not_contact || lead.opt_out_whatsapp}
                    title={lead.opt_out_whatsapp ? "Opted Out of WhatsApp" : undefined}
                  >
                    {t('actions.whatsapp', 'WhatsApp')}
                  </Button>
                </Group>
              </Box>

              <Box>
                <Text size="xs" c="dimmed">
                  {t('cards.location_tz', 'Location & Timezone')}
                </Text>
                <Text fw={500} size="sm">
                  {lead.suburb ? `${lead.suburb}, ` : ''}{lead.city} {lead.postcode || lead.pincode ? `(${lead.postcode || lead.pincode})` : ''}
                </Text>
                <Text size="xs" c="dimmed">
                  {t('fields.state', 'State')}: {lead.state || 'N/A'} • TZ: {lead.timezone || 'Asia/Kolkata'}
                </Text>
                <Text size="xs" c="dimmed" lineClamp={2}>
                  {lead.address || 'Address not recorded'}
                </Text>
              </Box>

              <Box>
                <Text size="xs" c="dimmed">
                  {t('cards.property_consumption', 'Property & Consumption')}
                </Text>
                <Text fw={500} size="sm">
                  {translatePropertyType(lead.property_type, i18n.language) || 'Residential'} • {translateRoofType(lead.roof_type, i18n.language) || 'RCC'}
                </Text>
                <Text size="xs" c="dimmed">
                  {t('fields.electricity_provider', 'Provider')}: {lead.electricity_provider || 'Not recorded'}
                </Text>
                <Text size="xs" c="dimmed">
                  {t('fields.bill_amount', 'Bill')}: {lead.bill_amount ? `${lead.currency_symbol || '$'}${Number(lead.bill_amount).toLocaleString()} (${lead.bill_period || 'monthly'})` : (lead.monthly_bill ? `${lead.currency_symbol || '₹'}${lead.monthly_bill.toLocaleString()}` : '—')}
                </Text>
                {lead.normalized_monthly_bill && (
                  <Text size="10px" c="teal" fw={600}>
                    Normalized: {lead.currency_symbol || '$'}{Number(lead.normalized_monthly_bill).toFixed(0)}/mo
                  </Text>
                )}
                <Text size="10px" c="dimmed">
                  {t('fields.owner_or_tenant', 'Occupancy')}: {lead.owner_or_tenant || 'Owner'}
                </Text>
              </Box>

              <Box>
                <Text size="xs" c="dimmed">
                  {t('cards.next_step', 'Next Step & Follow-up')}
                </Text>
                <Text fw={600} size="sm" c={hasNoFollowup ? 'red.9' : 'yellow.9'}>
                  {lead.next_action || 'No action pending'}
                </Text>
                <Group gap={4} mt={2}>
                  <IconClock size={14} color={hasNoFollowup ? '#fa5252' : '#fab005'} />
                  <Text size="xs" fw={500} c={hasNoFollowup ? 'red' : undefined}>
                    {lead.user_next_followup_display || lead.next_followup_display || (lead.next_followup_at
                      ? new Date(lead.next_followup_at).toLocaleString([], {
                          dateStyle: 'short',
                          timeStyle: 'short',
                        })
                      : 'No follow-up set')}
                  </Text>
                </Group>
                {hasNoFollowup && (
                  <Badge color="red" size="xs" variant="filled" mt={4}>
                    {t('no_followup_badge', '⚠️ NO FOLLOW-UP DATE')}
                  </Badge>
                )}
                <Text size="10px" c="dimmed" mt={2}>
                  {t('fields.assigned_to', 'Assigned')}: {lead.assigned_to_name || t('unassigned', 'Unassigned')} • {t('fields.attempt_count', 'Call Attempts')}: {lead.attempt_count}
                </Text>
              </Box>
            </SimpleGrid>

            {lead.status === 'Won' && lead.won_at && (
              <Alert icon={<IconCheck size={16} />} color="green" title={t('alerts.won_title', 'Proposal Accepted & Won!')}>
                <Text size="xs">
                  {t('alerts.won_message', 'This lead successfully agreed to the solar proposal on ')}
                  {new Date(lead.won_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}.
                </Text>
              </Alert>
            )}

            {lead.status === 'Lost' && (
              <Alert icon={<IconX size={16} />} color="red" title={t('alerts.lost_title', 'Lead Lost')}>
                <Text size="xs">{t('fields.remark', 'Reason')}: {lead.lost_reason_name || 'Not specified'}</Text>
              </Alert>
            )}

            {lead.status === 'Nurture' && (
              <Alert icon={<IconClock size={16} />} color="orange" title={t('alerts.nurture_title', 'In Nurture Queue')}>
                <Text size="xs">{t('fields.remark', 'Reason')}: {lead.nurture_reason_name || 'Not specified'}</Text>
              </Alert>
            )}
          </Stack>
        </Card>

        {/* Compliance, Consent & DNCR Overview */}
        <Card shadow="xs" padding="md" radius="md" withBorder bg="gray.0">
          <Group justify="space-between" align="center" wrap="wrap">
            <Group gap="md">
              <ThemeIcon size="md" color="blue" variant="light">
                <IconShieldCheck size={20} />
              </ThemeIcon>
              <div>
                <Group gap="xs">
                  <Text size="sm" fw={700}>{t('cards.compliance', 'Compliance & Consent Record')}</Text>
                  <Badge size="xs" color={lead.consent_status === 'consented' ? 'green' : 'gray'}>
                    Consent: {lead.consent_status || 'Unknown'}
                  </Badge>
                  <Badge size="xs" color="indigo" variant="light">
                    {t('fields.preferred_language', 'Customer Language')}: {lead.preferred_language === 'hi' ? 'हिन्दी (Hindi)' : 'English'}
                  </Badge>
                  {lead.consent_source && (
                    <Badge size="xs" variant="outline" color="gray">
                      {t('fields.consent_source', 'Source')}: {lead.consent_source}
                    </Badge>
                  )}
                </Group>
                <Text size="xs" c="dimmed">
                  Channel Authorizations: Calls: {lead.opt_out_calls ? '❌ Opted Out' : '✅ Allowed'} | SMS: {lead.opt_out_sms ? '❌ Opted Out' : '✅ Allowed'} | WhatsApp: {lead.opt_out_whatsapp ? '❌ Opted Out' : '✅ Allowed'}
                </Text>
              </div>
            </Group>

            <Group gap="xs">
              {lead.region === 'AU' && (
                <Group gap="xs">
                  <Badge
                    size="md"
                    color={lead.dncr_status === 'on_register' ? 'red' : 'teal'}
                    variant="light"
                  >
                    DNCR: {lead.dncr_status === 'on_register' ? 'On Register (Do Not Call)' : 'Not On Register'}
                  </Badge>
                  <Button
                    size="xs"
                    variant="default"
                    loading={dncrLoading}
                    onClick={handleToggleDncr}
                  >
                    Toggle DNCR Status
                  </Button>
                </Group>
              )}
            </Group>
          </Group>
        </Card>

        {/* Detail Tabs */}
        <Tabs defaultValue="timeline" color="yellow">
          <Tabs.List>
            <Tabs.Tab value="timeline" leftSection={<IconClock size={16} />}>
              {t('tabs.timeline', 'Timeline & History')} ({activities.length})
            </Tabs.Tab>
            <Tabs.Tab value="surveys" leftSection={<IconClipboardCheck size={16} />}>
              {t('tabs.surveys', 'Site Surveys')} ({surveys.length})
            </Tabs.Tab>
            <Tabs.Tab value="quotes" leftSection={<IconBolt size={16} />}>
              {t('tabs.quotes', 'Quotations')} ({quotes.length})
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
                  {t('surveys:title', 'Site Technical Surveys')}
                </Text>
                <Button
                  size="xs"
                  color="yellow"
                  leftSection={<IconCalendarPlus size={14} />}
                  onClick={() => setBookSurveyOpen(true)}
                >
                  {t('surveys:book_new', 'Book New Survey')}
                </Button>
              </Group>

              {surveys.length === 0 ? (
                <Text size="xs" c="dimmed" ta="center" py="xl">
                  {t('surveys:empty', 'No site surveys booked for this lead yet.')}
                </Text>
              ) : (
                <Table highlightOnHover verticalSpacing="sm">
                  <Table.Thead bg="var(--mantine-color-gray-0)">
                    <Table.Tr>
                      <Table.Th>{t('surveys:fields.scheduled_at', 'Scheduled Date & Time')}</Table.Th>
                      <Table.Th>{t('surveys:fields.surveyor', 'Surveyor')}</Table.Th>
                      <Table.Th>{t('surveys:fields.status', 'Status')}</Table.Th>
                      <Table.Th>{t('surveys:fields.site_suitable', 'Site Suitable?')}</Table.Th>
                      <Table.Th>{t('surveys:fields.notes', 'Notes')}</Table.Th>
                      <Table.Th ta="right">{t('common:actions.actions', 'Actions')}</Table.Th>
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
                              {t('surveys:rescheduled_times', { count: survey.reschedule_count, defaultValue: `Rescheduled ${survey.reschedule_count}x` })}
                            </Badge>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs">{survey.surveyor_name || t('common:fields.unassigned', 'Unassigned')}</Text>
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
                            {translateStatus(survey.status, i18n.language).toUpperCase()}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          {survey.site_suitable === true ? (
                            <Badge color="green" size="xs">
                              {t('surveys:fields.yes', 'Yes')}
                            </Badge>
                          ) : survey.site_suitable === false ? (
                            <Badge color="red" size="xs">
                              {t('surveys:fields.no', 'No')}
                            </Badge>
                          ) : (
                            <Text size="xs" c="dimmed">
                              {t('surveys:fields.pending', 'Pending')}
                            </Text>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs" lineClamp={2}>
                            {survey.notes || '—'}
                          </Text>
                          {survey.remark && (
                            <Text size="10px" c="blue" mt={2}>
                              💬 {t('leads:fields.remark', 'Remark')}: {survey.remark}
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
                                {t('surveys:actions.mark_done', 'Mark Done')}
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
                                {t('surveys:actions.reschedule', 'Reschedule')}
                              </Button>
                              <Button
                                size="xs"
                                color="red"
                                variant="subtle"
                                onClick={() => missedSurveyMutation.mutate(survey.id)}
                              >
                                {t('surveys:actions.mark_missed', 'Missed')}
                              </Button>
                            </Group>
                          ) : (
                            <Text size="xs" c="dimmed">
                              {t('surveys:status.completed', 'Completed')}
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
                  {t('quotes:title', 'Quotation Versions & Proposals')}
                </Text>
                <Button
                  size="xs"
                  color="yellow"
                  leftSection={<IconFilePlus size={14} />}
                  onClick={() => setCreateQuoteOpen(true)}
                >
                  {t('quotes:new_quote', 'Create New Quote')}
                </Button>
              </Group>

              {quotes.length === 0 ? (
                <Text size="xs" c="dimmed" ta="center" py="xl">
                  {t('quotes:empty', 'No quotes generated for this lead yet.')}
                </Text>
              ) : (
                <Table highlightOnHover verticalSpacing="sm">
                  <Table.Thead bg="var(--mantine-color-gray-0)">
                    <Table.Tr>
                      <Table.Th>{t('quotes:table.version', 'Version')}</Table.Th>
                      <Table.Th>{t('quotes:table.system_size', 'System Size')}</Table.Th>
                      <Table.Th>{t('quotes:table.equipment', 'Equipment Specs')}</Table.Th>
                      <Table.Th>{t('quotes:table.pricing', 'Price & Subsidy')}</Table.Th>
                      <Table.Th>{t('quotes:table.status', 'Status')}</Table.Th>
                      <Table.Th ta="right">{t('common:actions.actions', 'Actions')}</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {quotes.map((quote) => {
                      const currSym = quote.currency_symbol || (quote.currency === 'AUD' ? 'A$' : '₹');
                      const incLabel = quote.incentive_label || (quote.region === 'AU' ? 'Incentive (STCs)' : 'Subsidy');
                      const incAmount = quote.incentive_amount !== undefined && quote.incentive_amount !== null
                        ? quote.incentive_amount
                        : (quote.subsidy_amount || 0);
                      const net = quote.price - incAmount;

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
                            {quote.battery_kwh && (
                              <Badge size="xs" color="indigo" variant="light" mt={2}>
                                Battery: {quote.battery_kwh} kWh
                              </Badge>
                            )}
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
                              {currSym}{Number(quote.price).toLocaleString()}
                            </Text>
                            {incAmount > 0 && (
                              <Text size="10px" c="green">
                                {incLabel}: -{currSym}{Number(incAmount).toLocaleString()} (Net: {currSym}{Number(net).toLocaleString()})
                              </Text>
                            )}
                            {quote.tax_amount && (
                              <Text size="10px" c="dimmed">
                                Tax (GST): {currSym}{Number(quote.tax_amount).toLocaleString()}
                              </Text>
                            )}
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
                              {translateStatus(quote.status, i18n.language).toUpperCase()}
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
                                  {t('quotes:actions.mark_sent', 'Mark Sent')}
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
                                    {t('quotes:actions.accept', 'Accept (Won)')}
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
                                    {t('quotes:actions.revise', 'Revise')}
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
                                    {t('quotes:actions.reject', 'Reject')}
                                  </Button>
                                </>
                              )}
                              <Button
                                size="xs"
                                variant="light"
                                color="gray"
                                leftSection={<IconDownload size={12} />}
                                onClick={() => downloadPdfBlob(`/api/quotes/${quote.id}/pdf/`, `quote_${quote.id}.pdf`)}
                              >
                                PDF
                              </Button>
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
        onClose={() => {
          setOutcomeModalOpen(false);
          setPrefilledOutcome(null);
        }}
        lead={lead}
        initialOutcomeName={prefilledOutcome}
        onSuccess={() => {
          refetchLead();
          setPrefilledOutcome(null);
          queryClient.invalidateQueries({ queryKey: ['activities', leadId] });
          queryClient.invalidateQueries({ queryKey: ['ai-suggestion', leadId] });
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

      <AnonymizeLeadModal
        opened={anonymizeModalOpen}
        onClose={() => setAnonymizeModalOpen(false)}
        lead={lead}
        onSuccess={() => {
          refetchLead();
          queryClient.invalidateQueries({ queryKey: ['leads'] });
        }}
      />

      <PrivacyCorrectModal
        opened={correctModalOpen}
        onClose={() => setCorrectModalOpen(false)}
        lead={lead}
        onSuccess={() => {
          refetchLead();
          queryClient.invalidateQueries({ queryKey: ['leads'] });
        }}
      />

      {/* Admin Soft-Delete Lead Modal */}
      <Modal
        opened={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        title="Soft-Delete Lead"
        radius="md"
      >
        <Stack gap="md">
          <Text size="sm">
            Are you sure you want to soft-delete <b>{lead.name}</b>?
          </Text>
          <Text size="xs" c="dimmed">
            This lead will be removed from all active pipelines, sales queues, and reporting lists. A mandatory audit reason must be supplied.
          </Text>
          <Textarea
            label="Mandatory Deletion Reason"
            placeholder="e.g. Requested under Australian Privacy Principle 13 / GDPR / Duplicate error..."
            required
            value={deleteReason}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDeleteReason(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="light" color="gray" onClick={() => setDeleteModalOpen(false)}>Cancel</Button>
            <Button
              color="red"
              disabled={!deleteReason.trim()}
              loading={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
            >
              Confirm Soft-Delete
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
};
