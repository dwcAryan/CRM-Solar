import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Container,
  Title,
  Text,
  SimpleGrid,
  Paper,
  Group,
  Stack,
  ThemeIcon,
  Badge,
  Progress,
  Button,
  Loader,
  Alert,
  Card,
} from '@mantine/core';
import {
  IconClockExclamation,
  IconTrophy,
  IconUsers,
  IconAlertTriangle,
  IconTrendingUp,
} from '@tabler/icons-react';
import { fetchDashboard } from '../api/client';
import type { DashboardData } from '../api/types';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();

  const { data, isLoading, error, refetch } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: fetchDashboard,
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <Container size="xl" py="xl">
        <Group justify="center" p="xl">
          <Loader size="lg" color="yellow" />
          <Text size="sm" c="dimmed">
            Loading sales dashboard...
          </Text>
        </Group>
      </Container>
    );
  }

  if (error || !data) {
    return (
      <Container size="xl" py="xl">
        <Alert icon={<IconAlertTriangle size={16} />} title="Error loading dashboard" color="red">
          {(error as Error)?.message || 'Failed to load metrics.'}
          <Button size="xs" variant="light" color="red" mt="xs" onClick={() => refetch()}>
            Retry
          </Button>
        </Alert>
      </Container>
    );
  }

  const funnelTotal =
    data.funnel.new +
    data.funnel.interested +
    data.funnel.survey +
    data.funnel.quote_sent +
    data.funnel.won || 1;

  return (
    <Container size="xl" py="sm">
      <Stack gap="lg">
        <Group justify="space-between" align="center">
          <div>
            <Title order={2}>Sales Overview</Title>
            <Text size="xs" c="dimmed">
              Real-time pipeline metrics & conversion status
            </Text>
          </div>
          <Button
            leftSection={<IconClockExclamation size={16} />}
            color={data.overdue_followups > 0 ? 'red' : 'yellow'}
            variant={data.overdue_followups > 0 ? 'filled' : 'light'}
            onClick={() => navigate('/today')}
          >
            {data.overdue_followups} Overdue Follow-ups
          </Button>
        </Group>

        {/* Top KPI Cards */}
        <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={600} tt="uppercase">
                  Active Leads
                </Text>
                <Title order={3} mt={4}>
                  {data.total_active_leads}
                </Title>
              </div>
              <ThemeIcon size={44} radius="md" color="yellow" variant="light">
                <IconUsers size={24} />
              </ThemeIcon>
            </Group>
            <Text size="xs" c="dimmed" mt="xs">
              Excluding terminal statuses
            </Text>
          </Paper>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={600} tt="uppercase">
                  Overdue Follow-ups
                </Text>
                <Title order={3} mt={4} c={data.overdue_followups > 0 ? 'red' : 'green'}>
                  {data.overdue_followups}
                </Title>
              </div>
              <ThemeIcon size={44} radius="md" color={data.overdue_followups > 0 ? 'red' : 'green'} variant="light">
                <IconClockExclamation size={24} />
              </ThemeIcon>
            </Group>
            <Text size="xs" c="dimmed" mt="xs">
              Action urgently required
            </Text>
          </Paper>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={600} tt="uppercase">
                  Deals Won This Month
                </Text>
                <Title order={3} mt={4} c="teal">
                  {data.won_this_month}
                </Title>
              </div>
              <ThemeIcon size={44} radius="md" color="teal" variant="light">
                <IconTrophy size={24} />
              </ThemeIcon>
            </Group>
            <Text size="xs" c="dimmed" mt="xs">
              Agreed proposals
            </Text>
          </Paper>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={600} tt="uppercase">
                  Quotes in Negotiation
                </Text>
                <Title order={3} mt={4} c="blue">
                  {data.funnel.quote_sent}
                </Title>
              </div>
              <ThemeIcon size={44} radius="md" color="blue" variant="light">
                <IconTrendingUp size={24} />
              </ThemeIcon>
            </Group>
            <Text size="xs" c="dimmed" mt="xs">
              Quote sent / Revising / Neg.
            </Text>
          </Paper>
        </SimpleGrid>

        {/* Conversion Funnel */}
        <Paper withBorder p="md" radius="md">
          <Title order={4} mb="xs">
            Solar Sales Funnel
          </Title>
          <Text size="xs" c="dimmed" mb="md">
            Pipeline progress from first inquiry to contract Won
          </Text>

          <SimpleGrid cols={{ base: 1, sm: 5 }} spacing="sm">
            <Card withBorder padding="xs" radius="sm">
              <Text size="xs" c="dimmed">
                1. New Leads
              </Text>
              <Title order={3}>{data.funnel.new}</Title>
              <Progress value={(data.funnel.new / funnelTotal) * 100} color="gray" size="sm" mt="xs" />
            </Card>

            <Card withBorder padding="xs" radius="sm">
              <Text size="xs" c="dimmed">
                2. Interested
              </Text>
              <Title order={3}>{data.funnel.interested}</Title>
              <Progress value={(data.funnel.interested / funnelTotal) * 100} color="yellow" size="sm" mt="xs" />
            </Card>

            <Card withBorder padding="xs" radius="sm">
              <Text size="xs" c="dimmed">
                3. Site Survey
              </Text>
              <Title order={3}>{data.funnel.survey}</Title>
              <Progress value={(data.funnel.survey / funnelTotal) * 100} color="indigo" size="sm" mt="xs" />
            </Card>

            <Card withBorder padding="xs" radius="sm">
              <Text size="xs" c="dimmed">
                4. Quote Sent
              </Text>
              <Title order={3}>{data.funnel.quote_sent}</Title>
              <Progress value={(data.funnel.quote_sent / funnelTotal) * 100} color="blue" size="sm" mt="xs" />
            </Card>

            <Card withBorder padding="xs" radius="sm" style={{ backgroundColor: 'var(--mantine-color-teal-0)' }}>
              <Text size="xs" c="teal" fw={600}>
                5. Won 🎉
              </Text>
              <Title order={3} c="teal">
                {data.funnel.won}
              </Title>
              <Progress value={(data.funnel.won / funnelTotal) * 100} color="teal" size="sm" mt="xs" />
            </Card>
          </SimpleGrid>
        </Paper>

        {/* Status Distribution & Lead Sources */}
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
          {/* Status Breakdown */}
          <Paper withBorder p="md" radius="md">
            <Title order={4} mb="md">
              Lead Status Distribution
            </Title>
            <Stack gap="xs">
              {Object.entries(data.status_counts).map(([statusName, count]) => (
                <Group key={statusName} justify="space-between">
                  <Badge variant="light" color={statusName === 'Won' ? 'teal' : statusName === 'Lost' ? 'gray' : 'yellow'}>
                    {statusName}
                  </Badge>
                  <Text size="sm" fw={600}>
                    {count}
                  </Text>
                </Group>
              ))}
            </Stack>
          </Paper>

          {/* Lead Sources Breakdown */}
          <Paper withBorder p="md" radius="md">
            <Title order={4} mb="md">
              Leads by Marketing Source
            </Title>
            <Stack gap="xs">
              {data.leads_per_source.map((s) => (
                <Group key={s.source} justify="space-between">
                  <Text size="sm">{s.source}</Text>
                  <Badge color="blue" variant="filled">
                    {s.count}
                  </Badge>
                </Group>
              ))}
            </Stack>
          </Paper>
        </SimpleGrid>
      </Stack>
    </Container>
  );
};
