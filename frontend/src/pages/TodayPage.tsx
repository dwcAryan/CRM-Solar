import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Container,
  Title,
  Text,
  Group,
  Stack,
  Card,
  Badge,
  Button,
  SimpleGrid,
  ThemeIcon,
  ActionIcon,
  Alert,
  Loader,
  Center,
  Paper,
  Tooltip,
} from '@mantine/core';
import {
  IconCalendarEvent,
  IconPhone,
  IconBrandWhatsapp,
  IconMessage,
  IconClipboardCheck,
  IconAlertTriangle,
  IconCheck,
  IconArrowRight,
  IconClock,
  IconNotes,
} from '@tabler/icons-react';
import { fetchTodayLeads } from '../api/client';
import { useTranslation } from 'react-i18next';
import { translateStatus, translateRoofType, translatePropertyType } from '../i18n/formatters';
import { useRegion } from '../context/RegionContext';
import { LogOutcomeModal } from '../components/modals/LogOutcomeModal';
import { AddRemarkModal } from '../components/modals/AddRemarkModal';
import type { Lead } from '../api/types';

export const TodayPage: React.FC = () => {
  const { t, i18n } = useTranslation(['today', 'leads', 'common']);
  const navigate = useNavigate();
  const { selectedRegion } = useRegion();
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [outcomeModalOpen, setOutcomeModalOpen] = useState(false);
  const [remarkModalOpen, setRemarkModalOpen] = useState(false);

  const { data: leads = [], isLoading, isError, refetch } = useQuery<Lead[]>({
    queryKey: ['today-leads', selectedRegion],
    queryFn: () => fetchTodayLeads(selectedRegion || undefined),
  });

  const now = new Date();

  const overdueLeads = leads.filter((l) => {
    if (!l.next_followup_at) return false;
    return new Date(l.next_followup_at) < now;
  });

  const dueTodayLeads = leads.filter((l) => {
    if (!l.next_followup_at) return false;
    return new Date(l.next_followup_at) >= now;
  });

  const handleOpenOutcome = (lead: Lead) => {
    setSelectedLead(lead);
    setOutcomeModalOpen(true);
  };

  const renderLeadCard = (lead: Lead, isOverdue: boolean) => {
    const isAU = lead.region_code === 'AU' || lead.region === 'AU';
    const cleanPhone = lead.phone_e164 || lead.phone;
    const canCall = !lead.do_not_contact && !lead.opt_out_calls;
    const canWhatsApp = !lead.do_not_contact && !lead.opt_out_whatsapp;
    const canSMS = !lead.do_not_contact && !lead.opt_out_sms;

    return (
      <Card
        key={lead.id}
        shadow="sm"
        padding="md"
        radius="md"
        withBorder
        style={{
          borderLeft: isOverdue ? '4px solid var(--mantine-color-red-6)' : '4px solid var(--mantine-color-yellow-6)',
        }}
      >
        <Stack gap="xs">
          <Group justify="space-between" align="flex-start" wrap="nowrap">
            <div>
              <Group gap="xs" wrap="wrap">
                <Text
                  fw={600}
                  size="md"
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/leads/${lead.id}`)}
                >
                  {lead.name}
                </Text>
                <Badge size="xs" color="gray">
                  #{lead.id}
                </Badge>
                <Badge size="xs" color={isAU ? 'teal' : 'orange'} variant="outline">
                  {lead.region_code || 'IN'}
                </Badge>
                {lead.is_within_calling_hours === false && (
                  <Badge size="xs" color="red" variant="dot" title={lead.calling_hours_reason || 'Outside permitted hours'}>
                    {t('leads:outside_call_hours', 'Outside Hours')}
                  </Badge>
                )}
                {lead.do_not_contact && (
                  <Badge size="xs" color="red" variant="filled">
                    DNC
                  </Badge>
                )}
              </Group>
              <Text size="xs" c="dimmed" mt={2}>
                {isAU
                  ? `${lead.suburb || lead.city}, ${lead.state || ''} ${lead.postcode || ''}`
                  : `${lead.city}, ${lead.state || ''} ${lead.pincode || ''}`}{' '}
                • {translatePropertyType(lead.property_type, i18n.language) || 'Residential'} • {translateRoofType(lead.roof_type, i18n.language) || 'Standard'}
              </Text>
              <Text size="xs" fw={500} c="dark.3">
                📞 {lead.phone_display || lead.phone_e164 || lead.phone}
              </Text>
            </div>
            <Badge color={isOverdue ? 'red' : 'yellow'} variant="light">
              {translateStatus(lead.status, i18n.language)}
            </Badge>
          </Group>

          <Paper p="xs" bg={isOverdue ? 'var(--mantine-color-red-0)' : 'var(--mantine-color-yellow-0)'} radius="sm">
            <Group gap="xs">
              <IconClock size={16} color={isOverdue ? 'red' : '#fab005'} />
              <Text size="xs" fw={600} c={isOverdue ? 'red.9' : 'yellow.9'}>
                {isOverdue ? t('overdue_followup', 'Overdue Follow-up') : t('scheduled_followup', 'Scheduled Follow-up')}:{' '}
                {lead.user_next_followup_display ||
                  (lead.next_followup_at
                    ? new Date(lead.next_followup_at).toLocaleString([], {
                        dateStyle: 'medium',
                        timeStyle: 'short',
                      })
                    : 'Not set')}
              </Text>
            </Group>
            {lead.next_action && (
              <Text size="xs" mt={2} c="dimmed">
                <strong>{t('next_action_label', 'Next Action:')}</strong> {lead.next_action}
              </Text>
            )}
          </Paper>

          <Group justify="space-between" mt="xs" wrap="wrap">
            <Group gap="xs">
              {canCall ? (
                <Button
                  component="a"
                  href={lead.tel_url || `tel:${cleanPhone}`}
                  size="xs"
                  variant="light"
                  color="blue"
                  leftSection={<IconPhone size={14} />}
                >
                  {t('actions.call', 'Call')}
                </Button>
              ) : (
                <Tooltip label={lead.do_not_contact ? 'Do Not Contact active' : 'Call opted out'}>
                  <span>
                    <Button
                      size="xs"
                      variant="light"
                      color="gray"
                      disabled
                      leftSection={<IconPhone size={14} />}
                    >
                      {t('actions.call', 'Call')}
                    </Button>
                  </span>
                </Tooltip>
              )}

              {/* Show WhatsApp for India or where permitted */}
              {!isAU && (
                canWhatsApp ? (
                  <Button
                    component="a"
                    href={
                      lead.whatsapp_url ||
                      `https://wa.me/${cleanPhone.replace(/\D/g, '')}?text=${encodeURIComponent(
                        `Namaste ${lead.name}! Calling regarding your rooftop solar inquiry.`
                      )}`
                    }
                    target="_blank"
                    size="xs"
                    variant="light"
                    color="green"
                    leftSection={<IconBrandWhatsapp size={14} />}
                  >
                    {t('actions.whatsapp', 'WhatsApp')}
                  </Button>
                ) : (
                  <Tooltip label={lead.do_not_contact ? 'Do Not Contact active' : 'WhatsApp opted out'}>
                    <span>
                      <Button
                        size="xs"
                        variant="light"
                        color="gray"
                        disabled
                        leftSection={<IconBrandWhatsapp size={14} />}
                      >
                        {t('actions.whatsapp', 'WhatsApp')}
                      </Button>
                    </span>
                  </Tooltip>
                )
              )}

              {/* Show SMS for Australia */}
              {isAU && (
                canSMS ? (
                  <Button
                    component="a"
                    href={`sms:${cleanPhone}`}
                    size="xs"
                    variant="light"
                    color="cyan"
                    leftSection={<IconMessage size={14} />}
                  >
                    {t('actions.sms', 'SMS')}
                  </Button>
                ) : (
                  <Tooltip label={lead.do_not_contact ? 'Do Not Contact active' : 'SMS opted out'}>
                    <span>
                      <Button
                        size="xs"
                        variant="light"
                        color="gray"
                        disabled
                        leftSection={<IconMessage size={14} />}
                      >
                        {t('actions.sms', 'SMS')}
                      </Button>
                    </span>
                  </Tooltip>
                )
              )}
            </Group>

            <Group gap="xs">
              <Button
                size="xs"
                variant="light"
                color="gray"
                leftSection={<IconNotes size={14} />}
                onClick={() => {
                  setSelectedLead(lead);
                  setRemarkModalOpen(true);
                }}
              >
                {t('actions.remark', 'Remark')}
              </Button>
              <Button
                size="xs"
                color="yellow"
                leftSection={<IconClipboardCheck size={14} />}
                onClick={() => handleOpenOutcome(lead)}
              >
                {t('actions.log_outcome', 'Log Outcome')}
              </Button>
              <ActionIcon
                variant="subtle"
                color="gray"
                onClick={() => navigate(`/leads/${lead.id}`)}
                title={t('actions.view_full_lead', 'View full lead')}
              >
                <IconArrowRight size={16} />
              </ActionIcon>
            </Group>
          </Group>
        </Stack>
      </Card>
    );
  };

  return (
    <Container size="xl" py="md">
      <Stack gap="lg">
        <Group justify="space-between" align="center">
          <div>
            <Group gap="xs">
              <ThemeIcon size="lg" radius="md" color="yellow" variant="light">
                <IconCalendarEvent size={22} />
              </ThemeIcon>
              <div>
                <Title order={3}>{t('title', "Today's Follow-up Queue")}</Title>
                <Text size="xs" c="dimmed">
                  {t('subtitle', 'Calls, meetings, and surveys due today and overdue for follow-up')}
                </Text>
              </div>
            </Group>
          </div>
          <Badge size="lg" color="yellow" variant="filled">
            {t('total_due', { count: leads.length, defaultValue: `${leads.length} Total Due` })}
          </Badge>
        </Group>

        {isLoading ? (
          <Center py="xl">
            <Loader color="yellow" />
          </Center>
        ) : isError ? (
          <Alert icon={<IconAlertTriangle size={16} />} title="Error" color="red">
            Failed to load follow-up leads.
          </Alert>
        ) : leads.length === 0 ? (
          <Paper p="xl" withBorder radius="md" ta="center">
            <ThemeIcon size={48} radius="xl" color="green" variant="light" mx="auto" mb="sm">
              <IconCheck size={28} />
            </ThemeIcon>
            <Title order={4} mb="xs">
              {t('all_caught_up', 'All caught up for today!')}
            </Title>
            <Text size="sm" c="dimmed" mb="md">
              {t('no_pending', 'You have no pending or overdue follow-ups right now.')}
            </Text>
            <Button variant="light" color="yellow" onClick={() => navigate('/leads')}>
              {t('browse_leads', 'Browse All Leads')}
            </Button>
          </Paper>
        ) : (
          <Stack gap="xl">
            {overdueLeads.length > 0 && (
              <div>
                <Group gap="xs" mb="sm">
                  <Badge color="red" size="md">
                    {t('overdue_badge', { count: overdueLeads.length, defaultValue: `${overdueLeads.length} OVERDUE` })}
                  </Badge>
                  <Text size="xs" c="dimmed">
                    {t('immediate_action', 'Immediate action recommended')}
                  </Text>
                </Group>
                <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
                  {overdueLeads.map((l) => renderLeadCard(l, true))}
                </SimpleGrid>
              </div>
            )}

            {dueTodayLeads.length > 0 && (
              <div>
                <Group gap="xs" mb="sm">
                  <Badge color="yellow" size="md">
                    {t('due_today_badge', { count: dueTodayLeads.length, defaultValue: `${dueTodayLeads.length} DUE TODAY` })}
                  </Badge>
                  <Text size="xs" c="dimmed">
                    {t('scheduled_today', 'Scheduled for today')}
                  </Text>
                </Group>
                <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
                  {dueTodayLeads.map((l) => renderLeadCard(l, false))}
                </SimpleGrid>
              </div>
            )}
          </Stack>
        )}
      </Stack>

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
