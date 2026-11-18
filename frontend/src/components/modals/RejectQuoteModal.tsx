import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Modal, Button, Stack, Select, Textarea, Alert, Group, Text, Badge } from '@mantine/core';
import { IconX, IconAlertCircle } from '@tabler/icons-react';
import { rejectQuote, fetchLostReasons } from '../../api/client';
import type { Quote, LostReason } from '../../api/types';

interface RejectQuoteModalProps {
  opened: boolean;
  onClose: () => void;
  quote: Quote | null;
  onSuccess?: () => void;
}

export const RejectQuoteModal: React.FC<RejectQuoteModalProps> = ({
  opened,
  onClose,
  quote,
  onSuccess,
}) => {
  const queryClient = useQueryClient();
  const [lostReasonId, setLostReasonId] = useState<string | null>(null);
  const [notes, setNotes] = useState('');
  const [remark, setRemark] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data: lostReasons = [] } = useQuery<LostReason[]>({
    queryKey: ['lost-reasons'],
    queryFn: fetchLostReasons,
    enabled: opened,
  });

  const rejectMutation = useMutation({
    mutationFn: () => {
      if (!quote) throw new Error('No quote selected');
      if (!lostReasonId) throw new Error('Please select a lost reason');
      return rejectQuote(quote.id, Number(lostReasonId), notes.trim(), remark.trim() || undefined);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] });
      queryClient.invalidateQueries({ queryKey: ['lead', quote?.lead] });
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setErrorMsg(null);
      if (onSuccess) onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const resp = err.response?.data;
      if (typeof resp === 'object') {
        const messages = Object.entries(resp)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
          .join('\n');
        setErrorMsg(messages || 'Failed to reject quote.');
      } else {
        setErrorMsg(err.message || 'Failed to reject quote.');
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!lostReasonId) {
      setErrorMsg('A lost reason is mandatory when customer rejects the proposal.');
      return;
    }
    setErrorMsg(null);
    rejectMutation.mutate();
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <IconX size={18} color="red" />
          <Text fw={600}>Customer Rejected Proposal</Text>
          {quote && <Badge color="red">v{quote.version}</Badge>}
        </Group>
      }
      radius="md"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          {errorMsg && (
            <Alert icon={<IconAlertCircle size={16} />} title="Error" color="red" variant="light">
              <Text size="xs" style={{ whiteSpace: 'pre-line' }}>
                {errorMsg}
              </Text>
            </Alert>
          )}

          <Alert color="red" variant="light">
            <Text size="xs">
              Rejecting this quotation will transition the lead to terminal status <strong>Lost</strong> with the selected lost reason.
            </Text>
          </Alert>

          <Select
            label="Reason for Rejection / Lost Reason"
            placeholder="Select why the proposal was turned down"
            data={lostReasons.map((r) => ({ value: String(r.id), label: r.name }))}
            value={lostReasonId}
            onChange={setLostReasonId}
            required
            searchable
          />

          <Textarea
            label="Customer Feedback / Notes"
            placeholder="e.g. Chose competitor due to lower quotation, or decided not to invest now"
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.currentTarget.value)}
          />

          <Textarea
            label="Optional Remark"
            placeholder="Additional internal remark (max 500 chars)"
            rows={2}
            maxLength={500}
            value={remark}
            onChange={(e) => setRemark(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" color="red" loading={rejectMutation.isPending}>
              Confirm Rejection & Close Lead
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};
