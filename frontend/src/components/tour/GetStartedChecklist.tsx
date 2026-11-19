import React, { useState, useEffect } from 'react';
import {
  Card,
  Group,
  Stack,
  Text,
  Progress,
  Checkbox,
  ActionIcon,
  Collapse,
  Button,
  ThemeIcon,
  Badge,
} from '@mantine/core';
import {
  IconChecklist,
  IconChevronDown,
  IconChevronUp,
  IconArrowRight,
  IconX,
  IconCheck,
} from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { startTour } from './ProductTourService';
import {
  fetchOnboardingState,
  dismissOnboarding,
  toggleCollapseOnboarding,
  recordOnboardingEvent,
  type OnboardingState,
} from '../../api/client';

interface GetStartedChecklistProps {
  userRole?: string;
  hasSeenTour?: boolean;
  onOpenTourCenter: () => void;
}

export const GetStartedChecklist: React.FC<GetStartedChecklistProps> = ({
  userRole = 'salesperson',
  onOpenTourCenter,
}) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [state, setState] = useState<OnboardingState | null>(null);
  const [showAllDone, setShowAllDone] = useState(false);
  const [opened, setOpened] = useState(true);

  const syncState = async () => {
    try {
      const res = await fetchOnboardingState();
      setState(res);
      setOpened(!res.is_collapsed);
      if (res.just_completed) {
        setShowAllDone(true);
        setTimeout(() => {
          setState(prev => prev ? { ...prev, visible: false } : null);
          setShowAllDone(false);
        }, 3000);
      }
    } catch {
      // In case of error, fail safe and don't block dashboard
      setState(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    syncState();
  }, [userRole]);

  // Rule 4: No flicker. While loading or if latched/hidden, render nothing.
  if (loading || !state) return null;
  if (!state.visible && !showAllDone) return null;

  const items = state.items || [];
  const completedCount = items.filter(i => i.done).length;
  const progressPercent = items.length > 0 ? Math.round((completedCount / items.length) * 100) : 100;

  const handleDismiss = async () => {
    try {
      const res = await dismissOnboarding();
      setState(res);
    } catch {
      setState(prev => prev ? { ...prev, visible: false } : null);
    }
  };

  const handleCollapseToggle = async () => {
    const nextOpened = !opened;
    setOpened(nextOpened);
    try {
      await toggleCollapseOnboarding(!nextOpened);
    } catch {
      // ignore
    }
  };

  const handleItemAction = async (itemId: string) => {
    if (itemId === 'tour') {
      startTour('complete', () => {
        syncState();
      });
      return;
    }

    try {
      const res = await recordOnboardingEvent(itemId);
      setState(res);
      if (res.just_completed || (!res.visible && res.completed_at)) {
        setShowAllDone(true);
        setTimeout(() => {
          setState(prev => prev ? { ...prev, visible: false } : null);
          setShowAllDone(false);
        }, 3000);
      }
    } catch {
      // ignore
    }

    if (itemId === 'leads') {
      navigate('/leads');
    } else if (itemId === 'quote') {
      navigate('/quotes');
    } else if (itemId === 'surveys') {
      navigate('/surveys');
    } else if (itemId === 'tour_center') {
      onOpenTourCenter();
    }
  };

  if (showAllDone) {
    return (
      <Card
        withBorder
        radius="md"
        padding="md"
        mb="md"
        data-testid="onboarding-card"
        data-tour="dashboard-checklist"
        style={{ borderColor: '#22c55e', background: '#f0fdf4', transition: 'all 0.3s ease' }}
      >
        <Group justify="space-between" align="center">
          <Group gap="sm">
            <ThemeIcon size="lg" color="teal" variant="filled" radius="xl">
              <IconCheck size={20} />
            </ThemeIcon>
            <div>
              <Text fw={700} size="sm" c="teal.9">
                All done! Getting Started checklist completed 🎉
              </Text>
              <Text size="xs" c="teal.7">
                You're ready to maximize your solar pipeline and close more deals.
              </Text>
            </div>
          </Group>
          <Badge size="sm" color="teal" variant="filled">
            Completed
          </Badge>
        </Group>
      </Card>
    );
  }

  return (
    <Card
      withBorder
      radius="md"
      padding="md"
      mb="md"
      data-testid="onboarding-card"
      data-tour="dashboard-checklist"
      style={{ borderColor: '#cbd5e1', background: '#f8fafc' }}
    >
      <Group justify="space-between" mb="xs">
        <Group gap="xs">
          <ThemeIcon size="md" color="blue" variant="filled">
            <IconChecklist size={18} />
          </ThemeIcon>
          <div>
            <Group gap="xs">
              <Text fw={700} size="sm">
                Getting Started with Solar CRM
              </Text>
              <Badge size="xs" color={progressPercent === 100 ? 'teal' : 'blue'}>
                {completedCount} of {items.length} completed
              </Badge>
            </Group>
          </div>
        </Group>

        <Group gap="xs">
          <ActionIcon
            variant="subtle"
            color="gray"
            size="sm"
            onClick={handleCollapseToggle}
            title={opened ? 'Collapse' : 'Expand'}
            aria-label="Collapse checklist"
          >
            {opened ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
          </ActionIcon>
          <ActionIcon
            variant="subtle"
            color="gray"
            size="sm"
            onClick={handleDismiss}
            title="Dismiss"
            aria-label="Dismiss checklist"
          >
            <IconX size={16} />
          </ActionIcon>
        </Group>
      </Group>

      <Progress value={progressPercent} size="sm" radius="xl" color="blue" mb="sm" />

      <Collapse expanded={opened}>
        <Stack gap="xs" mt="sm">
          {items.map(item => (
            <Group key={item.id} justify="space-between" wrap="nowrap">
              <Group gap="xs" wrap="nowrap">
                <Checkbox
                  checked={item.done}
                  readOnly
                  color="blue"
                  size="xs"
                />
                <Text
                  size="xs"
                  style={{
                    textDecoration: item.done ? 'line-through' : 'none',
                    color: item.done ? '#94a3b8' : '#334155',
                  }}
                >
                  {item.label}
                </Text>
              </Group>

              <Button
                size="compact-xs"
                variant="subtle"
                color="blue"
                rightSection={<IconArrowRight size={10} />}
                onClick={() => handleItemAction(item.id)}
              >
                {item.id === 'tour'
                  ? 'Start Tour'
                  : item.id === 'leads'
                  ? 'Open Leads'
                  : item.id === 'quote'
                  ? 'Open Quotes'
                  : item.id === 'surveys'
                  ? 'View Surveys'
                  : 'Tour Center'}
              </Button>
            </Group>
          ))}
        </Stack>
      </Collapse>
    </Card>
  );
};
