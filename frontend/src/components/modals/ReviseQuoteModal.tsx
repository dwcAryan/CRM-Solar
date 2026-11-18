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
  const isAU = quote?.region === 'AU' || quote?.currency === 'AUD';
  const currencySymbol = quote?.currency_symbol || (isAU ? 'A$' : '₹');
  const incentiveLabel = quote?.incentive_label || (isAU ? 'Government Incentive (STCs & Rebates)' : 'Applicable Subsidy / Discount');

  const [systemSizeKw, setSystemSizeKw] = useState<number | string>(3.3);
  const [batteryKwh, setBatteryKwh] = useState<number | string>('');
  const [brand, setBrand] = useState('');
  const [price, setPrice] = useState<number | string>(0);
  const [subsidyAmount, setSubsidyAmount] = useState<number | string>(0);
  const [notes, setNotes] = useState('');
  const [remark, setRemark] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (opened && quote) {
      setSystemSizeKw(quote.system_size_kw);
      setBatteryKwh(quote.battery_kwh || '');
      setBrand(quote.brand);
      setPrice(quote.price);
      setSubsidyAmount(quote.subsidy_amount || 0);
      setNotes(`Revised from v${quote.version}: `);
      setRemark('');
      setErrorMsg(null);
    }
  }, [opened, quote]);

  const netPrice = Number(price || 0) - Number(subsidyAmount || 0);

  const reviseMutation = useMutation({
    mutationFn: () => {
      if (!quote) throw new Error('No quote selected');
      return reviseQuote(quote.id, {
        system_size_kw: Number(systemSizeKw),
        battery_kwh: batteryKwh ? Number(batteryKwh) : undefined,
        brand: brand.trim(),
        price: Number(price),
        subsidy_amount: subsidyAmount ? Number(subsidyAmount) : undefined,
        notes: notes.trim(),
        remark: remark.trim() || undefined,
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
          <Badge color={isAU ? 'teal' : 'orange'} variant="outline">
            {currencySymbol}
          </Badge>
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
              placeholder="e.g. 3.3, 5, 6.6, 10"
              value={systemSizeKw}
              onChange={setSystemSizeKw}
              min={0.5}
              step={0.1}
              required
            />
            <NumberInput
              label="Battery Storage (kWh) [Optional]"
              placeholder="e.g. 9.6, 13.5"
              value={batteryKwh}
              onChange={setBatteryKwh}
              min={0}
              step={0.5}
            />
          </Group>

          <TextInput
            label="Equipment Brand & Specification"
            value={brand}
            onChange={(e) => setBrand(e.currentTarget.value)}
            required
          />

          <Group grow>
            <NumberInput
              label={`Total Gross Price (${currencySymbol})`}
              value={price}
              onChange={setPrice}
              min={0}
              required
            />
            <NumberInput
              label={`${incentiveLabel} (${currencySymbol})`}
              value={subsidyAmount}
              onChange={setSubsidyAmount}
              min={0}
            />
          </Group>

          <Paper p="xs" withBorder bg={isAU ? 'var(--mantine-color-teal-0)' : 'var(--mantine-color-yellow-0)'}>
            <Group justify="space-between">
              <div>
                <Text size="xs" fw={500}>
                  New Customer Net Out-of-Pocket:
                </Text>
                <Text size="11px" c="dimmed">
                  {isAU
                    ? 'Price inclusive of 10% GST and point-of-sale STC discount'
                    : 'Price inclusive of 5% GST; subsidy claim processed per PM Surya Ghar guidelines'}
                </Text>
              </div>
              <Text size="md" fw={700} c={isAU ? 'teal.9' : 'yellow.9'}>
                {currencySymbol}
                {netPrice > 0
                  ? isAU
                    ? netPrice.toLocaleString('en-AU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                    : netPrice.toLocaleString('en-IN')
                  : 0}
              </Text>
            </Group>
          </Paper>

          <Textarea
            label="Revision Notes / Reason for Change"
            placeholder="e.g. Discount given, adjusted panel placement to fit 6.6kW"
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.currentTarget.value)}
            required
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
            <Button type="submit" color={isAU ? 'teal' : 'yellow'} loading={reviseMutation.isPending}>
              Create Revision v{(quote?.version || 0) + 1}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};
