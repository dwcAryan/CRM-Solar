import React, { useState, useEffect } from 'react';
import {
  Modal,
  Stack,
  Switch,
  Group,
  Text,
  Badge,
  Button,
  Divider,
  Paper,
} from '@mantine/core';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  IconDeviceDesktop,
} from '@tabler/icons-react';
import { apiClient } from '../../api/client';

interface NotificationSettingsModalProps {
  opened: boolean;
  onClose: () => void;
}

interface NotificationPreferenceData {
  id?: number;
  in_app_enabled: boolean;
  browser_enabled: boolean;
  push_enabled: boolean;
  email_enabled: boolean;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
}

export const NotificationSettingsModal: React.FC<NotificationSettingsModalProps> = ({
  opened,
  onClose,
}) => {
  const queryClient = useQueryClient();
  const [browserPermission, setBrowserPermission] = useState<string>('default');

  useEffect(() => {
    if ('Notification' in window) {
      setBrowserPermission(Notification.permission);
    }
  }, [opened]);

  const { data: preferences } = useQuery<NotificationPreferenceData>({
    queryKey: ['notification-preferences'],
    queryFn: async () => {
      const res = await apiClient.get('/api/notifications/preferences/');
      return res.data;
    },
    enabled: opened,
  });

  const [form, setForm] = useState<NotificationPreferenceData>({
    in_app_enabled: true,
    browser_enabled: true,
    push_enabled: true,
    email_enabled: false,
    quiet_hours_enabled: false,
    quiet_hours_start: '22:00',
    quiet_hours_end: '08:00',
  });

  useEffect(() => {
    if (preferences) {
      setForm({
        in_app_enabled: preferences.in_app_enabled,
        browser_enabled: preferences.browser_enabled,
        push_enabled: preferences.push_enabled,
        email_enabled: preferences.email_enabled,
        quiet_hours_enabled: preferences.quiet_hours_enabled,
        quiet_hours_start: preferences.quiet_hours_start ? preferences.quiet_hours_start.slice(0, 5) : '22:00',
        quiet_hours_end: preferences.quiet_hours_end ? preferences.quiet_hours_end.slice(0, 5) : '08:00',
      });
    }
  }, [preferences]);

  const updateMutation = useMutation({
    mutationFn: async (updated: Partial<NotificationPreferenceData>) => {
      const res = await apiClient.put('/api/notifications/preferences/', updated);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-preferences'] });
      onClose();
    },
  });

  const handleSave = () => {
    updateMutation.mutate(form);
  };

  const handleRequestBrowserPermission = async () => {
    if ('Notification' in window) {
      const res = await Notification.requestPermission();
      setBrowserPermission(res);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={<Text fw={600}>Notification &amp; Reminder Preferences</Text>}
      centered
      radius="md"
      size="md"
    >
      <Stack gap="md">
        {/* Browser Permission Status */}
        <Paper withBorder p="sm" radius="md">
          <Group justify="space-between">
            <Group gap="xs">
              <IconDeviceDesktop size={18} />
              <Text size="sm" fw={500}>Browser Notification Permission</Text>
            </Group>
            <Badge
              color={
                browserPermission === 'granted'
                  ? 'green'
                  : browserPermission === 'denied'
                  ? 'red'
                  : 'yellow'
              }
            >
              {browserPermission.toUpperCase()}
            </Badge>
          </Group>
          {browserPermission !== 'granted' && (
            <Button
              size="xs"
              variant="light"
              color="yellow"
              mt="xs"
              onClick={handleRequestBrowserPermission}
            >
              Request Browser Permission
            </Button>
          )}
        </Paper>

        <Divider label="Channels" labelPosition="left" />

        <Switch
          label="In-App Notifications"
          description="Display alerts in top navigation bell and count badge"
          checked={form.in_app_enabled}
          onChange={(e) => setForm({ ...form, in_app_enabled: e.currentTarget.checked })}
        />

        <Switch
          label="Browser Notifications"
          description="Pop-up notifications while Solar CRM is open in any tab"
          checked={form.browser_enabled}
          onChange={(e) => setForm({ ...form, browser_enabled: e.currentTarget.checked })}
        />

        <Switch
          label="Web Push Notifications"
          description="Receive critical reminders even when the browser tab is closed"
          checked={form.push_enabled}
          onChange={(e) => setForm({ ...form, push_enabled: e.currentTarget.checked })}
        />

        <Switch
          label="Email Digests"
          description="Receive daily morning summary emails of assigned tasks"
          checked={form.email_enabled}
          onChange={(e) => setForm({ ...form, email_enabled: e.currentTarget.checked })}
        />

        <Divider label="Quiet Hours &amp; Timezone" labelPosition="left" />

        <Switch
          label="Enable Quiet Hours"
          description="Silence notifications during your designated off-work hours"
          checked={form.quiet_hours_enabled}
          onChange={(e) => setForm({ ...form, quiet_hours_enabled: e.currentTarget.checked })}
        />

        {form.quiet_hours_enabled && (
          <Group grow>
            <div>
              <Text size="xs" fw={500} mb={4}>Quiet Hours Start</Text>
              <input
                type="time"
                value={form.quiet_hours_start}
                onChange={(e) => setForm({ ...form, quiet_hours_start: e.target.value })}
                style={{
                  width: '100%',
                  padding: '6px 10px',
                  borderRadius: '4px',
                  border: '1px solid #ced4da',
                }}
              />
            </div>
            <div>
              <Text size="xs" fw={500} mb={4}>Quiet Hours End</Text>
              <input
                type="time"
                value={form.quiet_hours_end}
                onChange={(e) => setForm({ ...form, quiet_hours_end: e.target.value })}
                style={{
                  width: '100%',
                  padding: '6px 10px',
                  borderRadius: '4px',
                  border: '1px solid #ced4da',
                }}
              />
            </div>
          </Group>
        )}

        <Divider />

        <Group justify="flex-end" gap="sm">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button color="yellow" onClick={handleSave} loading={updateMutation.isPending}>
            Save Preferences
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};
