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
} from '@mantine/core';
import {
  IconCalendarEvent,
  IconPhone,
  IconBrandWhatsapp,
  IconClipboardCheck,
  IconAlertTriangle,
  IconCheck,
  IconArrowRight,
  IconClock,
} from '@tabler/icons-react';
import { fetchTodayLeads } from '../api/client';
import { LogOutcomeModal } from '../components/modals/LogOutcomeModal';
import type { Lead } from '../api/types';

export const TodayPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [outcomeModalOpen, setOutcomeModalOpen] = useState(false);

  const { data: leads = [], isLoading, isError, refetch } = useQuery<Lead[]>({
    queryKey: ['today-leads'],
    queryFn: fetchTodayLeads,
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

  const getCleanPhone = (phone: string) => {
    return phone.replace(/\D/g, '').slice(-10);
  };

  const renderLeadCard = (lead: Lead, isOverdue: boolean) => (
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
            <Group gap="xs">
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
            </Group>
            <Text size="xs" c="dimmed">
              {lead.city} • {lead.property_type || 'Residential'} • {lead.roof_type || 'RCC'}
            </Text>
          </div>
          <Badge color={isOverdue ? 'red' : 'yellow'} variant="light">
            {lead.status}
          </Badge>
        </Group>

        <Paper p="xs" bg={isOverdue ? 'var(--mantine-color-red-0)' : 'var(--mantine-color-yellow-0)'} radius="sm">
          <Group gap="xs">
            <IconClock size={16} color={isOverdue ? 'red' : '#fab005'} />
            <Text size="xs" fw={600} c={isOverdue ? 'red.9' : 'yellow.9'}>
              {isOverdue ? 'Overdue Follow-up' : 'Scheduled Follow-up'}:{' '}
              {lead.next_followup_at
                ? new Date(lead.next_followup_at).toLocaleString([], {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })
                : 'Not set'}
            </Text>
          </Group>
          {lead.next_action && (
            <Text size="xs" mt={2} c="dimmed">
              <strong>Next Action:</strong> {lead.next_action}
            </Text>
          )}
        </Paper>

        <Group justify="space-between" mt="xs">
          <Group gap="xs">
            <Button
              component="a"
              href={`tel:${lead.phone}`}
              size="xs"
              variant="light"
              color="blue"
              leftSection={<IconPhone size={14} />}
            >
              Call
            </Button>
            <Button
              component="a"
              href={`https://wa.me/91${getCleanPhone(lead.phone)}?text=${encodeURIComponent(
                `Namaste ${lead.name}! Calling regarding your rooftop solar inquiry.`
              )}`}
              target="_blank"
              size="xs"
              variant="light"
              color="green"
              leftSection={<IconBrandWhatsapp size={14} />}
            >
              WhatsApp
            </Button>
          </Group>

          <Group gap="xs">
            <Button
              size="xs"
              color="yellow"
              leftSection={<IconClipboardCheck size={14} />}
              onClick={() => handleOpenOutcome(lead)}
            >
              Log Outcome
            </Button>
            <ActionIcon
              variant="subtle"
              color="gray"
              onClick={() => navigate(`/leads/${lead.id}`)}
              title="View full lead"
            >
              <IconArrowRight size={16} />
            </ActionIcon>
          </Group>
        </Group>
      </Stack>
    </Card>
  );

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
                <Title order={3}>Today's Follow-up Queue</Title>
                <Text size="xs" c="dimmed">
                  Calls, meetings, and surveys due today and overdue for follow-up
                </Text>
              </div>
            </Group>
          </div>
          <Badge size="lg" color="yellow" variant="filled">
            {leads.length} Total Due
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
              All caught up for today!
            </Title>
            <Text size="sm" c="dimmed" mb="md">
              You have no pending or overdue follow-ups right now.
            </Text>
            <Button variant="light" color="yellow" onClick={() => navigate('/leads')}>
              Browse All Leads
            </Button>
          </Paper>
        ) : (
          <Stack gap="xl">
            {overdueLeads.length > 0 && (
              <div>
                <Group gap="xs" mb="sm">
                  <Badge color="red" size="md">
                    {overdueLeads.length} OVERDUE
                  </Badge>
                  <Text size="xs" c="dimmed">
                    Immediate action recommended
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
                    {dueTodayLeads.length} DUE TODAY
                  </Badge>
                  <Text size="xs" c="dimmed">
                    Scheduled for today
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
    </Container>
  );
};
