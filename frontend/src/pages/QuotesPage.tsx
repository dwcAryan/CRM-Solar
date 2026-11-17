import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Container,
  Title,
  Text,
  Group,
  Stack,
  Badge,
  Button,
  SegmentedControl,
  Table,
  Loader,
  Center,
  Paper,
  ThemeIcon,
} from '@mantine/core';
import {
  IconSend,
  IconRefresh,
  IconCheck,
  IconFileCertificate,
} from '@tabler/icons-react';
import { fetchQuotes, markQuoteSent, acceptQuote } from '../api/client';
import { ReviseQuoteModal } from '../components/modals/ReviseQuoteModal';
import { RejectQuoteModal } from '../components/modals/RejectQuoteModal';
import type { Quote } from '../api/types';

export const QuotesPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedQuote, setSelectedQuote] = useState<Quote | null>(null);
  const [reviseModalOpen, setReviseModalOpen] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);

  const { data: quotes = [], isLoading, refetch } = useQuery<Quote[]>({
    queryKey: ['quotes', { status: statusFilter }],
    queryFn: () => {
      const params: Record<string, any> = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      return fetchQuotes(params);
    },
  });

  const sendMutation = useMutation({
    mutationFn: (id: number) => markQuoteSent(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] });
    },
  });

  const acceptMutation = useMutation({
    mutationFn: (id: number) => acceptQuote(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'accepted':
        return 'green';
      case 'rejected':
        return 'red';
      case 'sent':
        return 'blue';
      case 'revised':
        return 'gray';
      default:
        return 'yellow';
    }
  };

  return (
    <Container size="xl" py="md">
      <Stack gap="lg">
        {/* Header */}
        <Group justify="space-between" align="center">
          <div>
            <Group gap="xs">
              <ThemeIcon size="lg" radius="md" color="yellow" variant="light">
                <IconFileCertificate size={22} />
              </ThemeIcon>
              <div>
                <Title order={3}>Quotations & Proposals</Title>
                <Text size="xs" c="dimmed">
                  Track solar proposals, versioning, customer negotiations, and closed deals
                </Text>
              </div>
            </Group>
          </div>
        </Group>

        {/* Filter Bar */}
        <Paper p="xs" withBorder radius="md">
          <Group justify="space-between">
            <SegmentedControl
              value={statusFilter}
              onChange={setStatusFilter}
              color="yellow"
              size="xs"
              data={[
                { label: 'All', value: 'all' },
                { label: 'Draft', value: 'draft' },
                { label: 'Sent', value: 'sent' },
                { label: 'Revised', value: 'revised' },
                { label: 'Accepted (Won)', value: 'accepted' },
                { label: 'Rejected', value: 'rejected' },
              ]}
            />
            <Text size="xs" c="dimmed">
              Showing {quotes.length} proposals
            </Text>
          </Group>
        </Paper>

        {/* Quotes Table */}
        {isLoading ? (
          <Center py="xl">
            <Loader color="yellow" />
          </Center>
        ) : quotes.length === 0 ? (
          <Paper p="xl" withBorder radius="md" ta="center">
            <Text size="sm" c="dimmed">
              No quotations found matching the selected filter.
            </Text>
          </Paper>
        ) : (
          <Paper withBorder radius="md" style={{ overflow: 'hidden' }}>
            <Table highlightOnHover verticalSpacing="sm">
              <Table.Thead bg="var(--mantine-color-gray-0)">
                <Table.Tr>
                  <Table.Th>Proposal / Lead</Table.Th>
                  <Table.Th>Version</Table.Th>
                  <Table.Th>System Size</Table.Th>
                  <Table.Th>Brand & Specs</Table.Th>
                  <Table.Th>Price Breakdown</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th ta="right">Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {quotes.map((quote) => {
                  const net = quote.price - (quote.subsidy_amount || 0);
                  return (
                    <Table.Tr key={quote.id}>
                      <Table.Td>
                        <Group gap="xs">
                          <Text
                            fw={600}
                            size="sm"
                            style={{ cursor: 'pointer' }}
                            c="yellow.9"
                            onClick={() => navigate(`/leads/${quote.lead}`)}
                          >
                            {quote.lead_name || `Lead #${quote.lead}`}
                          </Text>
                        </Group>
                        <Text size="10px" c="dimmed">
                          Created {new Date(quote.created_at).toLocaleDateString()}
                        </Text>
                      </Table.Td>

                      <Table.Td>
                        <Badge color="gray" size="sm">
                          v{quote.version}
                        </Badge>
                      </Table.Td>

                      <Table.Td>
                        <Text size="xs" fw={600}>
                          {quote.system_size_kw} kW
                        </Text>
                      </Table.Td>

                      <Table.Td>
                        <Text size="xs">{quote.brand}</Text>
                        {quote.notes && (
                          <Text size="10px" c="dimmed" lineClamp={1}>
                            {quote.notes}
                          </Text>
                        )}
                      </Table.Td>

                      <Table.Td>
                        <Text size="xs" fw={600}>
                          ₹{quote.price.toLocaleString('en-IN')}
                        </Text>
                        {quote.subsidy_amount ? (
                          <Text size="10px" c="green">
                            Subsidy: -₹{quote.subsidy_amount.toLocaleString('en-IN')} (Net: ₹
                            {net.toLocaleString('en-IN')})
                          </Text>
                        ) : null}
                      </Table.Td>

                      <Table.Td>
                        <Badge color={getStatusColor(quote.status)} variant="light">
                          {quote.status.toUpperCase()}
                        </Badge>
                      </Table.Td>

                      <Table.Td ta="right">
                        <Group gap="xs" justify="flex-end">
                          <Button
                            size="xs"
                            variant="subtle"
                            color="gray"
                            onClick={() => navigate(`/leads/${quote.lead}`)}
                          >
                            Lead
                          </Button>

                          {quote.status === 'draft' && (
                            <Button
                              size="xs"
                              color="blue"
                              variant="light"
                              leftSection={<IconSend size={12} />}
                              onClick={() => sendMutation.mutate(quote.id)}
                            >
                              Send
                            </Button>
                          )}

                          {(quote.status === 'draft' || quote.status === 'sent') && (
                            <>
                              <Button
                                size="xs"
                                color="green"
                                variant="filled"
                                leftSection={<IconCheck size={12} />}
                                onClick={() => acceptMutation.mutate(quote.id)}
                              >
                                Accept
                              </Button>
                              <Button
                                size="xs"
                                color="yellow"
                                variant="light"
                                leftSection={<IconRefresh size={12} />}
                                onClick={() => {
                                  setSelectedQuote(quote);
                                  setReviseModalOpen(true);
                                }}
                              >
                                Revise
                              </Button>
                              <Button
                                size="xs"
                                color="red"
                                variant="subtle"
                                onClick={() => {
                                  setSelectedQuote(quote);
                                  setRejectModalOpen(true);
                                }}
                              >
                                Reject
                              </Button>
                            </>
                          )}
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Paper>
        )}
      </Stack>

      {/* Modals */}
      <ReviseQuoteModal
        opened={reviseModalOpen}
        onClose={() => {
          setReviseModalOpen(false);
          setSelectedQuote(null);
        }}
        quote={selectedQuote}
        onSuccess={() => refetch()}
      />

      <RejectQuoteModal
        opened={rejectModalOpen}
        onClose={() => {
          setRejectModalOpen(false);
          setSelectedQuote(null);
        }}
        quote={selectedQuote}
        onSuccess={() => refetch()}
      />
    </Container>
  );
};
