import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Modal, Button, Stack, TextInput, Textarea, Alert, Group, Text } from '@mantine/core';
import { IconCalendarTime, IconAlertCircle } from '@tabler/icons-react';
import { rescheduleSurvey } from '../../api/client';
import type { Survey } from '../../api/types';

interface RescheduleSurveyModalProps {
  opened: boolean;
  onClose: () => void;
  survey: Survey | null;
  onSuccess?: () => void;
}

export const RescheduleSurveyModal: React.FC<RescheduleSurveyModalProps> = ({
  opened,
  onClose,
  survey,
  onSuccess,
}) => {
  const queryClient = useQueryClient();
  const [scheduledAt, setScheduledAt] = useState('');
  const [notes, setNotes] = useState('');
  const [remark, setRemark] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const rescheduleMutation = useMutation({
    mutationFn: () => {
      if (!survey) throw new Error('No survey selected');
      return rescheduleSurvey(survey.id, {
        scheduled_at: new Date(scheduledAt).toISOString(),
        notes: notes.trim(),
        remark: remark.trim() || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
      queryClient.invalidateQueries({ queryKey: ['lead', survey?.lead] });
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      setScheduledAt('');
      setNotes('');
      setRemark('');
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
        setErrorMsg(messages || 'Failed to reschedule survey.');
      } else {
        setErrorMsg(err.message || 'Failed to reschedule survey.');
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!scheduledAt) {
      setErrorMsg('Please enter the new scheduled date and time.');
      return;
    }
    setErrorMsg(null);
    rescheduleMutation.mutate();
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <IconCalendarTime size={18} />
          <Text fw={600}>Reschedule Site Survey</Text>
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

          <TextInput
            label="New Survey Scheduled Date & Time"
            type="datetime-local"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.currentTarget.value)}
            required
          />

          <Textarea
            label="Reason for Rescheduling / Notes"
            placeholder="e.g. Customer unavailable due to office travel, requested weekend slot"
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
            <Button type="submit" color="yellow" loading={rescheduleMutation.isPending}>
              Confirm Reschedule
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};
