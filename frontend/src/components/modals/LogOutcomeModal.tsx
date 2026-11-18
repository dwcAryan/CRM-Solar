import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Modal,
  Button,
  Stack,
  SegmentedControl,
  Select,
  TextInput,
  Textarea,
  Alert,
  Text,
  Group,
  Badge,
} from '@mantine/core';
import { IconAlertCircle, IconCalendar } from '@tabler/icons-react';
import {
  fetchOutcomes,
  fetchLostReasons,
  fetchNurtureReasons,
  logActivity,
} from '../../api/client';
import { ConfirmActionModal } from './ConfirmActionModal';
import type { Lead, Outcome, LostReason, NurtureReason } from '../../api/types';

interface LogOutcomeModalProps {
  opened: boolean;
  onClose: () => void;
  lead: Lead | null;
  onSuccess?: () => void;
  defaultStage?: 'call' | 'survey' | 'quote';
  initialOutcomeName?: string | null;
}

const TERMINAL_STATUSES = ['Won', 'Lost', 'Do not contact', 'Merged', 'Invalid contact'];

export const LogOutcomeModal: React.FC<LogOutcomeModalProps> = ({
  opened,
  onClose,
  lead,
  onSuccess,
  defaultStage = 'call',
  initialOutcomeName,
}) => {
  const queryClient = useQueryClient();
  const [stage, setStage] = useState<'call' | 'survey' | 'quote'>(defaultStage);
  const [outcomeId, setOutcomeId] = useState<string | null>(null);
  const [statusVal, setStatusVal] = useState<string>('');
  const [nextAction, setNextAction] = useState<string>('');
  const [nextFollowupAt, setNextFollowupAt] = useState<string>('');
  const [lostReasonId, setLostReasonId] = useState<string | null>(null);
  const [nurtureReasonId, setNurtureReasonId] = useState<string | null>(null);
  const [notes, setNotes] = useState<string>('');
  const [remark, setRemark] = useState<string>('');
  const [overrideReason, setOverrideReason] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingPayload, setPendingPayload] = useState<any>(null);

  // Queries
  const { data: outcomes = [] } = useQuery<Outcome[]>({
    queryKey: ['outcomes', stage],
    queryFn: () => fetchOutcomes(stage),
    enabled: opened,
  });

  const { data: lostReasons = [] } = useQuery<LostReason[]>({
    queryKey: ['lost-reasons'],
    queryFn: fetchLostReasons,
    enabled: opened,
  });

  const { data: nurtureReasons = [] } = useQuery<NurtureReason[]>({
    queryKey: ['nurture-reasons'],
    queryFn: fetchNurtureReasons,
    enabled: opened,
  });

  // Reset form when modal opens with a lead
  useEffect(() => {
    if (opened && lead) {
      setStage(defaultStage);
      setOutcomeId(null);
      setStatusVal(lead.status);
      setNextAction(lead.next_action || '');
      setNextFollowupAt(
        lead.next_followup_at
          ? new Date(lead.next_followup_at).toISOString().slice(0, 16)
          : ''
      );
      setLostReasonId(lead.lost_reason ? String(lead.lost_reason) : null);
      setNurtureReasonId(lead.nurture_reason ? String(lead.nurture_reason) : null);
      setNotes('');
      setRemark('');
      setOverrideReason('');
      setErrorMsg(null);
    }
  }, [opened, lead, defaultStage]);

  // When outcome changes, auto-fill fields
  const handleOutcomeChange = (selectedId: string | null) => {
    setOutcomeId(selectedId);
    setErrorMsg(null);

    if (!selectedId) return;
    const outcome = outcomes.find((o) => String(o.id) === selectedId);
    if (!outcome) return;

    setStatusVal(outcome.default_status);

    let defaultNext = outcome.default_next_action || '';
    if (lead) {
      const channel = lead.region_code === 'AU' || lead.region === 'AU' ? 'SMS' : 'WhatsApp';
      const inc = lead.region_code === 'AU' || lead.region === 'AU' ? 'Government incentive (STCs and rebates)' : 'Subsidy';
      defaultNext = defaultNext.replace(/\{channel\}/g, channel).replace(/\{incentive_label\}/g, inc);
    }
    setNextAction(defaultNext);

    if (outcome.is_terminal || TERMINAL_STATUSES.includes(outcome.default_status)) {
      setNextFollowupAt('');
    } else if (outcome.default_followup_days !== null && outcome.default_followup_days !== undefined) {
      const targetDate = new Date();
      if (outcome.default_followup_days === 0) {
        targetDate.setHours(targetDate.getHours() + 4);
      } else {
        targetDate.setDate(targetDate.getDate() + outcome.default_followup_days);
      }
      setNextFollowupAt(targetDate.toISOString().slice(0, 16));
    }
  };

  // If an initialOutcomeName is passed, attempt to auto-select matching outcome
  useEffect(() => {
    if (opened && initialOutcomeName && outcomes.length > 0 && !outcomeId) {
      const targetLower = initialOutcomeName.toLowerCase();
      const matched = outcomes.find(
        (o) => o.name.toLowerCase() === targetLower || o.name.toLowerCase().includes(targetLower)
      );
      if (matched) {
        handleOutcomeChange(String(matched.id));
      }
    }
  }, [opened, initialOutcomeName, outcomes, outcomeId]);

  const isTerminal = TERMINAL_STATUSES.includes(statusVal);
  const showLostReason = statusVal === 'Lost' || outcomes.find((o) => String(o.id) === outcomeId)?.requires_lost_reason;
  const showNurtureReason = statusVal === 'Nurture' || outcomes.find((o) => String(o.id) === outcomeId)?.requires_nurture_reason;

  const logActivityMutation = useMutation({
    mutationFn: (payload: any) => {
      if (!lead) throw new Error('No lead selected');
      return logActivity(lead.id, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['today-leads'] });
      queryClient.invalidateQueries({ queryKey: ['lead', lead?.id] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      if (onSuccess) onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const data = err.response?.data;
      if (typeof data === 'object') {
        const messages = Object.entries(data)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
          .join('\n');
        setErrorMsg(messages || 'Validation failed.');
      } else {
        setErrorMsg(err.message || 'Failed to log outcome.');
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    // Front-end validations
    if (!isTerminal && !nextFollowupAt) {
      setErrorMsg('Next follow-up date and time is required for non-terminal statuses.');
      return;
    }

    if (statusVal === 'Lost' && !lostReasonId) {
      setErrorMsg('A lost reason must be selected when marking a lead as Lost.');
      return;
    }

    if (statusVal === 'Nurture' && !nurtureReasonId) {
      setErrorMsg('A nurture reason must be selected when placing a lead into Nurture.');
      return;
    }

    if (stage === 'call' && lead?.is_within_calling_hours === false && !overrideReason.trim()) {
      setErrorMsg('A valid override reason is mandatory to log a call conducted outside permitted calling hours.');
      return;
    }

    const payload: any = {
      type: stage,
      outcome_id: outcomeId ? Number(outcomeId) : null,
      notes,
      remark: remark.trim() || undefined,
      calling_hours_override_reason: overrideReason.trim() || undefined,
      status: statusVal,
      next_action: nextAction,
      next_followup_at: isTerminal ? null : (nextFollowupAt ? new Date(nextFollowupAt).toISOString() : null),
      lost_reason_id: lostReasonId ? Number(lostReasonId) : null,
      nurture_reason_id: nurtureReasonId ? Number(nurtureReasonId) : null,
    };

    if (['Lost', 'Do not contact', 'Won'].includes(statusVal)) {
      setPendingPayload(payload);
      setConfirmOpen(true);
      return;
    }

    logActivityMutation.mutate(payload);
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <Text fw={600}>Log Interaction Outcome</Text>
          {lead && <Badge color="yellow">{lead.name}</Badge>}
        </Group>
      }
      size="lg"
      radius="md"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          {errorMsg && (
            <Alert icon={<IconAlertCircle size={16} />} title="Action Blocked / Error" color="red" variant="light">
              <Text size="xs" style={{ whiteSpace: 'pre-line' }}>
                {errorMsg}
              </Text>
            </Alert>
          )}

          <div>
            <Text size="xs" fw={600} mb={4}>
              Interaction Stage
            </Text>
            <SegmentedControl
              fullWidth
              color="yellow"
              value={stage}
              onChange={(val) => {
                setStage(val as any);
                setOutcomeId(null);
              }}
              data={[
                { label: 'Call', value: 'call' },
                { label: 'Site Survey', value: 'survey' },
                { label: 'Quotation', value: 'quote' },
              ]}
            />
          </div>

          {lead?.do_not_contact && (
            <Alert icon={<IconAlertCircle size={16} />} title="Do Not Contact Active" color="red" variant="filled">
              <Text size="xs">
                This lead has opted out or been marked &quot;Do not contact&quot;. Further calls and direct messages are strictly blocked.
              </Text>
            </Alert>
          )}

          {stage === 'call' && lead?.opt_out_calls && (
            <Alert icon={<IconAlertCircle size={16} />} title="Call Channel Opted Out" color="red" variant="light">
              <Text size="xs">
                Customer has specifically unsubscribed from voice calls. Consider written communication if permitted.
              </Text>
            </Alert>
          )}

          {stage === 'call' && lead && lead.is_within_calling_hours === false && (
            <Alert icon={<IconAlertCircle size={16} />} title="Outside Permitted Calling Hours" color="orange" variant="light">
              <Text size="xs">
                {lead.calling_hours_reason || 'Outside standard calling hours for lead local timezone.'}
                <br />
                Under telemarketing regulations, logging calls outside standard hours requires an explicit justification (e.g. customer pre-agreed time). This reason will be recorded immutably in the compliance Audit Log.
              </Text>
            </Alert>
          )}

          {stage === 'call' && lead && lead.is_within_calling_hours === false && (
            <TextInput
              label="Calling Hours Override Reason (Required)"
              placeholder="e.g. Customer emailed requesting a call at this time"
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.currentTarget.value)}
              required
            />
          )}

          <Select
            label="Pick Outcome"
            placeholder="Select the call/meeting result"
            data={outcomes.map((o) => ({
              value: String(o.id),
              label: `${o.name}  →  [${o.default_status}]`,
            }))}
            value={outcomeId}
            onChange={handleOutcomeChange}
            searchable
            clearable
          />

          <Group grow>
            <TextInput
              label="Resulting Status"
              value={statusVal}
              onChange={(e) => setStatusVal(e.currentTarget.value)}
              required
            />
            <TextInput
              label="Next Action"
              value={nextAction}
              onChange={(e) => setNextAction(e.currentTarget.value)}
              required={!isTerminal}
            />
          </Group>

          {!isTerminal && (
            <TextInput
              label="Next Follow-up Date & Time"
              description="Required for all non-terminal leads"
              type="datetime-local"
              value={nextFollowupAt}
              onChange={(e) => setNextFollowupAt(e.currentTarget.value)}
              required
              leftSection={<IconCalendar size={16} />}
            />
          )}

          {showLostReason && (
            <Select
              label="Lost Reason"
              placeholder="Select why the lead was lost"
              data={lostReasons.map((r) => ({ value: String(r.id), label: r.name }))}
              value={lostReasonId}
              onChange={setLostReasonId}
              required
            />
          )}

          {showNurtureReason && (
            <Select
              label="Nurture Reason"
              placeholder="Select why the lead wants to wait"
              data={nurtureReasons.map((r) => ({ value: String(r.id), label: r.name }))}
              value={nurtureReasonId}
              onChange={setNurtureReasonId}
              required
            />
          )}

          <Textarea
            label="Interaction Notes"
            placeholder="Customer remarks, roof dimensions mentioned, family concerns, etc."
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.currentTarget.value)}
          />

          <div>
            <TextInput
              label="Optional Remark (max 500 chars)"
              placeholder="e.g. Call back on Friday after 6 PM"
              maxLength={500}
              value={remark}
              onChange={(e) => setRemark(e.currentTarget.value)}
            />
            {remark && (
              <Text size="10px" c="dimmed" ta="right">
                {remark.length}/500 chars
              </Text>
            )}
          </div>

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" color="yellow" loading={logActivityMutation.isPending}>
              Save Outcome
            </Button>
          </Group>
        </Stack>
      </form>

      <ConfirmActionModal
        opened={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => {
          setConfirmOpen(false);
          if (pendingPayload) {
            logActivityMutation.mutate(pendingPayload);
          }
        }}
        title={
          statusVal === 'Lost'
            ? 'Confirm Marking Lead Lost'
            : statusVal === 'Won'
            ? 'Confirm Proposal Won'
            : 'Confirm Do Not Contact'
        }
        message={
          statusVal === 'Lost'
            ? `Are you sure you want to mark "${lead?.name}" as Lost? This is a terminal status.`
            : statusVal === 'Won'
            ? `Are you sure you want to mark "${lead?.name}" as Won? The customer has accepted the solar proposal.`
            : `Are you sure you want to mark "${lead?.name}" as Do Not Contact? All further call and WhatsApp interactions will be permanently blocked.`
        }
        confirmLabel={statusVal === 'Won' ? 'Confirm Won' : 'Confirm Action'}
        confirmColor={statusVal === 'Won' ? 'green' : 'red'}
        loading={logActivityMutation.isPending}
      />
    </Modal>
  );
};
