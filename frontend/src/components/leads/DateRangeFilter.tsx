import React, { useState } from 'react';
import {
  Group,
  Select,
  Button,
  Badge,
  ActionIcon,
  Drawer,
  Stack,
  Box,
} from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { useMediaQuery } from '@mantine/hooks';
import { IconCalendar, IconX } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import dayjs from 'dayjs';
import 'dayjs/locale/hi';

export interface DateFilterValue {
  field: 'created_at' | 'next_followup_at' | 'updated_at' | 'last_activity_at' | 'won_at';
  from: Date | null;
  to: Date | null;
}

interface DateRangeFilterProps {
  value: DateFilterValue;
  onChange: (value: DateFilterValue) => void;
  onClear: () => void;
}

export const DateRangeFilter: React.FC<DateRangeFilterProps> = ({
  value,
  onChange,
  onClear,
}) => {
  const { t, i18n } = useTranslation(['leads', 'common']);
  const isMobile = useMediaQuery('(max-width: 600px)');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [preset, setPreset] = useState<string>('custom');

  const lang = i18n.language?.startsWith('hi') ? 'hi' : 'en';

  const toDateObj = (d: any): Date | null => (d ? (d instanceof Date ? d : new Date(d)) : null);

  const fieldOptions = [
    { value: 'created_at', label: t('date_filter.created_date', 'Created date') },
    { value: 'next_followup_at', label: t('date_filter.next_followup_date', 'Next follow-up date') },
    { value: 'last_activity_at', label: t('date_filter.last_activity_date', 'Last activity date') },
    { value: 'updated_at', label: t('date_filter.last_updated_date', 'Last updated date') },
    { value: 'won_at', label: t('date_filter.won_date', 'Won date') },
  ];

  const handlePresetSelect = (presetKey: string) => {
    setPreset(presetKey);
    const today = dayjs();
    let newFrom: Date | null = null;
    let newTo: Date | null = null;

    switch (presetKey) {
      case 'today':
        newFrom = today.toDate();
        newTo = today.toDate();
        break;
      case 'yesterday':
        newFrom = today.subtract(1, 'day').toDate();
        newTo = today.subtract(1, 'day').toDate();
        break;
      case 'last_7_days':
        newFrom = today.subtract(6, 'day').toDate();
        newTo = today.toDate();
        break;
      case 'this_month':
        newFrom = today.startOf('month').toDate();
        newTo = today.toDate();
        break;
      case 'last_month':
        newFrom = today.subtract(1, 'month').startOf('month').toDate();
        newTo = today.subtract(1, 'month').endOf('month').toDate();
        break;
      case 'custom':
      default:
        return;
    }

    onChange({
      ...value,
      from: newFrom,
      to: newTo,
    });
  };

  const hasActiveFilter = Boolean(value.from || value.to);

  const getActiveChipLabel = () => {
    const fieldObj = fieldOptions.find((f) => f.value === value.field);
    const fieldName = fieldObj?.label || 'Created';
    const fromStr = value.from ? dayjs(value.from).format('DD/MM/YYYY') : '...';
    const toStr = value.to ? dayjs(value.to).format('DD/MM/YYYY') : '...';
    return `${fieldName}: ${fromStr} - ${toStr}`;
  };

  const renderFilterControls = () => (
    <Stack gap="xs">
      <Group gap="xs" grow={isMobile}>
        <Select
          size="xs"
          data={fieldOptions}
          value={value.field}
          onChange={(newField) => {
            if (newField) {
              onChange({
                ...value,
                field: newField as DateFilterValue['field'],
              });
            }
          }}
          style={{ minWidth: 160 }}
          aria-label="Filter by date field"
        />

        <Select
          size="xs"
          placeholder={t('date_filter.presets', 'Presets')}
          data={[
            { value: 'custom', label: t('date_filter.custom', 'Custom') },
            { value: 'today', label: t('date_filter.today', 'Today') },
            { value: 'yesterday', label: t('date_filter.yesterday', 'Yesterday') },
            { value: 'last_7_days', label: t('date_filter.last_7_days', 'Last 7 days') },
            { value: 'this_month', label: t('date_filter.this_month', 'This month') },
            { value: 'last_month', label: t('date_filter.last_month', 'Last month') },
          ]}
          value={preset}
          onChange={(val) => val && handlePresetSelect(val)}
          style={{ minWidth: 130 }}
        />
      </Group>

      <Group gap="xs" grow={isMobile}>
        <DatePickerInput
          size="xs"
          locale={lang}
          valueFormat="DD/MM/YYYY"
          placeholder={t('date_filter.from_date', 'From date (DD/MM/YYYY)')}
          value={value.from}
          onChange={(d) => {
            setPreset('custom');
            onChange({ ...value, from: toDateObj(d) });
          }}
          clearable
          style={{ minWidth: 140 }}
          aria-label="From date"
        />

        <DatePickerInput
          size="xs"
          locale={lang}
          valueFormat="DD/MM/YYYY"
          placeholder={t('date_filter.to_date', 'To date (DD/MM/YYYY)')}
          value={value.to}
          onChange={(d) => {
            setPreset('custom');
            onChange({ ...value, to: toDateObj(d) });
          }}
          clearable
          minDate={value.from || undefined}
          style={{ minWidth: 140 }}
          aria-label="To date"
        />
      </Group>
    </Stack>
  );

  return (
    <Box>
      {isMobile ? (
        <>
          <Button
            size="xs"
            variant={hasActiveFilter ? 'filled' : 'light'}
            color={hasActiveFilter ? 'yellow' : 'gray'}
            leftSection={<IconCalendar size={14} />}
            onClick={() => setDrawerOpen(true)}
          >
            {hasActiveFilter ? t('date_filter.active', 'Date Filter Active') : t('date_filter.filter_by_date', 'Filter by Date')}
          </Button>

          <Drawer
            opened={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            title={t('date_filter.title', 'Filter Leads by Date')}
            position="bottom"
            size="md"
          >
            <Stack gap="md" p="xs">
              {renderFilterControls()}
              <Group justify="flex-end" mt="md">
                {hasActiveFilter && (
                  <Button
                    size="xs"
                    variant="subtle"
                    color="red"
                    onClick={() => {
                      onClear();
                      setPreset('custom');
                    }}
                  >
                    {t('common:clear', 'Clear')}
                  </Button>
                )}
                <Button size="xs" onClick={() => setDrawerOpen(false)}>
                  {t('common:apply', 'Apply')}
                </Button>
              </Group>
            </Stack>
          </Drawer>
        </>
      ) : (
        <Group gap="xs" align="center" wrap="wrap">
          <Group gap="xs">
            <Select
              size="xs"
              data={fieldOptions}
              value={value.field}
              onChange={(newField) => {
                if (newField) {
                  onChange({
                    ...value,
                    field: newField as DateFilterValue['field'],
                  });
                }
              }}
              style={{ width: 155 }}
              aria-label="Filter by date field"
            />

            <Select
              size="xs"
              data={[
                { value: 'custom', label: t('date_filter.custom', 'Custom') },
                { value: 'today', label: t('date_filter.today', 'Today') },
                { value: 'yesterday', label: t('date_filter.yesterday', 'Yesterday') },
                { value: 'last_7_days', label: t('date_filter.last_7_days', 'Last 7 days') },
                { value: 'this_month', label: t('date_filter.this_month', 'This month') },
                { value: 'last_month', label: t('date_filter.last_month', 'Last month') },
              ]}
              value={preset}
              onChange={(val) => val && handlePresetSelect(val)}
              style={{ width: 125 }}
            />

            <DatePickerInput
              size="xs"
              locale={lang}
              valueFormat="DD/MM/YYYY"
              placeholder={t('date_filter.from_date', 'From date')}
              value={value.from}
              onChange={(d) => {
                setPreset('custom');
                onChange({ ...value, from: toDateObj(d) });
              }}
              clearable
              style={{ width: 130 }}
              aria-label="From date"
            />

            <DatePickerInput
              size="xs"
              locale={lang}
              valueFormat="DD/MM/YYYY"
              placeholder={t('date_filter.to_date', 'To date')}
              value={value.to}
              onChange={(d) => {
                setPreset('custom');
                onChange({ ...value, to: toDateObj(d) });
              }}
              clearable
              minDate={value.from || undefined}
              style={{ width: 130 }}
              aria-label="To date"
            />
          </Group>

          {hasActiveFilter && (
            <Badge
              variant="outline"
              color="yellow"
              size="md"
              rightSection={
                <ActionIcon
                  size="xs"
                  color="yellow"
                  radius="xl"
                  variant="transparent"
                  onClick={() => {
                    onClear();
                    setPreset('custom');
                  }}
                  aria-label="Remove date filter"
                >
                  <IconX size={10} />
                </ActionIcon>
              }
            >
              {getActiveChipLabel()}
            </Badge>
          )}
        </Group>
      )}
    </Box>
  );
};
