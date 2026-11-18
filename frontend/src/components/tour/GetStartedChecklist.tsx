import React, { useState } from 'react';
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
} from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { startTour } from './ProductTourService';

interface GetStartedChecklistProps {
  userRole?: string;
  hasSeenTour?: boolean;
  onOpenTourCenter: () => void;
}

interface ChecklistItem {
  id: string;
  label: string;
  actionText: string;
  action: () => void;
  done: boolean;
}

export const GetStartedChecklist: React.FC<GetStartedChecklistProps> = ({
  userRole = 'salesperson',
  hasSeenTour = false,
  onOpenTourCenter,
}) => {
  const navigate = useNavigate();
  const [opened, setOpened] = useState(true);
  const [dismissed, setDismissed] = useState(false);
  const [completedItems, setCompletedItems] = useState<Record<string, boolean>>({
    tour: hasSeenTour,
  });

  if (dismissed) return null;

  const toggleItem = (id: string) => {
    setCompletedItems(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const items: ChecklistItem[] = [
    {
      id: 'tour',
      label: 'Complete the interactive Product Tour',
      actionText: 'Start Tour',
      action: () => startTour('complete'),
      done: completedItems['tour'] || hasSeenTour,
    },
    ...(userRole === 'surveyor'
      ? [
          {
            id: 'surveys',
            label: 'Review assigned site surveys and locations',
            actionText: 'View Surveys',
            action: () => navigate('/surveys'),
            done: !!completedItems['surveys'],
          },
        ]
      : [
          {
            id: 'leads',
            label: 'Review your leads pipeline and customer details',
            actionText: 'Open Leads',
            action: () => navigate('/leads'),
            done: !!completedItems['leads'],
          },
          {
            id: 'quote',
            label: 'Create your first solar pricing proposal',
            actionText: 'Open Quotes',
            action: () => navigate('/quotes'),
            done: !!completedItems['quote'],
          },
        ]),
    {
      id: 'tour_center',
      label: 'Explore specialized workflows in the Tour Center',
      actionText: 'Tour Center',
      action: onOpenTourCenter,
      done: !!completedItems['tour_center'],
    },
  ];

  const completedCount = items.filter(i => i.done).length;
  const progressPercent = Math.round((completedCount / items.length) * 100);

  return (
    <Card
      withBorder
      radius="md"
      padding="md"
      mb="md"
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
            onClick={() => setOpened(o => !o)}
            title={opened ? 'Collapse' : 'Expand'}
          >
            {opened ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
          </ActionIcon>
          <ActionIcon
            variant="subtle"
            color="gray"
            size="sm"
            onClick={() => setDismissed(true)}
            title="Dismiss"
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
                  onChange={() => toggleItem(item.id)}
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
                onClick={item.action}
              >
                {item.actionText}
              </Button>
            </Group>
          ))}
        </Stack>
      </Collapse>
    </Card>
  );
};
