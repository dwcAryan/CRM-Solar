import React, { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  Button,
  Stack,
  Text,
  Group,
  ThemeIcon,
  List,
  Alert,
  Divider,
} from '@mantine/core';
import {
  IconBellRinging,
  IconShieldCheck,
  IconAlertCircle,
  IconRefresh,
} from '@tabler/icons-react';
import { apiClient } from '../../api/client';

function urlBase64ToArrayBuffer(base64String: string): ArrayBuffer {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const buffer = new ArrayBuffer(rawData.length);
  const outputArray = new Uint8Array(buffer);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return buffer;
}

export const NotificationPermissionModal: React.FC = () => {
  const [modalOpened, setModalOpened] = useState(false);
  const [deniedModalOpened, setDeniedModalOpened] = useState(false);
  const [subscribing, setSubscribing] = useState(false);

  const subscribePush = useCallback(async () => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      return;
    }
    try {
      setSubscribing(true);
      const reg = await navigator.serviceWorker.ready;

      // Fetch VAPID public key from backend
      const res = await apiClient.get('/api/notifications/vapid-public-key/');
      const pubKey = res.data?.public_key;
      if (!pubKey) return;

      const convertedVapidKey = urlBase64ToArrayBuffer(pubKey);
      let sub = await reg.pushManager.getSubscription();

      if (!sub) {
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: convertedVapidKey,
        });
      }

      const subJson = sub.toJSON();
      if (subJson.endpoint && subJson.keys) {
        await apiClient.post('/api/notifications/push-subscribe/', {
          endpoint: subJson.endpoint,
          keys: subJson.keys,
          user_agent: navigator.userAgent,
        });
      }
    } catch (err) {
      console.warn('Push subscription failed:', err);
    } finally {
      setSubscribing(false);
    }
  }, []);

  const checkPermissionState = useCallback(() => {
    if (!('Notification' in window)) return;

    const current = Notification.permission;
    if (current === 'granted') {
      subscribePush();
    } else if (current === 'default') {
      // Check 3-day cooldown and session restriction
      const dismissedAt = localStorage.getItem('solar_crm_notif_dismissed_at');
      const sessionPrompted = sessionStorage.getItem('solar_crm_notif_session_prompted');

      const threeDaysMs = 3 * 24 * 60 * 60 * 1000;
      const isCoolingDown = dismissedAt && Date.now() - parseInt(dismissedAt, 10) < threeDaysMs;

      if (!sessionPrompted && !isCoolingDown) {
        sessionStorage.setItem('solar_crm_notif_session_prompted', 'true');
        setModalOpened(true);
      }
    }
  }, [subscribePush]);

  useEffect(() => {
    checkPermissionState();
  }, [checkPermissionState]);

  const handleEnableClick = async () => {
    if (!('Notification' in window)) return;
    try {
      const result = await Notification.requestPermission();
      setModalOpened(false);

      if (result === 'granted') {
        await subscribePush();
      } else if (result === 'denied') {
        setDeniedModalOpened(true);
      }
    } catch (err) {
      console.error('Notification permission request error:', err);
    }
  };

  const handleNotNow = () => {
    localStorage.setItem('solar_crm_notif_dismissed_at', Date.now().toString());
    setModalOpened(false);
  };

  const handleCheckAgain = () => {
    if ('Notification' in window) {
      const current = Notification.permission;
      if (current === 'granted') {
        setDeniedModalOpened(false);
        subscribePush();
      }
    }
  };

  return (
    <>
      {/* Friendly Permission Request Modal */}
      <Modal
        opened={modalOpened}
        onClose={handleNotNow}
        title={
          <Group gap="xs">
            <ThemeIcon color="yellow" variant="light" size="lg" radius="xl">
              <IconBellRinging size={20} />
            </ThemeIcon>
            <Text fw={600} size="md">
              Turn on notifications to get follow-up and survey reminders
            </Text>
          </Group>
        }
        centered
        radius="md"
        size="md"
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Stay on top of critical solar customer milestones without constantly checking your browser tab:
          </Text>

          <List
            spacing="sm"
            size="sm"
            center
            icon={
              <ThemeIcon color="teal" size={24} radius="xl">
                <IconShieldCheck size={14} />
              </ThemeIcon>
            }
          >
            <List.Item>
              <strong>Morning Follow-up Alerts:</strong> Instant 9:00 AM digests of due and overdue customer calls.
            </List.Item>
            <List.Item>
              <strong>Survey Reminders:</strong> Alerts 24 hours prior to scheduled rooftop feasibility visits.
            </List.Item>
            <List.Item>
              <strong>Quiet Hours Respected:</strong> Automatically paused during your region's non-working hours.
            </List.Item>
          </List>

          <Divider my="xs" />

          <Group justify="flex-end" gap="sm">
            <Button variant="subtle" color="gray" onClick={handleNotNow}>
              Not now
            </Button>
            <Button
              color="yellow"
              onClick={handleEnableClick}
              loading={subscribing}
            >
              Enable notifications
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Denied State Help Modal / Dialog */}
      <Modal
        opened={deniedModalOpened}
        onClose={() => setDeniedModalOpened(false)}
        title={
          <Group gap="xs">
            <ThemeIcon color="red" variant="light" size="lg" radius="xl">
              <IconAlertCircle size={20} />
            </ThemeIcon>
            <Text fw={600} size="md">
              How to Unblock Notifications for Solar CRM
            </Text>
          </Group>
        }
        centered
        radius="md"
        size="md"
      >
        <Stack gap="md">
          <Alert color="red" title="Notifications are blocked in your browser">
            Follow the steps below for your browser to re-enable follow-up reminders:
          </Alert>

          <List type="ordered" spacing="xs" size="sm">
            <List.Item>
              <strong>Chrome / Edge:</strong> Click the <strong>View site information</strong> icon (tune/lock sliders) on the left side of the address bar, then switch <strong>Notifications</strong> to <strong>Allow</strong>.
            </List.Item>
            <List.Item>
              <strong>Firefox:</strong> Click the crossed-out notification speech bubble in the address bar, then click the <strong>✕</strong> next to <em>Blocked</em>.
            </List.Item>
            <List.Item>
              <strong>Safari (macOS):</strong> Go to <strong>Safari &gt; Settings &gt; Websites &gt; Notifications</strong>, find this site and set to <strong>Allow</strong>.
            </List.Item>
          </List>

          <Divider my="xs" />

          <Group justify="space-between">
            <Button variant="default" onClick={() => setDeniedModalOpened(false)}>
              Close
            </Button>
            <Button
              variant="light"
              color="blue"
              leftSection={<IconRefresh size={16} />}
              onClick={handleCheckAgain}
            >
              Check again
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
};
