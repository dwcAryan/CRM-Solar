import React, { useState, useEffect } from 'react';
import {
  Drawer,
  Stack,
  Group,
  Text,
  Badge,
  Button,
  Card,
  ThemeIcon,
  Divider,
} from '@mantine/core';
import {
  IconCompass,
  IconCheck,
  IconPlayerPlay,
  IconRotateClockwise2,
  IconUsers,
  IconMapPin,
  IconFileText,
  IconUpload,
  IconSparkles,
  IconWorld,
  IconBell,
  IconSettings,
} from '@tabler/icons-react';
import { TOUR_DEFINITIONS, type TourDefinition } from '../../tours/tourDefinitions';
import { startTour } from './ProductTourService';
import { fetchTourState, resetTourState } from '../../api/client';

interface TourCenterDrawerProps {
  opened: boolean;
  onClose: () => void;
  userRole?: string;
}

const TOUR_ICONS: Record<string, React.ReactNode> = {
  complete: <IconCompass size={18} />,
  'getting-started': <IconCompass size={18} />,
  leads: <IconUsers size={18} />,
  surveys: <IconMapPin size={18} />,
  quotes: <IconFileText size={18} />,
  import: <IconUpload size={18} />,
  'ai-suggestions': <IconSparkles size={18} />,
  regions: <IconWorld size={18} />,
  notifications: <IconBell size={18} />,
  admin: <IconSettings size={18} />,
};

export const TourCenterDrawer: React.FC<TourCenterDrawerProps> = ({
  opened,
  onClose,
  userRole = 'salesperson',
}) => {
  const [completedTours, setCompletedTours] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const loadState = async () => {
    try {
      const state = await fetchTourState();
      setCompletedTours(state.completed_tours || []);
    } catch (e) {
      console.error('Failed to load tour state:', e);
    }
  };

  useEffect(() => {
    if (opened) {
      loadState();
    }
  }, [opened]);

  const handleStartTour = (tourId: string) => {
    onClose();
    setTimeout(() => {
      startTour(tourId, () => {
        loadState();
      });
    }, 250);
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await resetTourState();
      try {
        localStorage.removeItem('solar_crm_has_seen_tour');
      } catch {
        // ignore
      }
      setCompletedTours([]);
    } catch (e) {
      console.error('Failed to reset tour state:', e);
    } finally {
      setLoading(false);
    }
  };

  // Filter tours by role
  const toursList = Object.values(TOUR_DEFINITIONS).filter((t: TourDefinition) =>
    t.roles.includes(userRole)
  );

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <ThemeIcon size="md" color="blue" variant="light">
            <IconCompass size={18} />
          </ThemeIcon>
          <Text fw={700} size="md">
            Product Tour Center
          </Text>
        </Group>
      }
      position="right"
      size="md"
      padding="md"
    >
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Master the Solar CRM with interactive, step-by-step feature walkthroughs. Take a quick
          overview or explore specialized workflows below.
        </Text>

        <Stack gap="sm">
          {toursList.map((tour) => {
            const isCompleted = completedTours.includes(tour.id);
            return (
              <Card key={tour.id} withBorder padding="sm" radius="md">
                <Group justify="space-between" align="flex-start" wrap="nowrap">
                  <Group gap="xs" align="flex-start" wrap="nowrap">
                    <ThemeIcon size="md" color={isCompleted ? 'teal' : 'blue'} variant="light">
                      {TOUR_ICONS[tour.id] || <IconCompass size={18} />}
                    </ThemeIcon>
                    <div>
                      <Group gap="xs">
                        <Text fw={600} size="sm">
                          {tour.title}
                        </Text>
                        <Badge size="xs" variant="outline" color="gray">
                          {tour.duration}
                        </Badge>
                        {isCompleted && (
                          <Badge size="xs" color="teal" leftSection={<IconCheck size={10} />}>
                            Completed
                          </Badge>
                        )}
                      </Group>
                      <Text size="xs" c="dimmed" mt={2}>
                        {tour.description}
                      </Text>
                    </div>
                  </Group>

                  <Button
                    size="xs"
                    variant={isCompleted ? 'subtle' : 'light'}
                    color="blue"
                    leftSection={<IconPlayerPlay size={12} />}
                    onClick={() => handleStartTour(tour.id)}
                  >
                    {isCompleted ? 'Replay' : 'Start'}
                  </Button>
                </Group>
              </Card>
            );
          })}
        </Stack>

        <Divider my="xs" />

        <Group justify="space-between">
          <Button
            size="xs"
            variant="subtle"
            color="red"
            leftSection={<IconRotateClockwise2 size={14} />}
            loading={loading}
            onClick={handleReset}
          >
            Reset All Tours
          </Button>

          <Button size="xs" variant="default" onClick={onClose}>
            Close
          </Button>
        </Group>
      </Stack>
    </Drawer>
  );
};
