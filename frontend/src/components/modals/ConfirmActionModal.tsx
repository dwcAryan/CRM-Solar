import React from 'react';
import { Modal, Button, Stack, Text, Group, Alert } from '@mantine/core';
import { IconAlertTriangle, IconCheck } from '@tabler/icons-react';

interface ConfirmActionModalProps {
  opened: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  confirmColor?: string;
  loading?: boolean;
}

export const ConfirmActionModal: React.FC<ConfirmActionModalProps> = ({
  opened,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirm',
  confirmColor = 'red',
  loading = false,
}) => {
  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <IconAlertTriangle size={18} color={`var(--mantine-color-${confirmColor}-6)`} />
          <Text fw={600}>{title}</Text>
        </Group>
      }
      radius="md"
    >
      <Stack gap="md">
        <Alert
          color={confirmColor}
          variant="light"
          icon={confirmColor === 'green' ? <IconCheck size={16} /> : <IconAlertTriangle size={16} />}
        >
          <Text size="sm">{message}</Text>
        </Alert>

        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button color={confirmColor} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};
