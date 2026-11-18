import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  Stack,
  Group,
  Text,
  Badge,
  Button,
  ActionIcon,
  Alert,
  Accordion,
  Paper,
  Divider,
  Loader,
  Box,
  SimpleGrid,
  Tooltip,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconSparkles,
  IconRefresh,
  IconCopy,
  IconCheck,
  IconBrandWhatsapp,
  IconCalendarClock,
  IconAlertTriangle,
  IconAlertCircle,
  IconBulb,
  IconShieldQuestion,
  IconArrowRight,
  IconInfoCircle,
} from '@tabler/icons-react';
import { fetchAISuggestion, generateAISuggestion } from '../../api/client';
import type { Lead, AISuggestion } from '../../api/types';

interface AISuggestionsCardProps {
  lead: Lead;
  onPreFillOutcome?: (outcomeName: string) => void;
}

export const AISuggestionsCard: React.FC<AISuggestionsCardProps> = ({ lead, onPreFillOutcome }) => {
  const queryClient = useQueryClient();
  const [copied, setCopied] = useState(false);

  // Fetch cached AI suggestion or generate default
  const {
    data: suggestion,
    isLoading,
    isFetching,
    error,
  } = useQuery<AISuggestion>({
    queryKey: ['ai-suggestion', lead.id],
    queryFn: () => fetchAISuggestion(lead.id),
    staleTime: 60 * 1000,
    retry: 1,
  });

  // Explicit refresh mutation
  const refreshMutation = useMutation({
    mutationFn: () => generateAISuggestion(lead.id, true),
    onSuccess: (data) => {
      queryClient.setQueryData(['ai-suggestion', lead.id], data);
      notifications.show({
        title: 'AI Analysis Refreshed',
        message: 'Loaded the latest recommendations for this lead.',
        color: 'teal',
        icon: <IconCheck size={16} />,
      });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.error || err.message || 'Failed to refresh AI analysis';
      notifications.show({
        title: 'Refresh Failed',
        message: msg,
        color: 'red',
        icon: <IconAlertCircle size={16} />,
      });
    },
  });

  const handleCopyWhatsapp = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
    notifications.show({
      title: 'WhatsApp Message Copied',
      message: 'Paste it directly into WhatsApp web or your phone app.',
      color: 'teal',
      icon: <IconCopy size={16} />,
    });
  };

  const handleOpenWhatsapp = (phone: string, text: string) => {
    const cleanPhone = phone.replace(/\D/g, '');
    const fullPhone = cleanPhone.length === 10 ? `91${cleanPhone}` : cleanPhone;
    window.open(`https://wa.me/${fullPhone}?text=${encodeURIComponent(text)}`, '_blank');
  };

  const isTerminal = ['Won', 'Lost', 'Do not contact', 'Merged', 'Invalid contact'].includes(lead.status);

  // Risk styling helper
  const renderRiskBadge = (level: 'low' | 'medium' | 'high') => {
    switch (level) {
      case 'high':
        return (
          <Badge color="red" variant="filled" leftSection={<IconAlertTriangle size={14} />}>
            High Risk
          </Badge>
        );
      case 'medium':
        return (
          <Badge color="orange" variant="light" leftSection={<IconAlertCircle size={14} />}>
            Medium Risk
          </Badge>
        );
      case 'low':
      default:
        return (
          <Badge color="green" variant="light" leftSection={<IconCheck size={14} />}>
            Low Risk
          </Badge>
        );
    }
  };

  // Provider branding badge
  const renderProviderBadge = (sugg: AISuggestion) => {
    if (sugg.provider === 'anthropic' && !sugg.is_fallback) {
      return (
        <Badge variant="gradient" gradient={{ from: 'indigo', to: 'violet', deg: 90 }} size="sm">
          Claude 3.5 Sonnet
        </Badge>
      );
    }
    if (sugg.is_fallback) {
      return (
        <Badge color="yellow" variant="light" size="sm">
          Rules Engine (Fallback)
        </Badge>
      );
    }
    return (
      <Badge color="gray" variant="outline" size="sm">
        Solar Sales Rules Engine
      </Badge>
    );
  };

  return (
    <Card withBorder radius="md" p="md" shadow="sm" style={{ borderLeft: '4px solid #4f46e5' }}>
      <Stack gap="sm">
        {/* Header */}
        <Group justify="space-between" align="center" wrap="wrap">
          <Group gap="xs">
            <Box style={{ color: '#4f46e5', display: 'flex', alignItems: 'center' }}>
              <IconSparkles size={22} />
            </Box>
            <Text fw={700} fz="md" style={{ color: '#1e293b' }}>
              AI Sales Copilot & Strategic Suggestions
            </Text>
            {suggestion && renderProviderBadge(suggestion)}
          </Group>

          <Group gap="xs">
            <Tooltip label="Regenerate strategy based on latest history & activities">
              <Button
                variant="light"
                color="indigo"
                size="xs"
                leftSection={
                  refreshMutation.isPending || isFetching ? (
                    <Loader size={14} color="indigo" />
                  ) : (
                    <IconRefresh size={14} />
                  )
                }
                loading={refreshMutation.isPending || isFetching}
                onClick={() => refreshMutation.mutate()}
              >
                Refresh Analysis
              </Button>
            </Tooltip>
          </Group>
        </Group>

        <Text fz="xs" c="dimmed">
          <IconInfoCircle size={12} style={{ display: 'inline', verticalAlign: 'text-bottom', marginRight: 4 }} />
          AI-generated recommendations. Please review and exercise professional judgment before taking action.
        </Text>

        <Divider />

        {/* Loading state */}
        {isLoading && (
          <Paper p="xl" withBorder style={{ textAlign: 'center', backgroundColor: '#f8fafc' }}>
            <Stack align="center" gap="xs">
              <Loader size="md" color="indigo" />
              <Text fz="sm" fw={500} c="dimmed">
                Synthesizing customer profile, interactions, and solar economics...
              </Text>
            </Stack>
          </Paper>
        )}

        {/* Error state */}
        {error && (
          <Alert color="red" title="Could not load AI recommendations" icon={<IconAlertCircle size={16} />}>
            {(error as any)?.response?.data?.error ||
              'An error occurred while analyzing this lead. Please click refresh to try again.'}
          </Alert>
        )}

        {/* Terminal Lead Banner */}
        {isTerminal && (
          <Alert color="gray" title={`Lead status is ${lead.status}`} icon={<IconInfoCircle size={16} />}>
            Active sales outreach is paused or closed for this lead. Suggestions below reflect historical context and
            retrospective retention strategy.
          </Alert>
        )}

        {/* Loaded Content */}
        {suggestion?.output_json && (
          <Stack gap="md">
            {/* Situation Summary & Risk */}
            <Paper p="sm" withBorder radius="sm" style={{ backgroundColor: '#f8fafc' }}>
              <Group justify="space-between" align="flex-start" mb="xs">
                <Group gap="xs">
                  <IconBulb size={18} color="#f59e0b" />
                  <Text fw={600} fz="sm">
                    Situation Assessment
                  </Text>
                </Group>
                <Group gap="xs">
                  {renderRiskBadge(suggestion.output_json.risk_level)}
                </Group>
              </Group>

              <Text fz="sm" c="dark.7" mb="xs">
                {suggestion.output_json.situation_summary}
              </Text>

              {suggestion.output_json.risk_reason && (
                <Text fz="xs" c="dimmed">
                  <strong>Risk Factor:</strong> {suggestion.output_json.risk_reason}
                </Text>
              )}
            </Paper>

            {/* Next Best Action Grid */}
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="sm">
              {/* Best Action */}
              <Paper p="sm" withBorder radius="sm">
                <Group gap="xs" mb="xs">
                  <IconArrowRight size={18} color="#4f46e5" />
                  <Text fw={600} fz="sm">
                    Recommended Next Action
                  </Text>
                </Group>
                <Text fz="sm" fw={500} c="dark.8" mb="xs">
                  {suggestion.output_json.best_next_action}
                </Text>

                <Group gap="xs" mt="xs">
                  <IconCalendarClock size={16} color="#64748b" />
                  <Text fz="xs" c="dimmed">
                    <strong>Optimal Timing:</strong> {suggestion.output_json.suggested_follow_up_timing}
                  </Text>
                </Group>
              </Paper>

              {/* Suggested Outcome to Log */}
              <Paper p="sm" withBorder radius="sm" style={{ backgroundColor: '#f0fdf4' }}>
                <Group justify="space-between" align="center" mb="xs">
                  <Text fw={600} fz="sm" c="teal.9">
                    Target Outcome
                  </Text>
                  <Badge color="teal" variant="light" size="sm">
                    {suggestion.output_json.suggested_outcome_to_log}
                  </Badge>
                </Group>
                <Text fz="xs" c="dimmed" mb="sm">
                  Pre-fill this outcome into your call/interaction log to save time and align with system policies.
                </Text>
                {onPreFillOutcome && !isTerminal && (
                  <Button
                    size="xs"
                    color="teal"
                    variant="filled"
                    leftSection={<IconCheck size={14} />}
                    onClick={() => onPreFillOutcome(suggestion.output_json.suggested_outcome_to_log)}
                  >
                    Use This Outcome
                  </Button>
                )}
              </Paper>
            </SimpleGrid>

            {/* Suggested WhatsApp Outreach */}
            {suggestion.output_json.suggested_whatsapp_message && (
              <Paper p="sm" withBorder radius="sm" style={{ borderLeft: '3px solid #25D366', backgroundColor: '#fcfdfc' }}>
                <Group justify="space-between" align="center" mb="xs">
                  <Group gap="xs">
                    <IconBrandWhatsapp size={18} color="#25D366" />
                    <Text fw={600} fz="sm" c="#128C7E">
                      Suggested WhatsApp Script (English/Hinglish)
                    </Text>
                  </Group>
                  <Group gap="xs">
                    <Button
                      size="xs"
                      variant="light"
                      color="teal"
                      leftSection={copied ? <IconCheck size={14} /> : <IconCopy size={14} />}
                      onClick={() => handleCopyWhatsapp(suggestion.output_json.suggested_whatsapp_message)}
                    >
                      {copied ? 'Copied' : 'Copy Message'}
                    </Button>
                    {!lead.do_not_contact && (
                      <ActionIcon
                        color="teal"
                        variant="subtle"
                        title="Send via WhatsApp Web"
                        onClick={() => handleOpenWhatsapp(lead.phone, suggestion.output_json.suggested_whatsapp_message)}
                      >
                        <IconBrandWhatsapp size={18} />
                      </ActionIcon>
                    )}
                  </Group>
                </Group>

                <Paper p="xs" withBorder radius="xs" style={{ backgroundColor: '#ffffff', fontStyle: 'normal' }}>
                  <Text fz="xs" c="dark.8" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                    {suggestion.output_json.suggested_whatsapp_message}
                  </Text>
                </Paper>
              </Paper>
            )}

            {/* Talking Points & Objections Accordion */}
            <Accordion variant="separated" radius="sm">
              {suggestion.output_json.talking_points?.length > 0 && (
                <Accordion.Item value="talking_points">
                  <Accordion.Control icon={<IconBulb size={18} color="#eab308" />}>
                    <Text fw={600} fz="sm">
                      Consultative Talking Points ({suggestion.output_json.talking_points.length})
                    </Text>
                  </Accordion.Control>
                  <Accordion.Panel>
                    <Stack gap="xs">
                      {suggestion.output_json.talking_points.map((point, idx) => (
                        <Group key={idx} align="flex-start" gap="xs">
                          <IconCheck size={16} color="#16a34a" style={{ marginTop: 2, flexShrink: 0 }} />
                          <Text fz="xs" c="dark.7" style={{ flex: 1 }}>
                            {point}
                          </Text>
                        </Group>
                      ))}
                    </Stack>
                  </Accordion.Panel>
                </Accordion.Item>
              )}

              {suggestion.output_json.objections_to_expect?.length > 0 && (
                <Accordion.Item value="objections">
                  <Accordion.Control icon={<IconShieldQuestion size={18} color="#3b82f6" />}>
                    <Text fw={600} fz="sm">
                      Likely Objections & Counter-Arguments ({suggestion.output_json.objections_to_expect.length})
                    </Text>
                  </Accordion.Control>
                  <Accordion.Panel>
                    <Stack gap="sm">
                      {suggestion.output_json.objections_to_expect.map((item, idx) => (
                        <Paper key={idx} p="xs" withBorder radius="xs" style={{ backgroundColor: '#f8fafc' }}>
                          <Text fz="xs" fw={600} c="red.8" mb={4}>
                            Q: "{item.objection}"
                          </Text>
                          <Text fz="xs" c="dark.8">
                            <strong>Effective Response:</strong> {item.reply}
                          </Text>
                        </Paper>
                      ))}
                    </Stack>
                  </Accordion.Panel>
                </Accordion.Item>
              )}
            </Accordion>
          </Stack>
        )}
      </Stack>
    </Card>
  );
};
