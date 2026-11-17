import React, { useState, useEffect } from 'react';
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
  Badge,
  Paper,
} from '@mantine/core';
import { IconFileDiff, IconAlertCircle } from '@tabler/icons-react';
import { reviseQuote } from '../../api/client';
import type { Quote } from '../../api/types';

interface ReviseQuoteModalProps {
  opened: boolean;
  onClose: () => void;
  quote: Quote | null;
  onSuccess?: () => void;
}

export const ReviseQuoteModal: React.FC<ReviseQuoteModalProps> = ({
  opened,
  onClose,
  quote,
  onSuccess,
}) => {
  const queryClient = useQueryClient();
  const [systemSizeKw, setSystemSizeKw] = useState<number | string>(3.3);
  const [brand, setBrand] = useState('');
  const [price, setPrice] = useState<number | string>(0);
  const [subsidyAmount, setSubsidyAmount] = useState<number | string>(0);
  const [notes, setNotes] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (opened && quote) {
      setSystemSizeKw(quote.system_size_kw);
      setBrand(quote.brand);
      setPrice(quote.price);
      setSubsidyAmount(quote.subsidy_amount || 0);
      setNotes(`Revised from v${quote.version}: `);
      setErrorMsg(null);
    }
  }, [opened, quote]);

  const netPrice = Number(price || 0) - Number(subsidyAmount || 0);

  const reviseMutation = useMutation({
    mutationFn: () => {
      if (!quote) throw new Error('No quote selected');
      return reviseQuote(quote.id, {
        system_size_kw: Number(systemSizeKw),
        brand: brand.trim(),
        price: Number(price),
        subsidy_amount: subsidyAmount ? Number(subsidyAmount) : undefined,
        notes: notes.trim(),
      });
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
        setErrorMsg(messages || 'Failed to revise quote.');
      } else {
        setErrorMsg(err.message || 'Failed to revise quote.');
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!systemSizeKw || !price || !brand) {
      setErrorMsg('Please fill in system size, brand, and total price.');
      return;
    }
    setErrorMsg(null);
    reviseMutation.mutate();
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <IconFileDiff size={18} />
          <Text fw={600}>Revise Quotation</Text>
          {quote && <Badge color="gray">v{quote.version} → v{quote.version + 1}</Badge>}
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

          <Alert color="blue" variant="light">
            <Text size="xs">
              Revising will keep <strong>v{quote?.version}</strong> in history as superseded and create version{' '}
              <strong>v{(quote?.version || 0) + 1}</strong> with the lead updated to <em>Revising quote</em>.
            </Text>
          </Alert>

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
              value={brand}
              onChange={(e) => setBrand(e.currentTarget.value)}
              required
            />
          </Group>

          <Group grow>
            <NumberInput
              label="Total Gross Price (₹)"
              value={price}
              onChange={setPrice}
              min={0}
              required
            />
            <NumberInput
              label="Applicable Subsidy / Discount (₹)"
              value={subsidyAmount}
              onChange={setSubsidyAmount}
              min={0}
            />
          </Group>

          <Paper p="xs" withBorder bg="var(--mantine-color-yellow-0)">
            <Group justify="space-between">
              <Text size="xs" fw={500}>
                New Customer Net Payable:
              </Text>
              <Text size="md" fw={700} c="yellow.9">
                ₹{netPrice > 0 ? netPrice.toLocaleString('en-IN') : 0}
              </Text>
            </Group>
          </Paper>

          <Textarea
            label="Revision Notes / Reason for Change"
            placeholder="e.g. Discount given, adjusted panel placement to fit 4kW"
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.currentTarget.value)}
            required
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" color="yellow" loading={reviseMutation.isPending}>
              Create Revision v{(quote?.version || 0) + 1}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};
