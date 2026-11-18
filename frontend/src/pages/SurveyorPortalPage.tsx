import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Container,
  Title,
  Text,
  Tabs,
  Badge,
  Card,
  Group,
  Stack,
  Button,
  ActionIcon,
  Modal,
  Textarea,
  TextInput,
  Switch,
  FileInput,
  Paper,
  Loader,
  Center,
  SimpleGrid,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconPhone,
  IconMapPin,
  IconCheck,
  IconX,
  IconCalendar,
  IconCamera,
  IconRefresh,
} from '@tabler/icons-react';
import {
  fetchMySurveys,
  markSurveyDone,
  markSurveyMissed,
  rescheduleSurvey,
  uploadSurveyPhoto,
} from '../api/client';
import type { Survey } from '../api/types';

export const SurveyorPortalPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<string | null>('today');

  // Complete survey modal state
  const [completeSurveyModal, setCompleteSurveyModal] = useState<Survey | null>(null);
  const [siteSuitable, setSiteSuitable] = useState<boolean>(true);
  const [completeNotes, setCompleteNotes] = useState<string>('');
  const [photoFile, setPhotoFile] = useState<File | null>(null);

  // Reschedule survey modal state
  const [rescheduleModal, setRescheduleModal] = useState<Survey | null>(null);
  const [rescheduleDate, setRescheduleDate] = useState<string>('');
  const [rescheduleNotes, setRescheduleNotes] = useState<string>('');

  const { data: surveysData, isLoading, refetch } = useQuery({
    queryKey: ['my-surveys', tab],
    queryFn: () => fetchMySurveys({ filter: tab || 'today' }),
  });

  const surveys: Survey[] = Array.isArray(surveysData)
    ? surveysData
    : (surveysData as any)?.results || [];

  const completeMutation = useMutation({
    mutationFn: async ({
      surveyId,
      site_suitable,
      notes,
      file,
    }: {
      surveyId: number;
      site_suitable: boolean;
      notes: string;
      file: File | null;
    }) => {
      const res = await markSurveyDone(surveyId, { site_suitable, notes });
      if (file) {
        await uploadSurveyPhoto(surveyId, file, 'Site inspection photo');
      }
      return res;
    },
    onSuccess: () => {
      notifications.show({ title: 'Success', message: 'Survey inspection submitted.', color: 'green' });
      setCompleteSurveyModal(null);
      setPhotoFile(null);
      setCompleteNotes('');
      queryClient.invalidateQueries({ queryKey: ['my-surveys'] });
    },
    onError: (err: any) => {
      notifications.show({ title: 'Error', message: err?.message || 'Failed to submit survey.', color: 'red' });
    },
  });

  const markMissedMutation = useMutation({
    mutationFn: ({ surveyId, notes }: { surveyId: number; notes: string }) =>
      markSurveyMissed(surveyId, notes),
    onSuccess: () => {
      notifications.show({ title: 'Survey Missed', message: 'Status recorded. Sales will follow up.', color: 'orange' });
      queryClient.invalidateQueries({ queryKey: ['my-surveys'] });
    },
  });

  const rescheduleMutation = useMutation({
    mutationFn: ({ surveyId, scheduled_at, notes }: { surveyId: number; scheduled_at: string; notes: string }) =>
      rescheduleSurvey(surveyId, { scheduled_at, notes }),
    onSuccess: () => {
      notifications.show({ title: 'Rescheduled', message: 'New survey time confirmed.', color: 'blue' });
      setRescheduleModal(null);
      queryClient.invalidateQueries({ queryKey: ['my-surveys'] });
    },
  });

  return (
    <Container size="md" py="md">
      <Group justify="space-between" mb="md">
        <div>
          <Title order={2}>Field Surveyor Portal</Title>
          <Text size="sm" c="dimmed">
            Your assigned site inspections, property notes, and direct contact tools.
          </Text>
        </div>
        <ActionIcon variant="light" size="lg" onClick={() => refetch()}>
          <IconRefresh size={18} />
        </ActionIcon>
      </Group>

      <Tabs value={tab} onChange={setTab} variant="pills" radius="md" mb="lg">
        <Tabs.List grow>
          <Tabs.Tab value="today">Today's Visits</Tabs.Tab>
          <Tabs.Tab value="upcoming">Upcoming</Tabs.Tab>
          <Tabs.Tab value="completed">Completed History</Tabs.Tab>
        </Tabs.List>
      </Tabs>

      {isLoading ? (
        <Center py="xl"><Loader /></Center>
      ) : surveys.length === 0 ? (
        <Paper withBorder p="xl" radius="md" ta="center">
          <Text c="dimmed">No surveys found in this view.</Text>
        </Paper>
      ) : (
        <Stack gap="md">
          {surveys.map((survey) => {
            const rawPhone = (survey as any).lead_phone_e164 || (survey as any).lead_phone;
            const address = [(survey as any).lead_address, (survey as any).lead_city, (survey as any).lead_pincode]
              .filter(Boolean)
              .join(', ');

            return (
              <Card key={survey.id} withBorder radius="md" p="md" shadow="xs">
                <Group justify="space-between" mb="xs">
                  <div>
                    <Text fw={700} size="lg">{survey.lead_name}</Text>
                    <Text size="xs" c="dimmed">
                      Time: <b>{new Date(survey.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</b> • {new Date(survey.scheduled_at).toLocaleDateString()}
                    </Text>
                  </div>
                  <Badge
                    color={
                      survey.status === 'done'
                        ? 'green'
                        : survey.status === 'missed'
                        ? 'red'
                        : 'yellow'
                    }
                  >
                    {survey.status.toUpperCase()}
                  </Badge>
                </Group>

                <Group gap="xs" mb="sm">
                  {(survey as any).lead_roof_type && (
                    <Badge variant="outline" size="sm" color="gray">
                      Roof: {(survey as any).lead_roof_type}
                    </Badge>
                  )}
                  {(survey as any).lead_property_type && (
                    <Badge variant="outline" size="sm" color="gray">
                      Property: {(survey as any).lead_property_type}
                    </Badge>
                  )}
                </Group>

                {address && (
                  <Text size="sm" c="dimmed" mb="md">
                    📍 {address}
                  </Text>
                )}

                {/* Quick Contact & Map Actions */}
                <SimpleGrid cols={{ base: 2, sm: 2 }} mb="md">
                  <Button
                    component="a"
                    href={rawPhone ? `tel:${rawPhone}` : undefined}
                    disabled={!rawPhone}
                    variant="light"
                    color="green"
                    leftSection={<IconPhone size={16} />}
                  >
                    Call Customer
                  </Button>
                  <Button
                    component="a"
                    href={address ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}` : undefined}
                    target="_blank"
                    rel="noopener noreferrer"
                    disabled={!address}
                    variant="light"
                    color="blue"
                    leftSection={<IconMapPin size={16} />}
                  >
                    Google Maps
                  </Button>
                </SimpleGrid>

                {/* Status action buttons for active surveys */}
                {survey.status !== 'done' && (
                  <Group justify="flex-end" gap="xs">
                    <Button
                      size="xs"
                      variant="subtle"
                      color="orange"
                      leftSection={<IconX size={14} />}
                      onClick={() => markMissedMutation.mutate({ surveyId: survey.id, notes: 'Customer unreachable at site.' })}
                      loading={markMissedMutation.isPending}
                    >
                      Customer Missed
                    </Button>
                    <Button
                      size="xs"
                      variant="light"
                      color="blue"
                      leftSection={<IconCalendar size={14} />}
                      onClick={() => {
                        setRescheduleModal(survey);
                        setRescheduleDate(new Date(Date.now() + 86400000).toISOString().slice(0, 16));
                        setRescheduleNotes('');
                      }}
                    >
                      Reschedule
                    </Button>
                    <Button
                      size="xs"
                      color="green"
                      leftSection={<IconCheck size={14} />}
                      onClick={() => {
                        setCompleteSurveyModal(survey);
                        setSiteSuitable(true);
                        setCompleteNotes('');
                        setPhotoFile(null);
                      }}
                    >
                      Record Inspection
                    </Button>
                  </Group>
                )}

                {survey.status === 'done' && (
                  <Paper withBorder p="xs" radius="sm" bg="var(--mantine-color-green-0)">
                    <Text size="xs" fw={600} c="green">
                      Inspection Recorded • {survey.site_suitable ? '✅ Roof Suitable for Solar' : '❌ Roof Not Suitable'}
                    </Text>
                    {survey.notes && <Text size="xs" c="dimmed">"{survey.notes}"</Text>}
                  </Paper>
                )}
              </Card>
            );
          })}
        </Stack>
      )}

      {/* Modal: Complete Inspection */}
      <Modal
        opened={Boolean(completeSurveyModal)}
        onClose={() => setCompleteSurveyModal(null)}
        title="Complete Site Inspection"
        radius="md"
      >
        <Stack gap="md">
          <Text size="sm">
            Recording inspection outcome for <b>{completeSurveyModal?.lead_name}</b>:
          </Text>

          <Switch
            label="Is Site / Roof Suitable for Solar Installation?"
            checked={siteSuitable}
            onChange={(e) => setSiteSuitable(e.currentTarget.checked)}
            color="green"
            size="md"
          />

          <Textarea
            label="Inspection Findings & Measurements"
            placeholder="e.g. South-facing tin roof, 450 sq ft available, RCC slab strong, 3-phase connection..."
            required
            minRows={3}
            value={completeNotes}
            onChange={(e) => setCompleteNotes(e.target.value)}
          />

          <FileInput
            label="Upload Roof / Meter Photo"
            placeholder="Attach image from camera..."
            leftSection={<IconCamera size={16} />}
            accept="image/*"
            value={photoFile}
            onChange={setPhotoFile}
          />

          <Group justify="flex-end">
            <Button variant="light" color="gray" onClick={() => setCompleteSurveyModal(null)}>Cancel</Button>
            <Button
              color="green"
              loading={completeMutation.isPending}
              disabled={!completeNotes.trim()}
              onClick={() => {
                if (completeSurveyModal) {
                  completeMutation.mutate({
                    surveyId: completeSurveyModal.id,
                    site_suitable: siteSuitable,
                    notes: completeNotes,
                    file: photoFile,
                  });
                }
              }}
            >
              Submit Inspection
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Reschedule Survey */}
      <Modal
        opened={Boolean(rescheduleModal)}
        onClose={() => setRescheduleModal(null)}
        title="Reschedule Site Visit"
        radius="md"
      >
        <Stack gap="md">
          <Text size="sm">Propose new inspection time for <b>{rescheduleModal?.lead_name}</b>:</Text>
          <TextInput
            label="New Scheduled Date & Time"
            type="datetime-local"
            required
            value={rescheduleDate}
            onChange={(e) => setRescheduleDate(e.target.value)}
          />
          <Textarea
            label="Reschedule Note"
            placeholder="e.g. Customer requested weekend afternoon..."
            value={rescheduleNotes}
            onChange={(e) => setRescheduleNotes(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="light" color="gray" onClick={() => setRescheduleModal(null)}>Cancel</Button>
            <Button
              color="blue"
              loading={rescheduleMutation.isPending}
              disabled={!rescheduleDate}
              onClick={() => {
                if (rescheduleModal && rescheduleDate) {
                  rescheduleMutation.mutate({
                    surveyId: rescheduleModal.id,
                    scheduled_at: rescheduleDate,
                    notes: rescheduleNotes,
                  });
                }
              }}
            >
              Confirm Reschedule
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
};
