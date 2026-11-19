import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
  SegmentedControl,
  Switch,
  SimpleGrid,
  ThemeIcon,
  Loader,
  Center,
  Paper,
  Divider,
} from '@mantine/core';
import {
  IconClipboardCheck,
  IconCalendar,
  IconCheck,
  IconCalendarTime,
} from '@tabler/icons-react';
import { fetchSurveys, markSurveyMissed } from '../api/client';
import { useTranslation } from 'react-i18next';
import { translateStatus } from '../i18n/formatters';
import { useAuth } from '../context/AuthContext';
import { RescheduleSurveyModal } from '../components/modals/RescheduleSurveyModal';
import { MarkDoneSurveyModal } from '../components/modals/MarkDoneSurveyModal';
import type { Survey } from '../api/types';

export const SurveysPage: React.FC = () => {
  const { t, i18n } = useTranslation(['surveys', 'common', 'leads']);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, isSurveyor } = useAuth();

  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [mySurveysOnly, setMySurveysOnly] = useState<boolean>(isSurveyor);
  const [selectedSurvey, setSelectedSurvey] = useState<Survey | null>(null);
  const [rescheduleModalOpen, setRescheduleModalOpen] = useState(false);
  const [markDoneModalOpen, setMarkDoneModalOpen] = useState(false);

  const { data: surveys = [], isLoading, refetch } = useQuery<Survey[]>({
    queryKey: ['surveys', { status: statusFilter, my: mySurveysOnly }],
    queryFn: () => {
      const params: Record<string, any> = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      if (mySurveysOnly && user) params.surveyor = user.id;
      return fetchSurveys(params);
    },
  });

  const missedMutation = useMutation({
    mutationFn: (id: number) => markSurveyMissed(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
    },
  });


  const getStatusColor = (status: string) => {
    switch (status) {
      case 'done':
        return 'green';
      case 'booked':
        return 'blue';
      case 'rescheduled':
        return 'orange';
      case 'missed':
      case 'cancelled':
        return 'red';
      default:
        return 'gray';
    }
  };

  return (
    <Container size="xl" py="md">
      <Stack gap="lg">
        {/* Header */}
        <Group justify="space-between" align="center">
          <div>
            <Group gap="xs">
              <ThemeIcon size="lg" radius="md" color="teal" variant="light">
                <IconClipboardCheck size={22} />
              </ThemeIcon>
              <div>
                <Title order={3}>{t('title', 'Site Surveys Hub')}</Title>
                <Text size="xs" c="dimmed">
                  {t('subtitle', 'Manage technical site assessments, scheduling, and roof suitability reports')}
                </Text>
              </div>
            </Group>
          </div>

          <Group gap="md">
            <Switch
              label={t('my_surveys_only', 'My Surveys Only')}
              checked={mySurveysOnly}
              onChange={(e) => setMySurveysOnly(e.currentTarget.checked)}
              color="teal"
            />
          </Group>
        </Group>

        {/* Filter Bar */}
        <Paper p="xs" withBorder radius="md">
          <Group justify="space-between">
            <SegmentedControl
              value={statusFilter}
              onChange={setStatusFilter}
              color="teal"
              size="xs"
              data={[
                { label: t('status.all', 'All'), value: 'all' },
                { label: t('status.booked', 'Booked'), value: 'booked' },
                { label: t('status.rescheduled', 'Rescheduled'), value: 'rescheduled' },
                { label: t('status.done', 'Done'), value: 'done' },
                { label: t('status.missed', 'Missed'), value: 'missed' },
                { label: t('status.cancelled', 'Cancelled'), value: 'cancelled' },
              ]}
            />
            <Text size="xs" c="dimmed">
              {t('showing_count', { count: surveys.length, defaultValue: `Showing ${surveys.length} surveys` })}
            </Text>
          </Group>
        </Paper>

        {/* Surveys Content */}
        {isLoading ? (
          <Center py="xl">
            <Loader color="teal" />
          </Center>
        ) : surveys.length === 0 ? (
          <Paper p="xl" withBorder radius="md" ta="center">
            <Text size="sm" c="dimmed">
              {t('empty', 'No site surveys found matching current criteria.')}
            </Text>
          </Paper>
        ) : (
          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
            {surveys.map((survey) => {
              return (
                <Card
                  key={survey.id}
                  shadow="sm"
                  padding="md"
                  radius="md"
                  withBorder
                  style={{
                    borderLeft: `4px solid var(--mantine-color-${getStatusColor(survey.status)}-6)`,
                  }}
                >
                  <Stack gap="xs">
                    <Group justify="space-between" align="flex-start">
                      <div>
                        <Group gap="xs">
                          <Text
                            fw={600}
                            size="md"
                            style={{ cursor: 'pointer' }}
                            c="teal.9"
                            onClick={() => navigate(`/leads/${survey.lead}`)}
                          >
                            {survey.lead_name || `Lead #${survey.lead}`}
                          </Text>
                          <Badge size="xs" color="gray">
                            Survey #{survey.id}
                          </Badge>
                        </Group>
                        <Text size="xs" c="dimmed">
                          {t('fields.surveyor', 'Surveyor')}: <strong>{survey.surveyor_name || t('common:fields.unassigned', 'Unassigned')}</strong>
                        </Text>
                      </div>

                      <Badge color={getStatusColor(survey.status)} variant="filled">
                        {translateStatus(survey.status, i18n.language).toUpperCase()}
                      </Badge>
                    </Group>

                    <Paper p="xs" bg="var(--mantine-color-gray-0)" radius="sm">
                      <Group gap="xs">
                        <IconCalendar size={16} color="teal" />
                        <Text size="xs" fw={600}>
                          {t('scheduled_for', {
                            date: new Date(survey.scheduled_at).toLocaleString([], {
                              dateStyle: 'medium',
                              timeStyle: 'short',
                            }),
                            defaultValue: `Scheduled for: ${new Date(survey.scheduled_at).toLocaleString([], {
                              dateStyle: 'medium',
                              timeStyle: 'short',
                            })}`
                          })}
                        </Text>
                      </Group>
                      {survey.reschedule_count > 0 && (
                        <Text size="10px" c="orange" mt={2}>
                          {t('rescheduled_times', { count: survey.reschedule_count, defaultValue: `Rescheduled ${survey.reschedule_count} times` })}
                        </Text>
                      )}
                      {survey.notes && (
                        <Text size="xs" c="dimmed" mt={4}>
                          <strong>{t('fields.notes', 'Notes')}:</strong> {survey.notes}
                        </Text>
                      )}
                    </Paper>

                    {survey.status === 'done' && (
                      <Group gap="xs">
                        <Text size="xs" fw={500}>
                          {t('fields.site_suitable', 'Roof Suitability')}:
                        </Text>
                        {survey.site_suitable ? (
                          <Badge color="green" size="sm">
                            {t('fields.yes', 'Suitable for Solar')}
                          </Badge>
                        ) : (
                          <Badge color="red" size="sm">
                            {t('fields.no', 'Unsuitable (Lead Closed)')}
                          </Badge>
                        )}
                      </Group>
                    )}

                    <Divider mt="xs" />

                    <Group justify="space-between" align="center">
                      <Button
                        size="xs"
                        variant="subtle"
                        color="gray"
                        onClick={() => navigate(`/leads/${survey.lead}`)}
                      >
                        {t('leads:actions.details', 'View Lead Details')}
                      </Button>

                      {(survey.status === 'booked' || survey.status === 'rescheduled') && (
                        <Group gap="xs">
                          <Button
                            size="xs"
                            color="green"
                            variant="filled"
                            leftSection={<IconCheck size={14} />}
                            onClick={() => {
                              setSelectedSurvey(survey);
                              setMarkDoneModalOpen(true);
                            }}
                          >
                            {t('actions.mark_done', 'Mark Done')}
                          </Button>
                          <Button
                            size="xs"
                            color="orange"
                            variant="light"
                            leftSection={<IconCalendarTime size={14} />}
                            onClick={() => {
                              setSelectedSurvey(survey);
                              setRescheduleModalOpen(true);
                            }}
                          >
                            {t('actions.reschedule', 'Reschedule')}
                          </Button>
                          <Button
                            size="xs"
                            color="red"
                            variant="subtle"
                            onClick={() => missedMutation.mutate(survey.id)}
                          >
                            {t('actions.mark_missed', 'Missed')}
                          </Button>
                        </Group>
                      )}
                    </Group>
                  </Stack>
                </Card>
              );
            })}
          </SimpleGrid>
        )}
      </Stack>

      {/* Modals */}
      <RescheduleSurveyModal
        opened={rescheduleModalOpen}
        onClose={() => {
          setRescheduleModalOpen(false);
          setSelectedSurvey(null);
        }}
        survey={selectedSurvey}
        onSuccess={() => refetch()}
      />

      <MarkDoneSurveyModal
        opened={markDoneModalOpen}
        onClose={() => {
          setMarkDoneModalOpen(false);
          setSelectedSurvey(null);
        }}
        survey={selectedSurvey}
        onSuccess={() => refetch()}
      />
    </Container>
  );
};
