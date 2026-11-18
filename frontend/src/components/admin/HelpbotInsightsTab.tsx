import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Stack,
  Paper,
  Title,
  Text,
  Group,
  SimpleGrid,
  ThemeIcon,
  Badge,
  Button,
  Table,
  Alert,
  Loader,
  Card,
  Progress,
} from '@mantine/core';
import {
  IconSparkles,
  IconCheck,
  IconRotateClockwise2,
  IconThumbUp,
  IconBan,
  IconHelp,
} from '@tabler/icons-react';
import {
  fetchHelpbotStats,
  fetchHelpbotUnanswered,
  updateHelpbotUnanswered,
  triggerHelpbotReindex,
} from '../../api/client';
import type { HelpbotStatsResponse, HelpbotUnansweredItem } from '../../api/types';

export const HelpbotInsightsTab: React.FC = () => {
  const queryClient = useQueryClient();
  const [reindexSuccess, setReindexSuccess] = useState<string | null>(null);

  const { data: stats, isLoading: statsLoading } = useQuery<HelpbotStatsResponse>({
    queryKey: ['helpbot-stats'],
    queryFn: fetchHelpbotStats,
    refetchInterval: 30000,
  });

  const { data: unanswered = [], isLoading: unansweredLoading } = useQuery<HelpbotUnansweredItem[]>({
    queryKey: ['helpbot-unanswered'],
    queryFn: () => fetchHelpbotUnanswered(false),
    refetchInterval: 30000,
  });

  const reindexMutation = useMutation({
    mutationFn: triggerHelpbotReindex,
    onSuccess: (res) => {
      setReindexSuccess(res.message);
      queryClient.invalidateQueries({ queryKey: ['helpbot-stats'] });
      setTimeout(() => setReindexSuccess(null), 5000);
    },
  });

  const resolveMutation = useMutation({
    mutationFn: ({ id, resolved }: { id: number; resolved: boolean }) =>
      updateHelpbotUnanswered(id, resolved),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['helpbot-unanswered'] });
      queryClient.invalidateQueries({ queryKey: ['helpbot-stats'] });
    },
  });

  if (statsLoading || unansweredLoading) {
    return (
      <Paper p="xl" withBorder radius="md">
        <Group justify="center">
          <Loader size="sm" color="blue" />
          <Text size="sm" c="dimmed">
            Loading Helpbot insights & analytics...
          </Text>
        </Group>
      </Paper>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between" align="center">
        <div>
          <Title order={4}>Help Assistant Insights & Telemetry</Title>
          <Text size="xs" c="dimmed">
            Monitor real questions asked by team members, refusal rates, and identify missing knowledge
          </Text>
        </div>

        <Button
          size="xs"
          variant="light"
          color="blue"
          leftSection={<IconRotateClockwise2 size={14} />}
          loading={reindexMutation.isPending}
          onClick={() => reindexMutation.mutate()}
        >
          Rebuild Knowledge Index
        </Button>
      </Group>

      {reindexSuccess && (
        <Alert icon={<IconCheck size={16} />} title="Index Rebuilt" color="teal">
          {reindexSuccess}
        </Alert>
      )}

      {/* KPI Cards */}
      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
        <Card withBorder radius="md" padding="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Total Queries
            </Text>
            <ThemeIcon color="blue" variant="light" size="sm">
              <IconSparkles size={14} />
            </ThemeIcon>
          </Group>
          <Text fw={700} size="xl" mt="xs">
            {stats?.total_queries ?? 0}
          </Text>
          <Text size="xs" c="dimmed" mt={4}>
            Avg response time: {stats?.avg_latency_ms ?? 0} ms
          </Text>
        </Card>

        <Card withBorder radius="md" padding="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Helpful Rating
            </Text>
            <ThemeIcon color="teal" variant="light" size="sm">
              <IconThumbUp size={14} />
            </ThemeIcon>
          </Group>
          <Text fw={700} size="xl" mt="xs">
            {stats?.helpful_rate ?? 100}%
          </Text>
          <Progress value={stats?.helpful_rate ?? 100} color="teal" size="xs" mt="xs" />
        </Card>

        <Card withBorder radius="md" padding="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Refusal Rate
            </Text>
            <ThemeIcon color="orange" variant="light" size="sm">
              <IconBan size={14} />
            </ThemeIcon>
          </Group>
          <Text fw={700} size="xl" mt="xs">
            {stats?.refusal_rate ?? 0}%
          </Text>
          <Text size="xs" c="dimmed" mt={4}>
            {stats?.refusal_count ?? 0} out-of-scope requests blocked
          </Text>
        </Card>

        <Card withBorder radius="md" padding="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Unanswered / Low Conf
            </Text>
            <ThemeIcon color="red" variant="light" size="sm">
              <IconHelp size={14} />
            </ThemeIcon>
          </Group>
          <Text fw={700} size="xl" mt="xs">
            {stats?.unresolved_count ?? unanswered.length}
          </Text>
          <Text size="xs" c="dimmed" mt={4}>
            Questions requiring documentation
          </Text>
        </Card>
      </SimpleGrid>

      {/* Top Topics Distribution */}
      {stats?.top_topics && stats.top_topics.length > 0 && (
        <Paper p="md" withBorder radius="md">
          <Text size="sm" fw={600} mb="xs">
            Most Frequently Queried Topics
          </Text>
          <Group gap="xs">
            {stats.top_topics.map((t, idx) => (
              <Badge key={idx} variant="outline" size="md" color="blue">
                {t.topic.replace('_', ' ')}: {t.count}
              </Badge>
            ))}
          </Group>
        </Paper>
      )}

      {/* Unresolved Questions List */}
      <Paper withBorder radius="md" p="md">
        <Group justify="space-between" mb="xs">
          <Text size="sm" fw={600}>
            Unresolved or Low Confidence Questions ({unanswered.length})
          </Text>
        </Group>

        {unanswered.length === 0 ? (
          <Text size="xs" c="dimmed" py="sm">
            No unresolved questions currently recorded. All team questions were answered with high confidence.
          </Text>
        ) : (
          <Table highlightOnHover verticalSpacing="xs">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>User Question</Table.Th>
                <Table.Th>User</Table.Th>
                <Table.Th>Topic Guess</Table.Th>
                <Table.Th>Confidence</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {unanswered.map((item) => (
                <Table.Tr key={item.id}>
                  <Table.Td>
                    <Text size="xs" fw={500}>
                      {item.question}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="dimmed">
                      {item.user_name || 'Anonymous'}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge size="xs" variant="light" color="gray">
                      {item.topic_guess || 'out_of_scope'}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs">{item.confidence ? Math.round(item.confidence * 100) : 0}%</Text>
                  </Table.Td>
                  <Table.Td>
                    <Button
                      size="compact-xs"
                      variant="subtle"
                      color="teal"
                      leftSection={<IconCheck size={12} />}
                      onClick={() => resolveMutation.mutate({ id: item.id, resolved: true })}
                      loading={resolveMutation.isPending}
                    >
                      Resolve
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Paper>
    </Stack>
  );
};
