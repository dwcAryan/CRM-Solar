import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Modal,
  Button,
  Stack,
  Textarea,
  Alert,
  Group,
  Text,
  Badge,
} from '@mantine/core';
import { IconNotes, IconAlertCircle } from '@tabler/icons-react';
import { addRemark } from '../../api/client';
import type { Lead } from '../../api/types';

interface AddRemarkModalProps {
  opened: boolean;
  onClose: () => void;
  lead: Lead | null;
  onSuccess?: () => void;
}

export const AddRemarkModal: React.FC<AddRemarkModalProps> = ({
  opened,
  onClose,
  lead,
  onSuccess,
}) => {
  const queryClient = useQueryClient();
  const [remarkText, setRemarkText] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const addRemarkMutation = useMutation({
    mutationFn: () => {
      if (!lead) throw new Error('No lead selected');
      if (!remarkText.trim()) throw new Error('Remark text cannot be empty');
      return addRemark(lead.id, remarkText.trim());
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead', lead?.id] });
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['today-leads'] });
      queryClient.invalidateQueries({ queryKey: ['activities', lead?.id] });
      setRemarkText('');
      setErrorMsg(null);
      if (onSuccess) onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const resp = err.response?.data;
      setErrorMsg(resp?.remark || resp?.error || err.message || 'Failed to add remark.');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!remarkText.trim()) {
      setErrorMsg('Please enter a remark note.');
      return;
    }
    setErrorMsg(null);
    addRemarkMutation.mutate();
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <IconNotes size={18} />
          <Text fw={600}>Add Internal Remark</Text>
          {lead && <Badge color="yellow">{lead.name}</Badge>}
        </Group>
      }
      radius="md"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          {errorMsg && (
            <Alert icon={<IconAlertCircle size={16} />} title="Error" color="red" variant="light">
              <Text size="xs">{errorMsg}</Text>
            </Alert>
          )}

          <Text size="xs" c="dimmed">
            Remarks add a note to the lead's activity timeline without altering the current lead status or scheduled follow-up date.
          </Text>

          <div>
            <Textarea
              label="Remark / Note"
              placeholder="e.g. Customer preferred morning WhatsApp communication, key with caretaker."
              rows={4}
              maxLength={500}
              value={remarkText}
              onChange={(e) => setRemarkText(e.currentTarget.value)}
              required
            />
            <Text size="10px" c="dimmed" ta="right" mt={4}>
              {remarkText.length} / 500 characters
            </Text>
          </div>

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" color="yellow" loading={addRemarkMutation.isPending}>
              Save Remark
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};
