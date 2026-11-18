import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Modal, Button, Stack, TextInput, Select, Textarea, Alert, Group, Text } from '@mantine/core';
import { IconCalendarPlus, IconAlertCircle } from '@tabler/icons-react';
import { bookSurvey, fetchUsers } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import type { Lead, User } from '../../api/types';

interface BookSurveyModalProps {
  opened: boolean;
  onClose: () => void;
  lead: Lead | null;
  onSuccess?: () => void;
}

export const BookSurveyModal: React.FC<BookSurveyModalProps> = ({ opened, onClose, lead, onSuccess }) => {
  const queryClient = useQueryClient();
  const { can } = useAuth();
  const [scheduledAt, setScheduledAt] = useState('');
  const [surveyorId, setSurveyorId] = useState<string | null>(null);
  const [notes, setNotes] = useState('');
  const [remark, setRemark] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data: users = [] } = useQuery<User[]>({
    queryKey: ['users'],
    queryFn: fetchUsers,
    enabled: opened,
  });

  const surveyors = users.filter((u) => u.role === 'surveyor' || u.role === 'admin' || u.role === 'manager');

  const bookMutation = useMutation({
    mutationFn: () => {
      if (!lead) throw new Error('No lead selected');
      return bookSurvey({
        lead_id: lead.id,
        scheduled_at: new Date(scheduledAt).toISOString(),
        surveyor_id: surveyorId ? Number(surveyorId) : undefined,
        notes: notes.trim(),
        remark: remark.trim() || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
      queryClient.invalidateQueries({ queryKey: ['lead', lead?.id] });
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setScheduledAt('');
      setSurveyorId(null);
      setNotes('');
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
        setErrorMsg(messages || 'Failed to book survey.');
      } else {
        setErrorMsg(err.message || 'Failed to book survey.');
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!scheduledAt) {
      setErrorMsg('Please specify the survey date and time.');
      return;
    }
    setErrorMsg(null);
    bookMutation.mutate();
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <IconCalendarPlus size={18} />
          <Text fw={600}>Book Site Survey</Text>
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
            label="Survey Scheduled At"
            type="datetime-local"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.currentTarget.value)}
            required
            description="Select visit date and approximate time"
          />

          {can('survey.assign') ? (
            <Select
              label="Assign Surveyor"
              placeholder="Select solar technical surveyor"
              data={surveyors.map((s) => ({
                value: String(s.id),
                label: `${s.first_name || s.username} (${s.role})`,
              }))}
              value={surveyorId}
              onChange={setSurveyorId}
              searchable
              clearable
            />
          ) : (
            <Text size="xs" c="dimmed">
              ℹ️ A field surveyor will be assigned to this inspection by your regional manager.
            </Text>
          )}

          <Textarea
            label="Survey Instructions / Site Notes"
            placeholder="e.g. Call before arriving, key with neighbor, check roof shadow from adjacent water tank"
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.currentTarget.value)}
          />

          <TextInput
            label="Optional Remark (max 500 chars)"
            placeholder="e.g. Call customer at 9 AM to confirm gate entry"
            maxLength={500}
            value={remark}
            onChange={(e) => setRemark(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" color="yellow" loading={bookMutation.isPending}>
              Confirm Booking
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};
