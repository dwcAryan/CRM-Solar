import React, { useState, useEffect } from 'react';
import {
  Button,
  Modal,
  Stack,
  Text,
  Group,
  ThemeIcon,
  Badge,
  List,
  Alert,
  Divider,
} from '@mantine/core';
import {
  IconDownload,
  IconDeviceDesktop,
  IconDeviceMobile,
  IconCheck,
  IconBrandSafari,
  IconBrandChrome,
  IconBrandFirefox,
} from '@tabler/icons-react';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
}

interface InstallAppButtonProps {
  isMobile?: boolean;
}

export const InstallAppButton: React.FC<InstallAppButtonProps> = ({ isMobile = false }) => {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isStandalone, setIsStandalone] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [modalOpened, setModalOpened] = useState(false);

  useEffect(() => {
    // Check if running in standalone PWA mode
    const checkStandalone = () => {
      const isDisplayStandalone = window.matchMedia('(display-mode: standalone)').matches;
      const isNavStandalone = (navigator as unknown as { standalone?: boolean }).standalone === true;
      return isDisplayStandalone || isNavStandalone;
    };

    setIsStandalone(checkStandalone());

    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };

    const handleAppInstalled = () => {
      setIsInstalled(true);
      setDeferredPrompt(null);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstall);
    window.addEventListener('appinstalled', handleAppInstalled);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
      window.removeEventListener('appinstalled', handleAppInstalled);
    };
  }, []);

  const handleInstallClick = async () => {
    if (deferredPrompt) {
      try {
        await deferredPrompt.prompt();
        const choice = await deferredPrompt.userChoice;
        if (choice.outcome === 'accepted') {
          setIsInstalled(true);
        }
        setDeferredPrompt(null);
      } catch (err) {
        console.error('PWA install prompt error:', err);
      }
    } else {
      // Browser does not support native prompt (Safari, Firefox, etc.)
      setModalOpened(true);
    }
  };

  // Browser detection for custom instructions
  const ua = navigator.userAgent.toLowerCase();
  const isSafari = ua.includes('safari') && !ua.includes('chrome') && !ua.includes('chromium');
  const isFirefox = ua.includes('firefox');
  const isIOS = /iphone|ipad|ipod/.test(ua);

  if (isStandalone || isInstalled) {
    return (
      <Badge
        fullWidth
        variant="light"
        color="teal"
        size="lg"
        leftSection={<IconCheck size={14} />}
        py="xs"
      >
        App Installed
      </Badge>
    );
  }

  const label = isMobile ? 'Install app' : 'Download for desktop';
  const icon = isMobile ? <IconDeviceMobile size={18} /> : <IconDownload size={18} />;

  return (
    <>
      <Button
        fullWidth
        variant="light"
        color="yellow"
        leftSection={icon}
        onClick={handleInstallClick}
        size="sm"
        radius="md"
        styles={{
          root: {
            fontWeight: 600,
          },
        }}
      >
        {label}
      </Button>

      {/* Manual installation instructions modal */}
      <Modal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        title={
          <Group gap="xs">
            <ThemeIcon color="yellow" variant="light">
              <IconDeviceDesktop size={18} />
            </ThemeIcon>
            <Text fw={600}>Install Solar CRM as an App</Text>
          </Group>
        }
        centered
        radius="md"
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Install Solar CRM on your device for fast access, push notifications, and a distraction-free window.
          </Text>

          {isIOS ? (
            <Alert color="blue" icon={<IconBrandSafari size={18} />} title="Install on iPhone / iPad (Safari)">
              <List type="ordered" size="sm" spacing="xs">
                <List.Item>Tap the <strong>Share</strong> button (square with arrow pointing up) at the bottom of Safari.</List.Item>
                <List.Item>Scroll down the share sheet and tap <strong>Add to Home Screen</strong>.</List.Item>
                <List.Item>Tap <strong>Add</strong> in the top-right corner.</List.Item>
              </List>
            </Alert>
          ) : isSafari ? (
            <Alert color="blue" icon={<IconBrandSafari size={18} />} title="Install on Mac (Safari)">
              <List type="ordered" size="sm" spacing="xs">
                <List.Item>In the top menu bar, click <strong>File</strong>.</List.Item>
                <List.Item>Select <strong>Add to Dock...</strong></List.Item>
                <List.Item>Click <strong>Add</strong> to create the desktop app icon.</List.Item>
              </List>
            </Alert>
          ) : isFirefox ? (
            <Alert color="orange" icon={<IconBrandFirefox size={18} />} title="Firefox Desktop Notice">
              <Text size="sm">
                Mozilla Firefox desktop does not currently support installing Progressive Web Apps natively.
              </Text>
              <Text size="xs" mt="xs">
                For the best desktop app experience with one-click installation, we recommend opening Solar CRM in <strong>Google Chrome</strong>, <strong>Microsoft Edge</strong>, or <strong>Brave</strong>.
              </Text>
            </Alert>
          ) : (
            <Alert color="green" icon={<IconBrandChrome size={18} />} title="Install in Chrome or Edge">
              <List type="ordered" size="sm" spacing="xs">
                <List.Item>Click the <strong>Install</strong> icon in the address bar (on the right side next to bookmarks).</List.Item>
                <List.Item>Or open the browser menu (<strong>⋮</strong> or <strong>⋯</strong>) in the top-right corner.</List.Item>
                <List.Item>Click <strong>Install Solar CRM...</strong> and confirm.</List.Item>
              </List>
            </Alert>
          )}

          <Divider />

          <Group justify="flex-end">
            <Button variant="default" onClick={() => setModalOpened(false)}>
              Got it
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
};
