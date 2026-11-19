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
  IconDownload,
} from '@tabler/icons-react';
import { fetchQuotes, markQuoteSent, acceptQuote } from '../api/client';
import { useTranslation } from 'react-i18next';
import { translateStatus } from '../i18n/formatters';
import { ReviseQuoteModal } from '../components/modals/ReviseQuoteModal';
import { RejectQuoteModal } from '../components/modals/RejectQuoteModal';
import { downloadPdfBlob } from '../utils/downloadPdf';
import type { Quote } from '../api/types';

export const QuotesPage: React.FC = () => {
  const { t, i18n } = useTranslation(['quotes', 'common', 'leads']);
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
                <Title order={3}>{t('title', 'Quotations & Proposals')}</Title>
                <Text size="xs" c="dimmed">
                  {t('subtitle', 'Track solar proposals, versioning, customer negotiations, and closed deals')}
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
                { label: t('status.all', 'All'), value: 'all' },
                { label: t('status.draft', 'Draft'), value: 'draft' },
                { label: t('status.sent', 'Sent'), value: 'sent' },
                { label: t('status.revised', 'Revised'), value: 'revised' },
                { label: t('status.accepted', 'Accepted (Won)'), value: 'accepted' },
                { label: t('status.rejected', 'Rejected'), value: 'rejected' },
              ]}
            />
            <Text size="xs" c="dimmed">
              {t('showing_count', { count: quotes.length, defaultValue: `Showing ${quotes.length} proposals` })}
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
              {t('empty', 'No quotations found matching the selected filter.')}
            </Text>
          </Paper>
        ) : (
          <Paper withBorder radius="md" style={{ overflow: 'hidden' }}>
            <Table highlightOnHover verticalSpacing="sm">
              <Table.Thead bg="var(--mantine-color-gray-0)">
                <Table.Tr>
                  <Table.Th>{t('table.lead', 'Proposal / Lead')}</Table.Th>
                  <Table.Th>{t('table.version', 'Version')}</Table.Th>
                  <Table.Th>{t('table.system_size', 'System Size')}</Table.Th>
                  <Table.Th>{t('table.equipment', 'Brand & Specs')}</Table.Th>
                  <Table.Th>{t('table.pricing', 'Price Breakdown')}</Table.Th>
                  <Table.Th>{t('table.status', 'Status')}</Table.Th>
                  <Table.Th ta="right">{t('common:actions.actions', 'Actions')}</Table.Th>
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
                          {t('leads:fields.created_at', 'Created')}: {new Date(quote.created_at).toLocaleDateString()}
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
                            {t('fields.subsidy_amount', 'Subsidy')}: -₹{quote.subsidy_amount.toLocaleString('en-IN')} (Net: ₹
                            {net.toLocaleString('en-IN')})
                          </Text>
                        ) : null}
                      </Table.Td>

                      <Table.Td>
                        <Badge color={getStatusColor(quote.status)} variant="light">
                          {translateStatus(quote.status, i18n.language).toUpperCase()}
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
                            {t('table.lead', 'Lead')}
                          </Button>

                          {quote.status === 'draft' && (
                            <Button
                              size="xs"
                              color="blue"
                              variant="light"
                              leftSection={<IconSend size={12} />}
                              onClick={() => sendMutation.mutate(quote.id)}
                            >
                              {t('actions.mark_sent', 'Send')}
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
                                {t('actions.accept', 'Accept')}
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
                                {t('actions.revise', 'Revise')}
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
                                {t('actions.reject', 'Reject')}
                              </Button>
                            </>
                          )}
                          <Button
                            size="xs"
                            variant="light"
                            color="gray"
                            leftSection={<IconDownload size={12} />}
                            onClick={() => downloadPdfBlob(`/api/quotes/${quote.id}/pdf/`, `quote_${quote.id}.pdf`)}
                          >
                            PDF
                          </Button>
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
