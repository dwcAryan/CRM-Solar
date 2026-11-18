import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Modal, Button, Stack, Select, Textarea, Alert, Group, Text, Badge } from '@mantine/core';
import { IconGitMerge, IconAlertCircle } from '@tabler/icons-react';
import { mergeLead, fetchLeads } from '../../api/client';
import type { Lead } from '../../api/types';

interface MergeLeadModalProps {
  opened: boolean;
  onClose: () => void;
  duplicateLead: Lead | null;
  onSuccess?: () => void;
}

export const MergeLeadModal: React.FC<MergeLeadModalProps> = ({
  opened,
  onClose,
  duplicateLead,
  onSuccess,
}) => {
  const queryClient = useQueryClient();
  const [targetLeadId, setTargetLeadId] = useState<string | null>(null);
  const [note, setNote] = useState('');
  const [remark, setRemark] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data: leadsData } = useQuery<{ results: Lead[]; count: number }>({
    queryKey: ['leads-all'],
    queryFn: () => fetchLeads({ page_size: 100 }),
    enabled: opened,
  });

  const availableTargets = (leadsData?.results || []).filter(
    (l) => duplicateLead && l.id !== duplicateLead.id && l.status !== 'Merged'
  );

  const mergeMutation = useMutation({
    mutationFn: () => {
      if (!duplicateLead) throw new Error('No duplicate lead selected');
      if (!targetLeadId) throw new Error('Please select primary lead');
      return mergeLead(duplicateLead.id, Number(targetLeadId), note.trim(), remark.trim() || undefined);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['lead', duplicateLead?.id] });
      queryClient.invalidateQueries({ queryKey: ['lead', targetLeadId] });
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
        setErrorMsg(messages || 'Failed to merge leads.');
      } else {
        setErrorMsg(err.message || 'Failed to merge leads.');
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetLeadId) {
      setErrorMsg('Please choose the primary lead to keep active.');
      return;
    }
    setErrorMsg(null);
    mergeMutation.mutate();
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <IconGitMerge size={18} />
          <Text fw={600}>Merge Duplicate Lead</Text>
          {duplicateLead && <Badge color="orange">#{duplicateLead.id}</Badge>}
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

          <Alert color="orange" variant="light">
            <Text size="xs">
              Merging will move all activities, surveys, and quotes from{' '}
              <strong>{duplicateLead?.name} (#{duplicateLead?.id})</strong> into the selected primary lead, and mark this lead as <strong>Merged</strong> (terminal).
            </Text>
          </Alert>

          <Select
            label="Select Primary Target Lead"
            placeholder="Search by name, phone or ID"
            data={availableTargets.map((l) => ({
              value: String(l.id),
              label: `#${l.id} - ${l.name} (${l.phone}) [${l.status}]`,
            }))}
            value={targetLeadId}
            onChange={setTargetLeadId}
            searchable
            required
          />

          <Textarea
            label="Merge Note"
            placeholder="e.g. Same customer contacted via phone and website form"
            rows={2}
            value={note}
            onChange={(e) => setNote(e.currentTarget.value)}
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
            <Button type="submit" color="orange" loading={mergeMutation.isPending}>
              Confirm Merge
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};
