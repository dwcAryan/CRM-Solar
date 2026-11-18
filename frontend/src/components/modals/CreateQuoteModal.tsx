import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Modal,
  Button,
  Stack,
  NumberInput,
  TextInput,
  Textarea,
  Alert,
  Group,
  Text,
  Paper,
} from '@mantine/core';
import { IconFilePlus, IconAlertCircle } from '@tabler/icons-react';
import { createQuote } from '../../api/client';
import type { Lead } from '../../api/types';

interface CreateQuoteModalProps {
  opened: boolean;
  onClose: () => void;
  lead: Lead | null;
  onSuccess?: () => void;
}

export const CreateQuoteModal: React.FC<CreateQuoteModalProps> = ({
  opened,
  onClose,
  lead,
  onSuccess,
}) => {
  const queryClient = useQueryClient();
  const [systemSizeKw, setSystemSizeKw] = useState<number | string>(3.3);
  const [brand, setBrand] = useState('Waaree / Adani Mono PERC + Polycab/Growatt Inverter');
  const [price, setPrice] = useState<number | string>(195000);
  const [subsidyAmount, setSubsidyAmount] = useState<number | string>(78000);
  const [notes, setNotes] = useState('');
  const [remark, setRemark] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const netPrice = Number(price || 0) - Number(subsidyAmount || 0);

  const createMutation = useMutation({
    mutationFn: () => {
      if (!lead) throw new Error('No lead selected');
      return createQuote({
        lead_id: lead.id,
        system_size_kw: Number(systemSizeKw),
        brand: brand.trim(),
        price: Number(price),
        subsidy_amount: subsidyAmount ? Number(subsidyAmount) : undefined,
        notes: notes.trim(),
        remark: remark.trim() || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] });
      queryClient.invalidateQueries({ queryKey: ['lead', lead?.id] });
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
        setErrorMsg(messages || 'Failed to create quote.');
      } else {
        setErrorMsg(err.message || 'Failed to create quote.');
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!systemSizeKw || !price || !brand) {
      setErrorMsg('Please fill in system size, equipment brand, and total price.');
      return;
    }
    setErrorMsg(null);
    createMutation.mutate();
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <IconFilePlus size={18} />
          <Text fw={600}>Create Solar Quotation</Text>
        </Group>
      }
      size="lg"
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

          <Group grow>
            <NumberInput
              label="System Size (kW)"
              placeholder="e.g. 3.3, 5, 10"
              value={systemSizeKw}
              onChange={setSystemSizeKw}
              min={0.5}
              step={0.1}
              required
            />
            <TextInput
              label="Equipment Brand & Specification"
              placeholder="e.g. Waaree 540W Mono PERC + Growatt Inverter"
              value={brand}
              onChange={(e) => setBrand(e.currentTarget.value)}
              required
            />
          </Group>

          <Group grow>
            <NumberInput
              label="Total Gross Price (₹)"
              placeholder="e.g. 195000"
              value={price}
              onChange={setPrice}
              min={0}
              required
            />
            <NumberInput
              label="Applicable Subsidy / Discount (₹)"
              placeholder="e.g. 78000 (PM Surya Ghar)"
              value={subsidyAmount}
              onChange={setSubsidyAmount}
              min={0}
            />
          </Group>

          <Paper p="xs" withBorder bg="var(--mantine-color-yellow-0)">
            <Group justify="space-between">
              <Text size="xs" fw={500}>
                Customer Estimated Net Payable:
              </Text>
              <Text size="md" fw={700} c="yellow.9">
                ₹{netPrice > 0 ? netPrice.toLocaleString('en-IN') : 0}
              </Text>
            </Group>
          </Paper>

          <Textarea
            label="Proposal Notes / Terms"
            placeholder="e.g. Standard 5-year comprehensive warranty, hot-dip galvanized mounting structure included"
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.currentTarget.value)}
          />

          <TextInput
            label="Optional Remark (max 500 chars)"
            placeholder="e.g. Quoted special rate for bulk society installation"
            maxLength={500}
            value={remark}
            onChange={(e) => setRemark(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" color="yellow" loading={createMutation.isPending}>
              Generate Quotation
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};
