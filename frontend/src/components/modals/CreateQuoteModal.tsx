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
  Paper,
  Badge,
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
  const isAU = lead?.region_code === 'AU' || lead?.region === 'AU';
  const currencySymbol = lead?.currency_symbol || (isAU ? 'A$' : '₹');
  const incentiveLabel = isAU ? 'Government Incentive (STCs & Rebates)' : 'Applicable Subsidy (PM Surya Ghar)';

  const [systemSizeKw, setSystemSizeKw] = useState<number | string>(isAU ? 6.6 : 3.3);
  const [batteryKwh, setBatteryKwh] = useState<number | string>('');
  const [brand, setBrand] = useState(
    isAU
      ? 'Trina Solar 440W + Sungrow Inverter'
      : 'Waaree / Adani Mono PERC + Polycab/Growatt Inverter'
  );
  const [price, setPrice] = useState<number | string>(isAU ? 8500 : 195000);
  const [subsidyAmount, setSubsidyAmount] = useState<number | string>(isAU ? 2800 : 78000);
  const [notes, setNotes] = useState('');
  const [remark, setRemark] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (opened && lead) {
      const leadIsAU = lead.region_code === 'AU' || lead.region === 'AU';
      setSystemSizeKw(leadIsAU ? 6.6 : 3.3);
      setBatteryKwh(leadIsAU ? 10.0 : '');
      setBrand(
        leadIsAU
          ? 'Trina Solar 440W Vertex S+ with Sungrow SH5.0RS Hybrid'
          : 'Waaree 540W Mono PERC + Growatt Inverter'
      );
      setPrice(leadIsAU ? 8900 : 195000);
      setSubsidyAmount(leadIsAU ? 2900 : 78000);
      setNotes('');
      setRemark('');
      setErrorMsg(null);
    }
  }, [opened, lead]);

  const netPrice = Number(price || 0) - Number(subsidyAmount || 0);

  const createMutation = useMutation({
    mutationFn: () => {
      if (!lead) throw new Error('No lead selected');
      return createQuote({
        lead_id: lead.id,
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
          <Badge color={isAU ? 'teal' : 'orange'} variant="light">
            {lead?.region_code || 'IN'} ({currencySymbol})
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

          <Group grow>
            <NumberInput
              label="System Size (kW)"
              placeholder={isAU ? 'e.g. 6.6, 10' : 'e.g. 3.3, 5'}
              value={systemSizeKw}
              onChange={setSystemSizeKw}
              min={0.5}
              step={0.1}
              required
            />
            <NumberInput
              label="Battery Storage (kWh) [Optional]"
              placeholder={isAU ? 'e.g. 9.6, 13.5' : 'Optional (e.g. 5)'}
              value={batteryKwh}
              onChange={setBatteryKwh}
              min={0}
              step={0.5}
            />
          </Group>

          <TextInput
            label="Equipment Brand & Specification"
            placeholder={
              isAU
                ? 'e.g. Trina Vertex S+ 440W, Fronius Primo 5kW inverter'
                : 'e.g. Waaree 540W Mono PERC + Growatt Inverter'
            }
            value={brand}
            onChange={(e) => setBrand(e.currentTarget.value)}
            required
          />

          <Group grow>
            <NumberInput
              label={`Total Gross Price (${currencySymbol})`}
              placeholder={isAU ? 'e.g. 8900' : 'e.g. 195000'}
              value={price}
              onChange={setPrice}
              min={0}
              required
            />
            <NumberInput
              label={`${incentiveLabel} (${currencySymbol})`}
              placeholder={isAU ? 'e.g. 2900 (STC discount)' : 'e.g. 78000'}
              value={subsidyAmount}
              onChange={setSubsidyAmount}
              min={0}
            />
          </Group>

          <Paper p="xs" withBorder bg={isAU ? 'var(--mantine-color-teal-0)' : 'var(--mantine-color-yellow-0)'}>
            <Group justify="space-between">
              <div>
                <Text size="xs" fw={500}>
                  Customer Estimated Net Out-of-Pocket:
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
            label="Proposal Notes / Inclusions"
            placeholder={
              isAU
                ? 'e.g. CEC-accredited design, smart meter installation, DNSP grid pre-approval included'
                : 'e.g. Standard 5-year comprehensive warranty, hot-dip galvanized mounting structure included'
            }
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.currentTarget.value)}
          />

          <TextInput
            label="Optional Remark (max 500 chars)"
            placeholder="e.g. Discount given for same-day agreement"
            maxLength={500}
            value={remark}
            onChange={(e) => setRemark(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" color={isAU ? 'teal' : 'yellow'} loading={createMutation.isPending}>
              Generate Quotation
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};
