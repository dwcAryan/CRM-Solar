import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Modal,
  Button,
  Stack,
  Radio,
  Group,
  Select,
  Textarea,
  Alert,
  Text,
} from '@mantine/core';
import { IconCheck, IconAlertCircle } from '@tabler/icons-react';
import { markSurveyDone, fetchLostReasons } from '../../api/client';
import type { Survey, LostReason } from '../../api/types';

interface MarkDoneSurveyModalProps {
  opened: boolean;
  onClose: () => void;
  survey: Survey | null;
  onSuccess?: () => void;
}

export const MarkDoneSurveyModal: React.FC<MarkDoneSurveyModalProps> = ({
  opened,
  onClose,
  survey,
  onSuccess,
}) => {
  const queryClient = useQueryClient();
  const [siteSuitable, setSiteSuitable] = useState<string>('yes');
  const [lostReasonId, setLostReasonId] = useState<string | null>(null);
  const [notes, setNotes] = useState('');
  const [remark, setRemark] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data: lostReasons = [] } = useQuery<LostReason[]>({
    queryKey: ['lost-reasons'],
    queryFn: fetchLostReasons,
    enabled: opened,
  });

  const markDoneMutation = useMutation({
    mutationFn: () => {
      if (!survey) throw new Error('No survey selected');
      const suitable = siteSuitable === 'yes';
      return markSurveyDone(survey.id, {
        site_suitable: suitable,
        lost_reason_id: !suitable && lostReasonId ? Number(lostReasonId) : undefined,
        notes: notes.trim(),
        remark: remark.trim() || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
      queryClient.invalidateQueries({ queryKey: ['lead', survey?.lead] });
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setNotes('');
      setRemark('');
      setLostReasonId(null);
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
        setErrorMsg(messages || 'Failed to complete survey.');
      } else {
        setErrorMsg(err.message || 'Failed to complete survey.');
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (siteSuitable === 'no' && !lostReasonId) {
      setErrorMsg('Please select a reason why the site is not suitable (will mark lead Lost).');
      return;
    }
    setErrorMsg(null);
    markDoneMutation.mutate();
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <IconCheck size={18} />
          <Text fw={600}>Complete Site Survey</Text>
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

          <Radio.Group
            value={siteSuitable}
            onChange={setSiteSuitable}
            label="Is the site suitable for rooftop solar?"
            description="Assess roof area, shadow free conditions, structural strength and wiring path"
            required
          >
            <Group mt="xs">
              <Radio value="yes" label="Yes - Suitable (Moves lead to Design pending)" color="green" />
              <Radio value="no" label="No - Not Suitable (Marks lead as Lost)" color="red" />
            </Group>
          </Radio.Group>

          {siteSuitable === 'no' && (
            <Select
              label="Reason for Unsuitability"
              placeholder="Select rejection reason"
              data={lostReasons.map((r) => ({ value: String(r.id), label: r.name }))}
              value={lostReasonId}
              onChange={setLostReasonId}
              required
            />
          )}

          <Textarea
            label="Site Inspection Observations / Findings"
            placeholder="e.g. 450 sqft RCC roof, unshaded, 3-phase meter present, conduit path ~15m"
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.currentTarget.value)}
          />

          <Textarea
            label="Optional Remark"
            placeholder="Internal remark / notes (max 500 chars)"
            rows={2}
            maxLength={500}
            value={remark}
            onChange={(e) => setRemark(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              color={siteSuitable === 'yes' ? 'green' : 'red'}
              loading={markDoneMutation.isPending}
            >
              Submit Survey Report
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};
